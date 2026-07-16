"""Invoice PDF helpers for ecommerce checkout routes."""

from __future__ import annotations

import datetime
import io
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from fastapi import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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


@dataclass(frozen=True)
class CheckoutProfile:
    address: str
    payment_method: str


def build_invoice_pdf(items: list[dict[str, Any]], profile: CheckoutProfile, brand_name: str) -> bytes:
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


def invoice_response(pdf_bytes: bytes) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={INVOICE_FILENAME}"},
    )


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


def _invoice_items_element(items: list[dict[str, Any]]) -> Table:
    table = Table(_invoice_table_data(items), colWidths=INVOICE_TABLE_COL_WIDTHS)
    table.setStyle(_invoice_table_style())
    return table


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


def _short_invoice_item_name(name: Any) -> str:
    item_name = str(name or "")
    return item_name[:50] + ("..." if len(item_name) > 50 else "")


def _format_invoice_money(value: float) -> str:
    return f"{INVOICE_CURRENCY} {value:.2f}"


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
