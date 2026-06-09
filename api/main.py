"""
FastAPI application — Voice Shopping Agent API.

Endpoints:
  POST /v1/shop          Main pipeline: audio/text → ui_actions + voice response
  GET  /v1/products      List all products (for frontend sync)
  POST /v1/rebuild-index Admin: rebuild FAISS vector index
  GET  /health           Health check
"""

import json
import logging
import logging.config
import sys
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

import config
from agent import orchestrator
from api.middleware import RequestTracingMiddleware
from pydantic import BaseModel
from typing import List, Any, Optional


class ShopifySyncRequest(BaseModel):
    store_domain: Optional[str] = None
    access_token: Optional[str] = None

from api.models import (
    AddToCartRequest,
    CartItemResponse,
    CheckoutRequest,
    HealthResponse,
    ProductResponse,
    ShopResponse,
)
from db.database import (
    add_to_cart,
    clear_cart,
    get_all_products,
    get_cart_items,
    get_user_profile,
    remove_from_cart,
    update_user_profile,
)
from db.seed import seed as seed_db

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# Startup / Shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database, seed data, and build FAISS index on startup."""
    logger.info("Starting Voice Shopping Agent API...")

    from db.database import init_global_schema
    init_global_schema()
    
    # Preload RAG embedder and index into memory
    from agent import rag
    rag.preload()

    # --- Auto-update Shopify ScriptTags ---
    try:
        from db.database import get_global_db
        import os
        import httpx
        public_url = os.environ.get("PUBLIC_API_URL")
        if public_url:
            with get_global_db() as conn:
                installations = conn.execute("SELECT shop_domain, access_token FROM shopify_installations").fetchall()
                for inst in installations:
                    shop_domain = inst["shop_domain"]
                    access_token = inst["access_token"]
                    configured_shop = config.SHOPIFY_STORE_DOMAIN.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
                    if config.SHOPIFY_SITE_ID and shop_domain == configured_shop:
                        site_id = _safe_site_id(config.SHOPIFY_SITE_ID)
                    else:
                        site_id = _safe_site_id(shop_domain.removesuffix(".myshopify.com"))
                    script_url = f"{public_url}/shopbot.js?site={site_id}"
                    
                    headers = {
                        "X-Shopify-Access-Token": access_token,
                        "Content-Type": "application/json"
                    }
                    endpoint = f"https://{shop_domain}/admin/api/2024-01/script_tags.json"
                    
                    with httpx.Client() as client:
                        # Remove existing shopbot.js script tags
                        res = client.get(endpoint, headers=headers)
                        if res.status_code == 200:
                            for tag in res.json().get("script_tags", []):
                                if "shopbot.js" in tag.get("src", ""):
                                    client.delete(f"{endpoint.replace('.json', '')}/{tag['id']}.json", headers=headers)
                        
                        # Inject new script tag with the current public URL
                        client.post(
                            endpoint, 
                            json={"script_tag": {"event": "onload", "src": script_url, "display_scope": "online_store"}}, 
                            headers=headers
                        )
                    logger.info(f"Auto-updated ScriptTag for {shop_domain} to use {script_url}")
    except Exception as e:
        logger.error(f"Failed to auto-update ScriptTags: {e}")

    logger.info("Startup complete. API ready.")
    yield

    logger.info("Shutting down Voice Shopping Agent API.")


# App

app = FastAPI(
    title="Voice Shopping Agent API",
    description="Voice-enabled AI shopping assistant powered by OpenAI.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for demo; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if config.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestTracingMiddleware)


from api.integrations import oauth
app.include_router(oauth.router)

# Endpoints

@app.get("/health", response_model=HealthResponse, tags=["Utility"])
async def health():
    """Check API and model configuration health."""
    return HealthResponse(
        status="ok",
        models={
            "stt": config.STT_MODEL,
            "llm": config.LLM_MODEL,
            "tts": f"{config.TTS_MODEL} / {config.TTS_VOICE}",
            "embedding": config.EMBEDDING_MODEL,
        },
    )


@app.post("/v1/shop", response_model=ShopResponse, tags=["Shopping Agent"])
async def shop(
    site_id: str = Form(config.DEFAULT_SITE_ID, description="Site ID for multi-tenancy"),
    audio: Optional[UploadFile] = File(
        None, description="Audio file (WAV, MP3, WebM, OGG)"
    ),
    text: Optional[str] = Form(
        None, description="Text input (for testing without audio)"
    ),
    skip_tts: bool = Form(False, description="Skip TTS to reduce latency (testing)"),
    conversation_history: Optional[str] = Form(
        None, description="JSON array of prior conversation turns"
    ),
):
    """
    **Main endpoint.** Send customer audio or text → receive UI actions + voice response.

    - **audio**: Upload a recorded audio clip of the customer's voice.
    - **text**: Alternatively, send plain text (useful for debugging).
    - **skip_tts**: Set to `true` to skip speech synthesis (faster, text-only response).

    Returns:
    - `transcript` — what the customer said
    - `response_text` — what ShopBot says back
    - `ui_actions` — list of website control commands for the frontend
    - `audio_b64` — base64-encoded WAV of the spoken response
    """
    if audio is None and (text is None or text.strip() == ""):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either an audio file or text input.",
        )

    audio_bytes: Optional[bytes] = None
    audio_filename = "audio.wav"

    if audio is not None:
        audio_bytes = await audio.read()
        audio_filename = audio.filename or "audio.wav"

        if len(audio_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )

    parsed_history = _parse_conversation_history(conversation_history)

    result = orchestrator.run(
        site_id=site_id,
        audio_bytes=audio_bytes,
        text_input=text,
        audio_filename=audio_filename,
        skip_tts=skip_tts,
        conversation_history=parsed_history,
    )

    return ShopResponse(**result)


@app.post("/v1/shop/stream", tags=["Shopping Agent"])
async def shop_stream(
    site_id: str = Form(config.DEFAULT_SITE_ID, description="Site ID for multi-tenancy"),
    audio: Optional[UploadFile] = File(
        None, description="Audio file (WAV, MP3, WebM, OGG)"
    ),
    text: Optional[str] = Form(
        None, description="Text input (for testing without audio)"
    ),
    skip_tts: bool = Form(False, description="Skip TTS to reduce latency (testing)"),
    conversation_history: Optional[str] = Form(
        None, description="JSON array of prior conversation turns"
    ),
):
    """
    **Streaming endpoint.** Send customer audio or text → receive SSE events for transcript, ui_actions, and audio.
    """
    if audio is None and (text is None or text.strip() == ""):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either an audio file or text input.",
        )

    audio_bytes: Optional[bytes] = None
    audio_filename = "audio.wav"

    if audio is not None:
        audio_bytes = await audio.read()
        audio_filename = audio.filename or "audio.wav"
        if len(audio_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )

    parsed_history = _parse_conversation_history(conversation_history)

    def event_generator():
        for event in orchestrator.run_stream(
            site_id=site_id,
            audio_bytes=audio_bytes,
            text_input=text,
            audio_filename=audio_filename,
            skip_tts=skip_tts,
            conversation_history=parsed_history,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Bi-directional WebSocket for real-time voice shopping."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            text_input = payload.get("text")
            audio_b64 = payload.get("audio_b64")
            audio_bytes = None
            if audio_b64:
                import base64
                audio_bytes = base64.b64decode(audio_b64)
            
            # For simplicity, we assume conversation history is passed per request
            # In a real app, we could manage it in memory or Postgres.
            raw_history = payload.get("conversation_history", [])
            parsed_history = _parse_conversation_history(json.dumps(raw_history))
            site_id = payload.get("site_id", config.DEFAULT_SITE_ID)
            
            for event in orchestrator.run_stream(
                site_id=site_id,
                audio_bytes=audio_bytes,
                text_input=text_input,
                audio_filename="audio.wav",
                skip_tts=payload.get("skip_tts", False),
                conversation_history=parsed_history,
            ):
                await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


def _parse_conversation_history(raw_history: Optional[str]) -> list[dict[str, str]]:
    """Parse and sanitise browser-provided chat history before LLM use."""
    if not raw_history:
        return []

    try:
        decoded = json.loads(raw_history)
    except (json.JSONDecodeError, ValueError, TypeError):
        return []

    if not isinstance(decoded, list):
        return []

    clean_history: list[dict[str, str]] = []
    for item in decoded[-12:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue

        content = content.strip()
        if not content:
            continue

        clean_history.append(
            {
                "role": role,
                "content": content[: config.MAX_TRANSCRIPT_CHARS],
            }
        )

    return clean_history


@app.get("/v1/products", response_model=list[ProductResponse], tags=["Products"])
async def list_products(
    site_id: str = config.DEFAULT_SITE_ID, category: Optional[str] = None, limit: int = 50, offset: int = 0
):
    """
    Return active products in the catalog with pagination, optionally filtered by category.
    The frontend uses this to build its product grid dynamically.
    """
    try:
        if category:
            from db.database import get_products_by_category

            products = get_products_by_category(site_id, category, limit=limit)
        else:
            products = get_all_products(site_id, limit=limit, offset=offset)
        return [ProductResponse(**p) for p in products]
    except Exception as exc:
        logger.error("GET /v1/products failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch products.")


@app.get("/v1/products/by-ids", response_model=list[ProductResponse], tags=["Products"])
async def list_products_by_ids(ids: str, site_id: str = config.DEFAULT_SITE_ID):
    """Fetch specific products by a comma-separated list of IDs."""
    try:
        id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
        from db.database import get_products_by_ids

        products = get_products_by_ids(site_id, id_list)
        return [ProductResponse(**p) for p in products]
    except Exception as exc:
        logger.error("GET /v1/products/by-ids failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch products by IDs.")


@app.get("/v1/categories", tags=["Products"])
async def list_categories(site_id: str = config.DEFAULT_SITE_ID):
    """Return all active category names and slugs from the database."""
    try:
        from db.database import get_db
        with get_db(site_id) as conn:
            rows = conn.execute("SELECT name, slug FROM categories ORDER BY name ASC").fetchall()
            return [{"name": r["name"], "slug": r["slug"]} for r in rows]
    except Exception as exc:
        logger.error("GET /v1/categories failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch categories.")


@app.get("/v1/cart", response_model=list[CartItemResponse], tags=["Cart"])
async def get_cart(site_id: str = config.DEFAULT_SITE_ID):
    """Return all items currently in the shopping cart."""
    try:
        items = get_cart_items(site_id)
        return [CartItemResponse(**item) for item in items]
    except Exception as exc:
        logger.error("GET /v1/cart failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch cart.")


@app.post("/v1/cart/add", tags=["Cart"])
async def api_add_to_cart(req: AddToCartRequest):
    """Add a product to the cart."""
    try:
        cart_id = add_to_cart(req.site_id, req.product_id, req.quantity)
        return {"status": "ok", "cart_id": cart_id}
    except Exception as exc:
        logger.error("POST /v1/cart/add failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to add to cart.")


@app.post("/v1/cart/update", tags=["Cart"])
async def api_update_cart(req: AddToCartRequest):
    """Update the quantity of a product in the cart."""
    try:
        from db.database import update_cart_quantity

        success = update_cart_quantity(req.site_id, req.product_id, req.quantity)
        if not success:
            raise HTTPException(status_code=404, detail="Product not found in cart.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("POST /v1/cart/update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update cart.")


@app.delete("/v1/cart/{cart_id}", tags=["Cart"])
async def api_remove_from_cart(cart_id: int, site_id: str = config.DEFAULT_SITE_ID):
    """Remove a product from the cart."""
    try:
        success = remove_from_cart(site_id, cart_id)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found in cart.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("DELETE /v1/cart/{cart_id} failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to remove from cart.")


@app.delete("/v1/cart", tags=["Cart"])
async def api_clear_cart(site_id: str = config.DEFAULT_SITE_ID):
    """Clear the entire shopping cart."""
    try:
        clear_cart(site_id)
        return {"status": "ok"}
    except Exception as exc:
        logger.error("DELETE /v1/cart failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to clear cart.")


@app.post("/v1/cart/checkout", tags=["Cart"])
async def api_checkout_cart(req: CheckoutRequest):
    """Generate a PDF bill and clear the cart."""
    try:
        items = get_cart_items(req.site_id)
        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        profile = get_user_profile(req.site_id)
        final_address = profile.get("address")
        final_payment = profile.get("payment_method")

        # If new details provided and they aren't default "N/A", save them
        if req.address and req.address != "N/A" and req.address != "Not Provided":
            final_address = req.address
        if (
            req.payment_method
            and req.payment_method != "N/A"
            and req.payment_method != "Not Provided"
        ):
            final_payment = req.payment_method

        # Default fallbacks
        final_address = final_address or "Not Provided"
        final_payment = final_payment or "Not Provided"

        # Update profile to persist
        update_user_profile(req.site_id, final_address, final_payment)

        import io

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=12,
            textColor=colors.HexColor("#2c3e50"),
        )
        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=12,
            spaceAfter=20,
            textColor=colors.HexColor("#7f8c8d"),
        )

        # Header
        elements.append(Paragraph("<b>AI-KART INVOICE</b>", title_style))
        elements.append(
            Paragraph("Thank you for your futuristic purchase!", subtitle_style)
        )
        elements.append(Spacer(1, 12))

        # Customer Info
        elements.append(
            Paragraph(f"<b>Delivery Address:</b> {final_address}", styles["Normal"])
        )
        elements.append(
            Paragraph(f"<b>Payment Method:</b> {final_payment}", styles["Normal"])
        )
        elements.append(Spacer(1, 24))

        # Items Table
        data = [["Item", "Unit Price", "Qty", "Total"]]
        total_amount = 0

        for item in items:
            item_total = item["price"] * item["quantity"]
            total_amount += item_total
            data.append(
                [
                    item["name"][:40] + ("..." if len(item["name"]) > 40 else ""),
                    f"INR {item['price']:.2f}",
                    str(item["quantity"]),
                    f"INR {item_total:.2f}",
                ]
            )

        data.append(["", "", "Grand Total:", f"INR {total_amount:.2f}"])

        t = Table(data, colWidths=[250, 80, 50, 90])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#f7f9f9")),
                    ("GRID", (0, 0), (-1, -2), 1, colors.HexColor("#ecf0f1")),
                    ("FONTNAME", (2, -1), (3, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (2, -1), (3, -1), colors.HexColor("#e74c3c")),
                    ("LINEABOVE", (2, -1), (3, -1), 2, colors.HexColor("#34495e")),
                ]
            )
        )

        elements.append(t)

        # Footer
        elements.append(Spacer(1, 48))
        elements.append(
            Paragraph(
                "<i>Your intelligent items will be dispatched shortly. Have a nice day!</i>",
                styles["Normal"],
            )
        )

        doc.build(elements)

        from db.database import checkout_cart
        checkout_cart(req.site_id)

        from fastapi import Response

        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=bill.pdf"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("POST /v1/cart/checkout failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process checkout.")



@app.post("/v1/shopify/sync", tags=["Shopify Integration"])
async def shopify_sync(req: ShopifySyncRequest, background_tasks: BackgroundTasks):
    domain = req.store_domain or config.SHOPIFY_STORE_DOMAIN
    token = req.access_token or config.SHOPIFY_ACCESS_TOKEN
    
    if not domain or not token:
        raise HTTPException(400, "Missing Shopify domain or access token in request and environment variables.")
    
    try:
        import asyncio
        from agent.ingestion import sanitize_site_id, sync_shopify_api

        configured_shop = config.SHOPIFY_STORE_DOMAIN.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        request_shop = domain.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        if config.SHOPIFY_SITE_ID and request_shop == configured_shop:
            site_id = sanitize_site_id(config.SHOPIFY_SITE_ID)
        else:
            site_id = sanitize_site_id(request_shop.removesuffix(".myshopify.com"))

        synced_site_id = await asyncio.to_thread(
            sync_shopify_api,
            domain,
            token,
            site_id=site_id,
            reconcile_missing=True,
        )
    except Exception as e:
        logger.error(f"Shopify incremental sync failed: {e}")
        raise HTTPException(500, f"Failed to sync Shopify catalog: {e}")
    
    return {
        "status": "success", 
        "site_id": synced_site_id,
        "message": "Shopify catalog synced incrementally."
    }

def vectorize_site_catalog(site_id: str):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Background Vectorization started for site %s...", site_id)
    try:
        from db.database import get_db
        from agent.rag import _embed, _product_to_text
        
        with get_db(site_id) as conn:
            rows = conn.execute(
                "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON p.category_id = c.id WHERE p.embedding IS NULL"
            ).fetchall()
            
            if not rows:
                logger.info("No products need vectorization for site %s", site_id)
                return
                
            logger.info("Vectorizing %d products for site %s...", len(rows), site_id)
            texts = []
            for row in rows:
                texts.append(_product_to_text(dict(row)))
                
            embeddings = _embed(texts)
            
            for i, row in enumerate(rows):
                conn.execute(
                    "UPDATE products SET embedding = %s WHERE id = %s",
                    (embeddings[i], row["id"])
                )
            logger.info("Vectorization complete for site %s.", site_id)
    except Exception as exc:
        logger.error("Background Vectorization failed for site %s: %s", site_id, exc)




def _safe_site_id(raw: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", (raw or "").strip().lower())[:80] or "site_1"


def _safe_script_base_url(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip().strip("\"'")
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        return raw.rstrip("/")
    return ""


@app.get("/shopbot.js", tags=["Plugin"])
async def serve_plugin(site: Optional[str] = None, site_id: Optional[str] = None, shop: Optional[str] = None):
    """Serve the ShopBot JavaScript plugin with dynamic API URL."""
    from fastapi.responses import Response
    import config
    plugin_path = Path(__file__).parent.parent / "plugin" / "shopbot.js"
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")
        
    with open(plugin_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _safe_script_base_url(config.PUBLIC_API_URL) or _safe_script_base_url(config.VOICE_ORB_API_URL or "")

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(safe_api))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(safe_site))
    
    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


# Entry point

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )

