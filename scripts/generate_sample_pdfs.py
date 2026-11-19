import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors


def generate_pdf_from_text(txt_path: str, pdf_path: str, title: str):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=14
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563EB'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    story = []
    lines = text.split("\n")

    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.startswith("==="):
            continue
        if line_s.isupper() and len(line_s) > 10:
            story.append(Paragraph(line_s, title_style))
            story.append(Spacer(1, 10))
        elif line_s[0].isdigit() and "." in line_s[:4]:
            story.append(Paragraph(line_s, section_style))
        else:
            story.append(Paragraph(line_s, body_style))

    doc.build(story)
    print(f"Generated PDF: {pdf_path}")


def main():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "sample-data", "policies")
    files = [
        ("return_policy.txt", "return_policy.pdf", "Customer Returns & Exchanges Policy"),
        ("refund_policy.txt", "refund_policy.pdf", "Refund Issuance & Financial Workflows Policy"),
        ("shipping_sla_policy.txt", "shipping_sla_policy.pdf", "Logistics SLA & Delivery Delays Policy"),
        ("payment_discrepancy_policy.txt", "payment_discrepancy_policy.pdf", "Payment Discrepancies & Orphan Charges Policy"),
        ("damaged_goods_policy.txt", "damaged_goods_policy.pdf", "Damaged, Defective & DOA Merchandise Policy"),
    ]

    for txt_file, pdf_file, title in files:
        txt_path = os.path.join(base_dir, txt_file)
        pdf_path = os.path.join(base_dir, pdf_file)
        if os.path.exists(txt_path):
            generate_pdf_from_text(txt_path, pdf_path, title)


if __name__ == "__main__":
    main()

