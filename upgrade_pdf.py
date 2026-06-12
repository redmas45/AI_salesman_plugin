import os

target = "c:/Users/admin/Desktop/AI_salesman_plugin/api/main.py"
with open(target, 'r', encoding='utf-8') as f:
    text = f.read()

old_pdf_code = """        buffer = io.BytesIO()
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

        doc.build(elements)"""

new_pdf_code = """        import datetime
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

        doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)"""

new_text = text.replace(old_pdf_code, new_pdf_code)

if new_text == text:
    print("No change made. Code block not found.")
else:
    with open(target, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Successfully updated PDF generation code.")
