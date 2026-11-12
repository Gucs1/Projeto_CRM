"""Gera propostas PDF paginadas, com dados de cadastro e snapshots do orçamento."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 42
NAVY = colors.HexColor("#172554")
BLUE = colors.HexColor("#2563EB")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748B")
PALE = colors.HexColor("#F1F5F9")
GRID = colors.HexColor("#E2E8F0")
WHITE = colors.white
STATUS_STYLES = {
    "Enviado": (colors.HexColor("#1D4ED8"), colors.HexColor("#DBEAFE")),
    "Aprovado": (colors.HexColor("#047857"), colors.HexColor("#D1FAE5")),
    "Recusado": (colors.HexColor("#BE123C"), colors.HexColor("#FFE4E6")),
}
PRIORITY_STYLES = {
    "Baixa": (colors.HexColor("#047857"), colors.HexColor("#D1FAE5")),
    "Média": (colors.HexColor("#B45309"), colors.HexColor("#FEF3C7")),
    "Alta": (colors.HexColor("#BE123C"), colors.HexColor("#FFE4E6")),
}


def format_brl(cents: int) -> str:
    value = int(cents)
    whole = f"{value // 100:,}".replace(",", ".")
    return f"R$ {whole},{value % 100:02d}"


def _paragraph(value, style: ParagraphStyle, *, line_breaks: bool = False) -> Paragraph:
    text = escape(str(value or "Não informado"))
    if line_breaks:
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")
    return Paragraph(text, style)


class StatusTag(Flowable):
    """Status colorido com ícone vetorial, sem dependência de glifos externos."""

    def __init__(self, status: str):
        super().__init__()
        self.status = status
        self.foreground, self.background = STATUS_STYLES.get(status, STATUS_STYLES["Enviado"])
        self.width = 98
        self.height = 24

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(self.background)
        canvas.roundRect(0, 0, self.width, self.height, 8, stroke=0, fill=1)
        canvas.setStrokeColor(self.foreground)
        canvas.setLineWidth(1.2)
        cx, cy = 13, self.height / 2
        if self.status == "Aprovado":
            canvas.line(cx - 3, cy, cx - 0.5, cy - 2.5)
            canvas.line(cx - 0.5, cy - 2.5, cx + 4, cy + 3)
        elif self.status == "Recusado":
            canvas.line(cx - 3, cy - 3, cx + 3, cy + 3)
            canvas.line(cx - 3, cy + 3, cx + 3, cy - 3)
        else:
            canvas.line(cx - 4, cy, cx + 4, cy)
            canvas.line(cx + 1, cy - 3, cx + 4, cy)
            canvas.line(cx + 1, cy + 3, cx + 4, cy)
        canvas.setFillColor(self.foreground)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(23, 8, self.status)
        canvas.restoreState()


class PriorityTag(Flowable):
    """Prioridade legível e colorida na proposta, sem glifos especiais."""

    def __init__(self, priority: str):
        super().__init__()
        self.priority = priority
        self.foreground, self.background = PRIORITY_STYLES.get(
            priority, PRIORITY_STYLES["Média"]
        )
        self.width = 108
        self.height = 24

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(self.background)
        canvas.roundRect(0, 0, self.width, self.height, 8, stroke=0, fill=1)
        canvas.setFillColor(self.foreground)
        canvas.circle(12, self.height / 2, 3, stroke=0, fill=1)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(20, 8, f"Prioridade {self.priority}")
        canvas.restoreState()


def _make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "QuoteTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, textColor=NAVY, alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "subtitle": ParagraphStyle(
            "QuoteSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=12, textColor=MUTED,
        ),
        "section": ParagraphStyle(
            "QuoteSection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10, leading=13, textColor=NAVY, spaceBefore=2, spaceAfter=8,
        ),
        "label": ParagraphStyle(
            "QuoteLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7, leading=9, textColor=MUTED, uppercase=True,
        ),
        "body": ParagraphStyle(
            "QuoteBody", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=12, textColor=INK, wordWrap="CJK",
        ),
        "body_bold": ParagraphStyle(
            "QuoteBodyBold", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=INK, wordWrap="CJK",
        ),
        "item": ParagraphStyle(
            "QuoteItem", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=11, textColor=INK, wordWrap="CJK",
            splitLongWords=1,
        ),
        "table_header": ParagraphStyle(
            "QuoteTableHeader", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9, textColor=WHITE,
        ),
        "table_header_right": ParagraphStyle(
            "QuoteTableHeaderRight", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=9, textColor=WHITE, alignment=TA_RIGHT,
        ),
        "number": ParagraphStyle(
            "QuoteNumber", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=11, textColor=INK, alignment=TA_RIGHT,
        ),
        "total_label": ParagraphStyle(
            "QuoteTotalLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10, leading=13, textColor=NAVY, alignment=TA_RIGHT,
        ),
        "total_value": ParagraphStyle(
            "QuoteTotalValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=NAVY, alignment=TA_RIGHT,
            splitLongWords=1,
        ),
    }


def _draw_company_mark(canvas, logo_path: str | Path | None, company_name: str) -> None:
    x, y, width, height = MARGIN, PAGE_HEIGHT - 82, 50, 44
    if logo_path:
        logo = Path(logo_path)
        if logo.is_file():
            try:
                canvas.drawImage(
                    ImageReader(str(logo)), x, y, width, height,
                    preserveAspectRatio=True, anchor="c", mask="auto",
                )
                return
            except (OSError, ValueError):
                pass
    canvas.setFillColor(BLUE)
    canvas.roundRect(x, y, width, height, 10, stroke=0, fill=1)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(x + width / 2, y + 12, "M")


def _draw_page_chrome(company: dict, logo_path: str | Path | None):
    def draw(canvas, document):
        canvas.saveState()
        _draw_company_mark(canvas, logo_path, company.get("name", "Empresa"))

        name_style = ParagraphStyle(
            "CompanyName", fontName="Helvetica-Bold", fontSize=12,
            leading=15, textColor=NAVY,
        )
        contact_style = ParagraphStyle(
            "CompanyContact", fontName="Helvetica", fontSize=7.5,
            leading=10, textColor=MUTED,
        )
        name = Paragraph(escape(company.get("name") or "Empresa"), name_style)
        name_width = PAGE_WIDTH - MARGIN * 2 - 64
        _, name_height = name.wrap(name_width, 32)
        name.drawOn(canvas, MARGIN + 62, PAGE_HEIGHT - 43 - name_height)

        contacts = [
            company.get("address", ""),
            company.get("phone", ""),
            company.get("email", ""),
        ]
        contacts = [escape(value.strip()) for value in contacts if value and value.strip()]
        if contacts:
            contact = Paragraph("  |  ".join(contacts), contact_style)
            _, contact_height = contact.wrap(name_width, 24)
            contact.drawOn(canvas, MARGIN + 62, PAGE_HEIGHT - 62 - contact_height)

        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.7)
        canvas.line(MARGIN, PAGE_HEIGHT - 101, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 101)
        canvas.line(MARGIN, 39, PAGE_WIDTH - MARGIN, 39)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(MARGIN, 25, "Proposta comercial")
        canvas.drawRightString(PAGE_WIDTH - MARGIN, 25, f"Página {document.page}")
        canvas.restoreState()

    return draw


def generate_quote_pdf(quote, items, company: dict, logo_path: str | Path | None = None) -> bytes:
    """Retorna um PDF A4 em memória, com cabeçalhos e rodapés em todas as páginas."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=122,
        bottomMargin=55,
        title=f"Orçamento {quote['id']} - {quote['client_name']}",
        author=company.get("name", "CRM de Orçamentos"),
        subject=f"Proposta comercial {quote['id']}",
    )
    styles = _make_styles()
    story = []
    story.append(Paragraph(f"Orçamento #{quote['id']}", styles["title"]))
    story.append(Spacer(1, 4))

    try:
        quote_date = datetime.fromisoformat(str(quote["created_at"])).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        quote_date = str(quote["created_at"])[:10]
    metadata = Table(
        [[Paragraph(f"Data: <b>{escape(quote_date)}</b>", styles["subtitle"]), PriorityTag(quote["priority"]), StatusTag(quote["status"])]],
        colWidths=[document.width - 208, 110, 98],
        hAlign="LEFT",
    )
    metadata.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([metadata, Spacer(1, 16), Paragraph("DADOS DO CLIENTE", styles["section"])])

    primary_lines = [f"<b>{escape(str(quote['client_name']))}</b>"]
    if quote["client_company"]:
        primary_lines.append(escape(str(quote["client_company"])))
    contact_lines = [
        escape(str(value))
        for value in (quote["client_email"], quote["client_phone"])
        if value
    ] or ["Não informado"]
    client_primary = Paragraph(
        "<font size='7' color='#64748B'><b>CLIENTE</b></font><br/>" + "<br/>".join(primary_lines),
        styles["body"],
    )
    client_contact = Paragraph(
        "<font size='7' color='#64748B'><b>CONTATO</b></font><br/>" + "<br/>".join(contact_lines),
        styles["body"],
    )

    client_panel = Table(
        [[client_primary, client_contact]],
        colWidths=[document.width * 0.53, document.width * 0.47],
        hAlign="LEFT",
    )
    client_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([client_panel, Spacer(1, 17), Paragraph("ITENS E VALORES", styles["section"])])

    header = [
        Paragraph("#", styles["table_header"]),
        Paragraph("PRODUTO OU SERVIÇO", styles["table_header"]),
        Paragraph("QTD.", styles["table_header_right"]),
        Paragraph("VALOR UNITÁRIO", styles["table_header_right"]),
        Paragraph("SUBTOTAL", styles["table_header_right"]),
    ]
    rows = [header]
    for index, item in enumerate(items, start=1):
        product_lines = [f"<b>{escape(str(item['product_name']))}</b>"]
        if item["description"]:
            escaped_description = escape(str(item["description"])).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")
            product_lines.append(f"<font color='#64748B'>{escaped_description}</font>")
        rows.append([
            Paragraph(str(index), styles["number"]),
            Paragraph("<br/>".join(product_lines), styles["item"]),
            Paragraph(f"{item['quantity']:,}".replace(",", "."), styles["number"]),
            Paragraph(escape(format_brl(item["unit_price_cents"])), styles["number"]),
            Paragraph(escape(format_brl(item["line_total_cents"])), styles["number"]),
        ])

    col_widths = [25, document.width - 25 - 42 - 108 - 112, 42, 108, 112]
    item_table = LongTable(
        rows,
        colWidths=col_widths,
        repeatRows=1,
        splitByRow=1,
        splitInRow=0,
        hAlign="LEFT",
    )
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([item_table, Spacer(1, 10)])

    total = Table(
        [[Paragraph("TOTAL DO ORÇAMENTO", styles["total_label"]),
          Paragraph(escape(format_brl(quote["total_cents"])), styles["total_value"])]],
        colWidths=[document.width - 150, 150],
        hAlign="LEFT",
    )
    total.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("LINEABOVE", (0, 0), (-1, 0), 1, BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(total)

    if quote["notes"]:
        story.extend([Spacer(1, 18), Paragraph("OBSERVAÇÕES", styles["section"])])
        story.append(_paragraph(quote["notes"], styles["body"], line_breaks=True))

    document.build(
        story,
        onFirstPage=_draw_page_chrome(company, logo_path),
        onLaterPages=_draw_page_chrome(company, logo_path),
    )
    return buffer.getvalue()
