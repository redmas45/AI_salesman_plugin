"""Ecommerce-only product, cart, checkout, and catalog routes."""

from __future__ import annotations

import datetime
import io
import logging
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

import psycopg
from fastapi import APIRouter, HTTPException, Response, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config
from api.models import AddToCartRequest, CartItemResponse, CheckoutRequest, ProductResponse, VariantResponse
from db import admin as admin_db
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
    get_product_variants,
    get_user_profile,
    remove_from_cart,
    tenant_catalog_preview,
    tenant_catalog_stats,
    update_user_profile,
)

logger = logging.getLogger(__name__)

CHECKOUT_EMPTY_VALUES = {"", "N/A", "Not Provided"}
CHECKOUT_DEFAULT_VALUE = "Not Provided"
INVOICE_DEFAULT_BRAND_NAME = "Client"
INVOICE_TITLE = "PREMIUM INVOICE"
INVOICE_FILENAME = "bill.pdf"
INVOICE_CURRENCY = "INR"
INVOICE_HEADER_COLOR = "#2c3e50"
INVOICE_TEXT_COLOR = "#34495e"
INVOICE_ACCENT_COLOR = "#1abc9c"
INVOICE_MUTED_COLOR = "#95a5a6"
INVOICE_TABLE_BACKGROUND = "#f8f9fa"
INVOICE_TABLE_GRID = "#dee2e6"
INVOICE_PAGE_MARGIN = 60
INVOICE_BORDER_MARGIN = 30
INVOICE_HEADER_HEIGHT = 100
INVOICE_HEADER_TOP_OFFSET = 130
INVOICE_TITLE_FONT_SIZE = 36
INVOICE_SUBTITLE_FONT_SIZE = 14
INVOICE_TABLE_COL_WIDTHS = [240, 90, 50, 110]
INVOICE_TOP_MARGIN = 150
DEFAULT_CRAWLER_SOURCE_NAME = "custom_url_crawler"

router = APIRouter(tags=["Ecommerce"])


@dataclass(frozen=True)
class CheckoutProfile:
    address: str
    payment_method: str


@router.get("/v1/products", response_model=list[ProductResponse], tags=["Products"])
async def list_products(
    site_id: str = config.DEFAULT_SITE_ID,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ProductResponse]:
    """Return active ecommerce products for a tenant."""
    try:
        products = _products_for_request(site_id=site_id, category=category, limit=limit, offset=offset)
        return [ProductResponse(**product) for product in products]
    except psycopg.Error as exc:
        logger.error("GET /v1/products failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch products.") from exc


@router.get("/v1/products/by-ids", response_model=list[ProductResponse], tags=["Products"])
async def list_products_by_ids(ids: str, site_id: str = config.DEFAULT_SITE_ID) -> list[ProductResponse]:
    """Fetch ecommerce products by a comma-separated ID list."""
    try:
        from db.database import get_products_by_ids

        products = get_products_by_ids(site_id, _parse_product_ids(ids))
        return [ProductResponse(**product) for product in products]
    except psycopg.Error as exc:
        logger.error("GET /v1/products/by-ids failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products by IDs.",
        ) from exc


@router.get("/v1/products/{product_id}/variants", response_model=list[VariantResponse], tags=["Products"])
async def list_product_variants(
    product_id: int,
    site_id: str = config.DEFAULT_SITE_ID,
) -> list[VariantResponse]:
    """Return all known variants for one ecommerce product."""
    try:
        variants = get_product_variants(site_id, product_id)
        return [VariantResponse(**variant) for variant in variants]
    except psycopg.Error as exc:
        logger.error("GET /v1/products/{product_id}/variants failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch product variants.",
        ) from exc


@router.get("/v1/categories", tags=["Products"])
async def list_categories(site_id: str = config.DEFAULT_SITE_ID) -> list[dict[str, str]]:
    """Return active ecommerce category names and slugs."""
    try:
        from db.database import get_db

        with get_db(site_id) as conn:
            rows = conn.execute("SELECT name, slug FROM categories ORDER BY name ASC").fetchall()
            return [{"name": row["name"], "slug": row["slug"]} for row in rows]
    except psycopg.Error as exc:
        logger.error("GET /v1/categories failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories.",
        ) from exc


@router.get("/v1/catalog/status", tags=["Products"])
async def catalog_status(site_id: str = config.DEFAULT_SITE_ID) -> dict[str, Any]:
    """Return ecommerce catalog/RAG sync status for a tenant site."""
    try:
        source_stats = catalog_source_stats(site_id)
        preview_source = _preview_source_name(source_stats)
        return {
            "site_id": site_id,
            "catalog": tenant_catalog_stats(site_id),
            "sources": source_stats,
            "recent_sync_runs": catalog_sync_history(site_id, limit=8),
            "catalog_preview": tenant_catalog_preview(site_id, limit=12),
            "source_preview": _catalog_source_preview(site_id, source_stats, preview_source),
        }
    except psycopg.Error as exc:
        logger.error("GET /v1/catalog/status failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch catalog status.",
        ) from exc


@router.get("/v1/cart", response_model=list[CartItemResponse], tags=["Cart"])
async def get_cart(site_id: str = config.DEFAULT_SITE_ID) -> list[CartItemResponse]:
    """Return all ecommerce cart items for a tenant."""
    try:
        items = get_cart_items(site_id)
        return [CartItemResponse(**item) for item in items]
    except psycopg.Error as exc:
        logger.error("GET /v1/cart failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch cart.") from exc


@router.post("/v1/cart/add", tags=["Cart"])
async def api_add_to_cart(req: AddToCartRequest) -> dict[str, Any]:
    """Add an ecommerce product to the tenant cart."""
    try:
        cart_id = add_to_cart(req.site_id, req.product_id, req.quantity)
        return {"status": "ok", "cart_id": cart_id}
    except InvalidProductIdError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.error("POST /v1/cart/add failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add to cart.") from exc


@router.post("/v1/cart/update", tags=["Cart"])
async def api_update_cart(req: AddToCartRequest) -> dict[str, str]:
    """Update an ecommerce cart product quantity."""
    try:
        from db.database import update_cart_quantity

        if not update_cart_quantity(req.site_id, req.product_id, req.quantity):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found in cart.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        logger.error("POST /v1/cart/update failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update cart.") from exc


@router.delete("/v1/cart/{cart_id}", tags=["Cart"])
async def api_remove_from_cart(cart_id: int, site_id: str = config.DEFAULT_SITE_ID) -> dict[str, str]:
    """Remove one ecommerce cart row."""
    try:
        if not remove_from_cart(site_id, cart_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart.")
        return {"status": "ok"}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        logger.error("DELETE /v1/cart/{cart_id} failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to remove from cart.") from exc


@router.delete("/v1/cart", tags=["Cart"])
async def api_clear_cart(site_id: str = config.DEFAULT_SITE_ID) -> dict[str, str]:
    """Clear all ecommerce cart rows for a tenant."""
    try:
        clear_cart(site_id)
        return {"status": "ok"}
    except psycopg.Error as exc:
        logger.error("DELETE /v1/cart failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to clear cart.") from exc


@router.post("/v1/cart/checkout", tags=["Cart"])
async def api_checkout_cart(req: CheckoutRequest) -> Response:
    """Generate an ecommerce PDF bill and clear the cart."""
    try:
        items = _checkout_items(req)
        if not items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")

        profile = _resolve_checkout_profile(req)
        update_user_profile(req.site_id, profile.address, profile.payment_method)
        _checkout_cart(req.site_id)
        return _invoice_response(_build_invoice_pdf(items, profile, _invoice_brand_name(req.site_id)))
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid checkout item data.") from exc
    except psycopg.Error as exc:
        logger.error("POST /v1/cart/checkout failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process checkout.",
        ) from exc


def vectorize_site_catalog(site_id: str) -> None:
    """Vectorize legacy ecommerce products, then sync generic knowledge rows."""
    logger.info("Background ecommerce vectorization started for site %s...", site_id)
    try:
        product_count = _vectorize_missing_products(site_id)
        knowledge_count = _sync_catalog_knowledge(site_id)
        logger.info(
            "Ecommerce vectorization complete for site %s: %d products, %d knowledge rows.",
            site_id,
            product_count,
            knowledge_count,
        )
    except (psycopg.Error, RuntimeError) as exc:
        logger.error("Background ecommerce vectorization failed for site %s: %s", site_id, exc)


def _products_for_request(site_id: str, category: str | None, limit: int, offset: int) -> list[dict[str, Any]]:
    if category:
        from db.database import get_products_by_category

        return get_products_by_category(site_id, category, limit=limit)
    return get_all_products(site_id, limit=limit, offset=offset)


def _parse_product_ids(raw_ids: str) -> list[int]:
    product_ids: list[int] = []
    for raw_id in str(raw_ids or "").split(","):
        parsed_id = _coerce_optional_product_id(raw_id)
        if parsed_id is not None:
            product_ids.append(parsed_id)
    return product_ids


def _coerce_optional_product_id(raw_id: str) -> int | None:
    cleaned_id = raw_id.strip().strip('"')
    if not cleaned_id:
        return None
    try:
        return coerce_product_id(cleaned_id)
    except InvalidProductIdError:
        return None


def _preview_source_name(source_stats: list[dict[str, Any]]) -> str:
    if not source_stats:
        return DEFAULT_CRAWLER_SOURCE_NAME
    return str(source_stats[0].get("source_name") or DEFAULT_CRAWLER_SOURCE_NAME)


def _catalog_source_preview(site_id: str, source_stats: list[dict[str, Any]], source_name: str) -> list[dict[str, Any]]:
    if not source_stats:
        return []
    return catalog_source_preview(site_id, source_name, limit=12)


def _checkout_items(req: CheckoutRequest) -> list[dict[str, Any]]:
    if not req.items:
        return get_cart_items(req.site_id)
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "quantity": item.quantity,
        }
        for item in req.items
    ]


def _provided_checkout_value(value: str | None) -> bool:
    return bool(value and value.strip() not in CHECKOUT_EMPTY_VALUES)


def _resolve_checkout_field(candidate: str | None, stored_value: Any) -> str:
    if _provided_checkout_value(candidate):
        return str(candidate).strip()
    stored_text = str(stored_value or "").strip()
    if stored_text and stored_text not in CHECKOUT_EMPTY_VALUES:
        return stored_text
    return CHECKOUT_DEFAULT_VALUE


def _resolve_checkout_profile(req: CheckoutRequest) -> CheckoutProfile:
    profile = get_user_profile(req.site_id)
    return CheckoutProfile(
        address=_resolve_checkout_field(req.address, profile.get("address")),
        payment_method=_resolve_checkout_field(req.payment_method, profile.get("payment_method")),
    )


def _checkout_cart(site_id: str) -> None:
    from db.database import checkout_cart

    checkout_cart(site_id)


def _invoice_brand_name(site_id: str) -> str:
    try:
        client = admin_db.get_client_detail(site_id)
    except (LookupError, psycopg.Error):
        return str(site_id or INVOICE_DEFAULT_BRAND_NAME)
    return str(client.get("name") or site_id or INVOICE_DEFAULT_BRAND_NAME)


def _draw_invoice_page(canvas: Any, _doc: Any, brand_name: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(INVOICE_HEADER_COLOR))
    canvas.setLineWidth(2)
    canvas.rect(
        INVOICE_BORDER_MARGIN,
        INVOICE_BORDER_MARGIN,
        letter[0] - (INVOICE_BORDER_MARGIN * 2),
        letter[1] - (INVOICE_BORDER_MARGIN * 2),
    )
    canvas.setFillColor(colors.HexColor(INVOICE_HEADER_COLOR))
    canvas.rect(
        INVOICE_BORDER_MARGIN,
        letter[1] - INVOICE_HEADER_TOP_OFFSET,
        letter[0] - (INVOICE_BORDER_MARGIN * 2),
        INVOICE_HEADER_HEIGHT,
        fill=1,
        stroke=0,
    )
    canvas.setFont("Helvetica-Bold", INVOICE_TITLE_FONT_SIZE)
    canvas.setFillColor(colors.white)
    canvas.drawString(INVOICE_PAGE_MARGIN, letter[1] - 85, brand_name)
    canvas.setFont("Helvetica", INVOICE_SUBTITLE_FONT_SIZE)
    canvas.drawString(INVOICE_PAGE_MARGIN, letter[1] - 110, INVOICE_TITLE)
    canvas.restoreState()


def _invoice_metadata_elements(styles: dict[str, Any]) -> list[Any]:
    now = datetime.datetime.now()
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor(INVOICE_TEXT_COLOR),
        alignment=2,
    )
    metadata = f"<b>Date:</b> {now:%B %d, %Y}<br/><b>Invoice #:</b> INV-{int(now.timestamp())}"
    return [Paragraph(metadata, meta_style), Spacer(1, 20)]


def _invoice_customer_elements(styles: dict[str, Any], profile: CheckoutProfile) -> list[Any]:
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(INVOICE_HEADER_COLOR),
    )
    customer_html = (
        f"<b>Billed To:</b><br/>{escape(profile.address)}<br/><br/>"
        f"<b>Payment Method:</b><br/>{escape(profile.payment_method)}"
    )
    return [Paragraph(customer_html, info_style), Spacer(1, 30)]


def _short_invoice_item_name(name: Any) -> str:
    item_name = str(name or "")
    return item_name[:50] + ("..." if len(item_name) > 50 else "")


def _format_invoice_money(value: float) -> str:
    return f"{INVOICE_CURRENCY} {value:.2f}"


def _invoice_table_data(items: list[dict[str, Any]]) -> list[list[str]]:
    rows = [["Description", "Unit Price", "Qty", "Total"]]
    total_amount = 0.0
    for item in items:
        rows.append(_invoice_item_row(item))
        total_amount += float(item["price"]) * int(item["quantity"])
    rows.extend(_invoice_total_rows(total_amount))
    return rows


def _invoice_item_row(item: dict[str, Any]) -> list[str]:
    item_price = float(item["price"])
    item_quantity = int(item["quantity"])
    return [
        _short_invoice_item_name(item["name"]),
        _format_invoice_money(item_price),
        str(item_quantity),
        _format_invoice_money(item_price * item_quantity),
    ]


def _invoice_total_rows(total_amount: float) -> list[list[str]]:
    return [
        ["", "", "Subtotal:", _format_invoice_money(total_amount)],
        ["", "", "Tax (0%):", _format_invoice_money(0.0)],
        ["", "", "Grand Total:", _format_invoice_money(total_amount)],
    ]


def _invoice_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INVOICE_HEADER_COLOR)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("TOPPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -4), colors.HexColor(INVOICE_TABLE_BACKGROUND)),
            ("GRID", (0, 0), (-1, -4), 1, colors.HexColor(INVOICE_TABLE_GRID)),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ("TOPPADDING", (0, 1), (-1, -1), 10),
            ("FONTNAME", (2, -3), (3, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (2, -1), (3, -1), colors.HexColor(INVOICE_ACCENT_COLOR)),
            ("FONTSIZE", (2, -1), (3, -1), 13),
            ("LINEABOVE", (2, -3), (3, -3), 1, colors.HexColor(INVOICE_HEADER_COLOR)),
            ("LINEABOVE", (2, -1), (3, -1), 2, colors.HexColor(INVOICE_HEADER_COLOR)),
        ]
    )


def _invoice_items_element(items: list[dict[str, Any]]) -> Table:
    table = Table(_invoice_table_data(items), colWidths=INVOICE_TABLE_COL_WIDTHS)
    table.setStyle(_invoice_table_style())
    return table


def _invoice_footer_elements(styles: dict[str, Any], brand_name: str) -> list[Any]:
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        alignment=1,
        textColor=colors.HexColor(INVOICE_MUTED_COLOR),
        fontSize=10,
        fontName="Helvetica-Oblique",
    )
    footer = f"Thank you for choosing {escape(brand_name)}.<br/>This is an automatically generated receipt."
    return [Spacer(1, 60), Paragraph(footer, footer_style)]


def _invoice_elements(items: list[dict[str, Any]], profile: CheckoutProfile, brand_name: str) -> list[Any]:
    styles = getSampleStyleSheet()
    return [
        *_invoice_metadata_elements(styles),
        *_invoice_customer_elements(styles, profile),
        _invoice_items_element(items),
        *_invoice_footer_elements(styles, brand_name),
    ]


def _build_invoice_pdf(items: list[dict[str, Any]], profile: CheckoutProfile, brand_name: str) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=INVOICE_PAGE_MARGIN,
        leftMargin=INVOICE_PAGE_MARGIN,
        topMargin=INVOICE_TOP_MARGIN,
        bottomMargin=INVOICE_PAGE_MARGIN,
    )
    document.build(
        _invoice_elements(items, profile, brand_name),
        onFirstPage=lambda canvas, doc: _draw_invoice_page(canvas, doc, brand_name),
        onLaterPages=lambda canvas, doc: _draw_invoice_page(canvas, doc, brand_name),
    )
    return buffer.getvalue()


def _invoice_response(pdf_bytes: bytes) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={INVOICE_FILENAME}"},
    )


def _vectorize_missing_products(site_id: str) -> int:
    from agent.rag import _embed, _product_to_text
    from db.database import get_db

    with get_db(site_id) as conn:
        rows = conn.execute(
            """
            SELECT p.*, c.name AS category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.embedding IS NULL
            """
        ).fetchall()
        if not rows:
            return 0

        embeddings = _embed([_product_to_text(dict(row)) for row in rows])
        for index, row in enumerate(rows):
            conn.execute("UPDATE products SET embedding = %s WHERE id = %s", (embeddings[index], row["id"]))
        return len(rows)


def _sync_catalog_knowledge(site_id: str) -> int:
    from agent.retrieval.generic_rag import vectorize_missing_knowledge
    from db.knowledge import sync_products_to_knowledge

    sync_products_to_knowledge(site_id, "manual_vectorize")
    return vectorize_missing_knowledge(site_id)
