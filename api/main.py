"""
FastAPI application — Voice Shopping Agent API.

Endpoints:
  POST /v1/shop          Main pipeline: audio/text → ui_actions + voice response
  GET  /v1/products      List all products (for frontend sync)
  GET  /health           Health check
"""

import json
import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import config
from agent import orchestrator
from api.middleware import RequestTracingMiddleware
from pydantic import BaseModel


class ClientLogRequest(BaseModel):
    event: str
    payload: dict[str, Any] = {}

from api.models import (
    AddToCartRequest,
    CartItemResponse,
    CheckoutRequest,
    HealthResponse,
    ProductResponse,
    ShopResponse,
)
from db.database import (
    InvalidProductIdError,
    ProductNotFoundError,
    add_to_cart,
    catalog_source_preview,
    catalog_source_stats,
    catalog_sync_history,
    clear_cart,
    coerce_product_id,
    get_all_products,
    get_cart_items,
    get_user_profile,
    tenant_catalog_preview,
    tenant_catalog_stats,
    remove_from_cart,
    update_user_profile,
)
from db.seed import seed as seed_db

# Module-level logger — file handler is added inside lifespan() AFTER
# uvicorn has called its own logging.config.dictConfig(), so we don't
# conflict with its formatter configuration.
logger = logging.getLogger(__name__)


# Startup / Shutdown


import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database, seed data, and register pgvector on startup."""
    logger.info("Starting Voice Shopping Agent API...")
    
    # Preload RAG embedder and index into memory
    from agent import rag
    rag.preload()

    import config
    import functools
    from agent.ingestion import sync_web_crawl
    import concurrent.futures
    
    async def run_crawl_once(target_url: str, site_id: str, *, initial: bool = False) -> None:
        phase = "startup" if initial else "periodic"
        logger.info("Starting %s crawl for %s...", phase, target_url)
        try:
            loop = asyncio.get_running_loop()
            func = functools.partial(
                sync_web_crawl,
                target_url,
                max_pages=config.CRAWL_MAX_PAGES,
                max_depth=config.CRAWL_MAX_DEPTH,
                site_id=site_id,
                reconcile_missing=True,
                source_name="custom_url_crawler"
            )
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(executor, func)
            logger.info("%s crawl completed for %s.", phase.capitalize(), target_url)
        except Exception as e:
            logger.error("%s crawl failed: %s", phase.capitalize(), e)

    async def periodic_crawl():
        target_url = config.CURRENT_URL
        site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
        if target_url:
            while True:
                await asyncio.sleep(120)
                await run_crawl_once(target_url, site_id)

    startup_target_url = config.CURRENT_URL
    startup_site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if startup_target_url and config.CRAWL_ON_STARTUP:
        await run_crawl_once(startup_target_url, startup_site_id, initial=True)

    crawler_task = asyncio.create_task(periodic_crawl())

    logger.info("Startup complete. API ready.")
    yield

    crawler_task.cancel()
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

@app.post("/v1/admin/crawler/run", tags=["Utility"])
async def trigger_crawler():
    """Manually trigger the crawler."""
    import config
    import asyncio
    import concurrent.futures
    from agent.ingestion import sync_web_crawl
    
    target_url = config.CURRENT_URL
    site_id = config.CURRENT_SITE_ID or config.DEFAULT_SITE_ID
    if not target_url:
        return {"status": "error", "message": "No CURRENT_URL configured."}

    logger.info("Manual crawler trigger requested for %s...", target_url)

    def run_sync():
        try:
            sync_web_crawl(
                target_url,
                max_pages=config.CRAWL_MAX_PAGES,
                max_depth=config.CRAWL_MAX_DEPTH,
                site_id=site_id,
                reconcile_missing=True,
                source_name="custom_url_crawler"
            )
        except Exception as e:
            logger.error("Manual crawl failed: %s", e)

    loop = asyncio.get_running_loop()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, run_sync)
    
    return {"status": "ok", "message": "Crawler started in background."}

@app.post("/v1/client-log", tags=["Utility"])
async def client_log(req: ClientLogRequest):
    """Receive browser-side diagnostics from the injected widget."""
    safe_event = str(req.event)[:80]
    safe_payload = {
        str(key)[:80]: str(value)[:300]
        for key, value in (req.payload or {}).items()
    }
    logger.info("CLIENT | %s | %s", safe_event, safe_payload)
    return {"status": "ok"}

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
        id_list = []
        for raw_id in ids.split(","):
            raw_id = raw_id.strip().strip('"')
            if raw_id:
                try:
                    id_list.append(coerce_product_id(raw_id))
                except InvalidProductIdError:
                    continue
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


@app.get("/v1/catalog/status", tags=["Products"])
async def catalog_status(site_id: str = config.DEFAULT_SITE_ID):
    """Return catalog/RAG sync status for the storefront admin panel."""
    try:
        source_stats = catalog_source_stats(site_id)
        preview_source = source_stats[0]["source_name"] if source_stats else "custom_url_crawler"
        return {
            "site_id": site_id,
            "catalog": tenant_catalog_stats(site_id),
            "sources": source_stats,
            "recent_sync_runs": catalog_sync_history(site_id, limit=8),
            "catalog_preview": tenant_catalog_preview(site_id, limit=12),
            "source_preview": catalog_source_preview(site_id, preview_source, limit=12)
            if source_stats
            else [],
        }
    except Exception as exc:
        logger.error("GET /v1/catalog/status failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch catalog status.")


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
    except InvalidProductIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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

        import datetime
        buffer = io.BytesIO()

        def on_page(canvas, doc):
            canvas.saveState()
            # Draw premium border
            canvas.setStrokeColor(colors.HexColor("#2c3e50"))
            canvas.setLineWidth(2)
            canvas.rect(30, 30, letter[0] - 60, letter[1] - 60)
            
            # Header background
            canvas.setFillColor(colors.HexColor("#2c3e50"))
            canvas.rect(30, letter[1] - 130, letter[0] - 60, 100, fill=1, stroke=0)
            
            # Header text
            canvas.setFont("Helvetica-Bold", 36)
            canvas.setFillColor(colors.white)
            canvas.drawString(60, letter[1] - 85, "AI-KART")
            
            canvas.setFont("Helvetica", 14)
            canvas.drawString(60, letter[1] - 110, "PREMIUM INVOICE")
            
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=60,
            leftMargin=60,
            topMargin=150,
            bottomMargin=60,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Invoice metadata
        inv_date = datetime.datetime.now().strftime("%B %d, %Y")
        inv_no = f"INV-{int(datetime.datetime.now().timestamp())}"
        
        meta_style = ParagraphStyle(
            "Meta", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#34495e"), alignment=2 # Right align
        )
        elements.append(Paragraph(f"<b>Date:</b> {inv_date}<br/><b>Invoice #:</b> {inv_no}", meta_style))
        elements.append(Spacer(1, 20))
        
        # Customer Info
        info_style = ParagraphStyle("Info", parent=styles["Normal"], fontSize=12, leading=16, textColor=colors.HexColor("#2c3e50"))
        elements.append(Paragraph(f"<b>Billed To:</b><br/>{final_address}<br/><br/><b>Payment Method:</b><br/>{final_payment}", info_style))
        elements.append(Spacer(1, 30))

        # Items Table
        data = [["Description", "Unit Price", "Qty", "Total"]]
        total_amount = 0

        for item in items:
            item_total = item["price"] * item["quantity"]
            total_amount += item_total
            data.append(
                [
                    item["name"][:50] + ("..." if len(item["name"]) > 50 else ""),
                    f"INR {item['price']:.2f}",
                    str(item["quantity"]),
                    f"INR {item_total:.2f}",
                ]
            )

        data.append(["", "", "Subtotal:", f"INR {total_amount:.2f}"])
        data.append(["", "", "Tax (0%):", "INR 0.00"])
        data.append(["", "", "Grand Total:", f"INR {total_amount:.2f}"])

        t = Table(data, colWidths=[240, 90, 50, 110])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -4), colors.HexColor("#f8f9fa")),
                    ("GRID", (0, 0), (-1, -4), 1, colors.HexColor("#dee2e6")),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
                    ("TOPPADDING", (0, 1), (-1, -1), 10),
                    # Totals styling
                    ("FONTNAME", (2, -3), (3, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (2, -1), (3, -1), colors.HexColor("#1abc9c")),
                    ("FONTSIZE", (2, -1), (3, -1), 13),
                    ("LINEABOVE", (2, -3), (3, -3), 1, colors.HexColor("#2c3e50")),
                    ("LINEABOVE", (2, -1), (3, -1), 2, colors.HexColor("#2c3e50")),
                ]
            )
        )

        elements.append(t)

        # Footer
        elements.append(Spacer(1, 60))
        footer_style = ParagraphStyle("Footer", parent=styles["Normal"], alignment=1, textColor=colors.HexColor("#95a5a6"), fontSize=10, fontName="Helvetica-Oblique")
        elements.append(Paragraph("Thank you for choosing AI-KART.<br/>This is an automatically generated receipt.", footer_style))

        doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)

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


def _public_widget_base_url() -> str:
    return (
        _safe_script_base_url(os.environ.get("PUBLIC_API_URL", ""))
        or _safe_script_base_url(config.PUBLIC_API_URL)
        or _safe_script_base_url(config.VOICE_ORB_API_URL or "")
    )


def _load_widget_script(*, site: str, api_base_url: str) -> str:
    plugin_path = Path(__file__).parent.parent / "plugin" / "shopbot.js"
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail="Plugin script not found.")

    with open(plugin_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    js_code = js_code.replace('"__AI_PUBLIC_API_URL__"', json.dumps(api_base_url))
    js_code = js_code.replace('"__AI_DEFAULT_SITE_ID__"', json.dumps(site))
    return js_code


def _render_embed_bootstrap(*, site: str, api_base_url: str) -> str:
    return f"""
(function () {{
  if (window.__shopbotFrameLoaded) return;
  window.__shopbotFrameLoaded = true;

  var currentScript = document.currentScript;
  var scriptUrl = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
  var siteId = {json.dumps(site)};
  var apiBaseUrl = {json.dumps(api_base_url)};
  var parentOrigin = window.location.origin;
  var frameUrl = new URL(apiBaseUrl + "/shopbot-frame");
  frameUrl.searchParams.set("site", siteId);
  frameUrl.searchParams.set("parent_origin", parentOrigin);

  var frame = document.createElement("iframe");
  frame.src = frameUrl.toString();
  frame.title = "ShopBot Voice Orb";
  frame.setAttribute("allow", "microphone");
  frame.setAttribute("aria-label", "ShopBot Voice Orb");
  frame.style.position = "fixed";
  frame.style.left = "50%";
  frame.style.bottom = "12px";
  frame.style.transform = "translateX(-50%)";
  frame.style.width = "360px";
  frame.style.height = "180px";
  frame.style.maxWidth = "calc(100vw - 24px)";
  frame.style.maxHeight = "calc(100vh - 24px)";
  frame.style.border = "0";
  frame.style.background = "transparent";
  frame.style.zIndex = "2147483647";
  frame.style.overflow = "hidden";
  frame.style.colorScheme = "light";

  function clamp(value, fallback, maxCss) {{
    var numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) return fallback;
    return Math.min(numeric, maxCss);
  }}

  window.addEventListener("message", function (event) {{
    if (event.origin !== apiBaseUrl) return;
    var data = event.data || {{}};
    if (data.source !== "shopbot-frame") return;

    if (data.type === "shopbot:frame-size") {{
      var width = clamp(data.width, 360, Math.max(320, window.innerWidth - 24));
      var height = clamp(data.height, 180, Math.max(180, window.innerHeight - 24));
      frame.style.width = width + "px";
      frame.style.height = height + "px";
      return;
    }}

    if (data.type === "shopbot:navigate" && data.path) {{
      try {{
        var targetUrl = new URL(data.path, window.location.href);
        if (targetUrl.origin === window.location.origin) {{
          window.location.href = targetUrl.pathname + targetUrl.search + targetUrl.hash;
        }}
      }} catch (_err) {{}}
    }}
  }});

  function mountFrame(retries) {{
    if (document.body) {{
      document.body.appendChild(frame);
      return;
    }}
    if (retries > 100) {{
      return;
    }}
    setTimeout(function () {{ mountFrame(retries + 1); }}, 50);
  }}

  mountFrame(0);
}})();
"""


@app.get("/shopbot-frame", tags=["Plugin"])
async def serve_plugin_frame(site: Optional[str] = None, site_id: Optional[str] = None, shop: Optional[str] = None, parent_origin: Optional[str] = None):
    """Serve a standalone orb frame for external website modes."""
    from fastapi.responses import Response

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    script_path = f"/shopbot-widget.js?site={safe_site}"
    if parent_origin:
        script_path += f"&parent_origin={parent_origin}"

    html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ShopBot</title>
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: transparent;
      }}
      body {{
        position: relative;
      }}
    </style>
  </head>
  <body>
    <script src="{script_path}"></script>
  </body>
</html>"""

    return Response(
        content=html_doc,
        media_type="text/html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/shopbot-widget.js", tags=["Plugin"])
async def serve_plugin_widget(site: Optional[str] = None, site_id: Optional[str] = None, shop: Optional[str] = None):
    """Serve the full widget app for direct use or inside the external embed frame."""
    from fastapi.responses import Response

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = _load_widget_script(site=safe_site, api_base_url=safe_api)

    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/shopbot.js", tags=["Plugin"])
async def serve_plugin(site: Optional[str] = None, site_id: Optional[str] = None, shop: Optional[str] = None):
    """Serve the public widget loader — inlined directly (no iframe).

    The iframe-based bootstrap (_render_embed_bootstrap) fails with free-tier
    ngrok because the interstitial "Visit Site" page blocks iframe loading.
    Serving the full widget JS directly avoids this issue entirely.
    """
    from fastapi.responses import Response

    safe_site = _safe_site_id(site or site_id or shop or config.DEFAULT_SITE_ID)
    safe_api = _public_widget_base_url()
    js_code = _load_widget_script(site=safe_site, api_base_url=safe_api)

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

