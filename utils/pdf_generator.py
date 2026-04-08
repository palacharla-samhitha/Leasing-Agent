# utils/pdf_generator.py
# Generates EJARI Certificate PDF for the leasing workflow
# Uses reportlab — pip install reportlab

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io

# ── MAF Brand Colors ──────────────────────────────────────────────────────────
MAF_DARK = colors.HexColor("#0a2342")
MAF_TEAL = colors.HexColor("#00c4b4")
MAF_LIGHT = colors.HexColor("#f0f4f8")
MAF_GREY = colors.HexColor("#4a5568")
MAF_BORDER = colors.HexColor("#d0d8e0")
WHITE = colors.white


def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "DocTitle", fontSize=20, fontName="Helvetica-Bold",
        textColor=MAF_DARK, alignment=TA_CENTER, spaceAfter=2*mm
    ))
    styles.add(ParagraphStyle(
        "DocSubtitle", fontSize=10, fontName="Helvetica",
        textColor=MAF_GREY, alignment=TA_CENTER, spaceAfter=6*mm
    ))
    styles.add(ParagraphStyle(
        "SectionHead", fontSize=12, fontName="Helvetica-Bold",
        textColor=MAF_DARK, spaceBefore=6*mm, spaceAfter=3*mm
    ))
    styles.add(ParagraphStyle(
        "CellLabel", fontSize=9, fontName="Helvetica",
        textColor=MAF_GREY
    ))
    styles.add(ParagraphStyle(
        "CellValue", fontSize=10, fontName="Helvetica-Bold",
        textColor=MAF_DARK
    ))
    styles.add(ParagraphStyle(
        "FooterNote", fontSize=7, fontName="Helvetica",
        textColor=MAF_GREY, alignment=TA_CENTER, spaceBefore=8*mm
    ))
    styles.add(ParagraphStyle(
        "StampText", fontSize=8, fontName="Helvetica",
        textColor=MAF_GREY, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        "RegNumber", fontSize=14, fontName="Helvetica-Bold",
        textColor=MAF_TEAL, alignment=TA_CENTER, spaceAfter=2*mm
    ))

    return styles


def _header_block(styles):
    return [
        Paragraph("Majid Al Futtaim Properties LLC", styles["DocSubtitle"]),
        Paragraph("EJARI REGISTRATION CERTIFICATE", styles["DocTitle"]),
        HRFlowable(width="100%", thickness=1.5, color=MAF_TEAL,
                    spaceAfter=4*mm, spaceBefore=2*mm),
    ]


def _detail_table(label_value_pairs, styles):
    data = []
    for label, value in label_value_pairs:
        data.append([
            Paragraph(label, styles["CellLabel"]),
            Paragraph(str(value), styles["CellValue"]),
        ])

    t = Table(data, colWidths=[55*mm, 115*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), MAF_LIGHT),
        ("BACKGROUND",    (1, 0), (1, -1), WHITE),
        ("GRID",          (0, 0), (-1, -1), 0.5, MAF_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def generate_ejari_pdf(state: dict) -> bytes:
    cert = state.get("ejari_certificate", {})
    inquiry = state.get("inquiry", {})
    unit = state.get("selected_unit", {})
    lease = state.get("lease_draft", {})
    lead = state.get("lead_score_result", {})

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    styles = _get_styles()
    elements = []

    # ── Header ────────────────────────────────────────────────────────────
    elements += _header_block(styles)

    # ── Registration Number ───────────────────────────────────────────────
    reg_num = cert.get("registration_number", "—")
    elements.append(Paragraph(f"Registration No: {reg_num}", styles["RegNumber"]))
    elements.append(Spacer(1, 4*mm))

    # ── Registration Details ──────────────────────────────────────────────
    elements.append(Paragraph("Registration details", styles["SectionHead"]))

    reg_date = cert.get("registration_date", datetime.now().strftime("%Y-%m-%d"))
    status = cert.get("status", "Registered")

    elements.append(_detail_table([
        ("Registration date", reg_date),
        ("Status", status),
        ("Filed at", cert.get("filed_at", reg_date)),
        ("Jurisdiction", "Dubai — EJARI System"),
    ], styles))
    elements.append(Spacer(1, 4*mm))

    # ── Parties ───────────────────────────────────────────────────────────
    elements.append(Paragraph("Parties", styles["SectionHead"]))

    elements.append(_detail_table([
        ("Landlord", "Majid Al Futtaim Properties LLC"),
        ("Tenant (legal)", inquiry.get("legal_entity_name", cert.get("tenant_legal_name", "—"))),
        ("Tenant (brand)", inquiry.get("brand_name", cert.get("tenant_brand_name", "—"))),
        ("Contact", inquiry.get("contact_name", "—")),
        ("Contact role", inquiry.get("contact_role", "—")),
    ], styles))
    elements.append(Spacer(1, 4*mm))

    # ── Property ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Property", styles["SectionHead"]))

    mall = unit.get("mall", cert.get("property", "—"))
    unit_id = unit.get("unit_id", "—")
    zone = unit.get("zone", "—")
    floor = unit.get("floor", "—")
    size = unit.get("size_sqm", "—")

    elements.append(_detail_table([
        ("Mall", mall),
        ("Unit", unit_id),
        ("Floor / Zone", f"{floor} — {zone}"),
        ("Size", f"{size} sqm"),
    ], styles))
    elements.append(Spacer(1, 4*mm))

    # ── Lease Terms ───────────────────────────────────────────────────────
    elements.append(Paragraph("Lease terms", styles["SectionHead"]))

    annual_rent = lease.get("annual_base_rent_aed", cert.get("annual_rent_aed", 0))
    start = lease.get("lease_start_date", cert.get("lease_start_date", "—"))
    end = lease.get("lease_end_date", cert.get("lease_end_date", "—"))
    rcd = lease.get("rent_commencement_date", "—")
    deposit = lease.get("security_deposit_aed", 0)

    elements.append(_detail_table([
        ("Lease start", start),
        ("Rent commencement", rcd),
        ("Lease end", end),
        ("Annual base rent", f"AED {annual_rent:,.0f}" if isinstance(annual_rent, (int, float)) else str(annual_rent)),
        ("Security deposit", f"AED {deposit:,.0f}" if isinstance(deposit, (int, float)) else str(deposit)),
    ], styles))
    elements.append(Spacer(1, 4*mm))

    # ── Lead Score (for demo impressiveness) ──────────────────────────────
    if lead:
        elements.append(Paragraph("Tenant qualification score", styles["SectionHead"]))
        grade = lead.get("lead_grade", "—")
        score = lead.get("lead_score", 0)
        elements.append(_detail_table([
            ("Lead score", f"{score:.2f}"),
            ("Grade", grade),
            ("Assessment", lead.get("reasoning", "—")),
        ], styles))
        elements.append(Spacer(1, 4*mm))

    # ── Stamp / Legal Note ────────────────────────────────────────────────
    stamp_data = [[
        Paragraph(
            "This certificate confirms that the above lease has been registered "
            "with the EJARI system operated by the Dubai Land Department in accordance "
            "with Decree No. 26 of 2013 and the Real Property Registration Law No. 7 "
            "of 2006. This registration is legally binding and enforceable under UAE law.",
            styles["StampText"]
        )
    ]]
    stamp = Table(stamp_data, colWidths=[170*mm])
    stamp.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), MAF_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    elements.append(stamp)
    elements.append(Spacer(1, 8*mm))

    # ── Signatures ────────────────────────────────────────────────────────
    sig_data = [[
        Paragraph(
            "_______________________________<br/>Leasing Director<br/>Majid Al Futtaim Properties LLC",
            ParagraphStyle("SigL", fontSize=8, fontName="Helvetica",
                           textColor=MAF_DARK, alignment=TA_CENTER)
        ),
        Paragraph(
            f"_______________________________<br/>AI Leasing Agent · Ref<br/>{reg_num}",
            ParagraphStyle("SigR", fontSize=8, fontName="Helvetica",
                           textColor=MAF_DARK, alignment=TA_CENTER)
        ),
    ]]
    sig = Table(sig_data, colWidths=[85*mm, 85*mm])
    sig.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(sig)
    elements.append(Spacer(1, 6*mm))

    # ── Footer ────────────────────────────────────────────────────────────
    elements.append(Paragraph(
        "CONFIDENTIAL · Generated by AI Leasing Agent · ReKnew × MAF Properties · "
        f"{datetime.now().strftime('%d %B %Y')} · Not for distribution",
        styles["FooterNote"]
    ))

    doc.build(elements)
    return buf.getvalue()