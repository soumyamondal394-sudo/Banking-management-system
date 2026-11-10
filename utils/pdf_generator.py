import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_statement_pdf(account, transactions, start_date=None, end_date=None):
    """
    Generates an Account Statement PDF using ReportLab for educational banking simulations.
    Returns an io.BytesIO buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#0f2b5c")
    secondary_color = colors.HexColor("#2563eb")
    dark_text = colors.HexColor("#1e293b")
    light_bg = colors.HexColor("#f1f5f9")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b")
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_text
    )

    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=dark_text
    )

    story = []

    # Bank Header
    header_data = [
        [
            Paragraph("<b>APEX GLOBAL BANK</b><br/><font size=8 color='#64748b'>Official Account Statement (Educational Simulation)</font>", title_style),
            Paragraph("<b>Apex Global Bank Ltd.</b><br/>Financial Center, Suite 500<br/>support@apexbank.com | 1-800-555-APEX", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Divider line
    divider = Table([['']], colWidths=[7.5 * inch], rowHeights=[2])
    divider.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), secondary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 15))

    # Account Holder & Statement Summary
    user = account.user
    now_utc = datetime.now(timezone.utc)
    date_range_str = f"{start_date.strftime('%b %d, %Y') if start_date else 'Account Opening'} to {end_date.strftime('%b %d, %Y') if end_date else now_utc.strftime('%b %d, %Y')}"

    summary_data = [
        [
            Paragraph("<b>Account Holder:</b>", cell_bold), Paragraph(user.full_name, cell_style),
            Paragraph("<b>Statement Period:</b>", cell_bold), Paragraph(date_range_str, cell_style)
        ],
        [
            Paragraph("<b>Account Number:</b>", cell_bold), Paragraph(str(account.account_number), cell_style),
            Paragraph("<b>Statement Date:</b>", cell_bold), Paragraph(now_utc.strftime('%b %d, %Y %H:%M UTC'), cell_style)
        ],
        [
            Paragraph("<b>Account Type:</b>", cell_bold), Paragraph(f"{account.account_type} Account", cell_style),
            Paragraph("<b>Available Balance:</b>", cell_bold), Paragraph(f"<b>${float(account.balance):,.2f}</b>", cell_bold)
        ],
        [
            Paragraph("<b>Account Status:</b>", cell_bold), Paragraph(account.status, cell_style),
            Paragraph("<b>Currency:</b>", cell_bold), Paragraph("USD ($)", cell_style)
        ]
    ]

    summary_table = Table(summary_data, colWidths=[1.4 * inch, 2.3 * inch, 1.5 * inch, 2.3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Transactions Header
    story.append(Paragraph("Transaction Activity", h2_style))
    story.append(Spacer(1, 6))

    # Table of transactions
    table_headers = [
        Paragraph("<b>Date</b>", cell_bold),
        Paragraph("<b>Reference ID</b>", cell_bold),
        Paragraph("<b>Description</b>", cell_bold),
        Paragraph("<b>Type</b>", cell_bold),
        Paragraph("<b>Amount</b>", cell_bold),
        Paragraph("<b>Balance</b>", cell_bold)
    ]
    
    rows = [table_headers]

    for txn in transactions:
        sign = "+" if txn.is_credit else "-"
        amt_color = "#16a34a" if txn.is_credit else "#dc2626"
        amount_styled = Paragraph(f"<font color='{amt_color}'><b>{sign}${float(txn.amount):,.2f}</b></font>", cell_style)
        type_str = txn.transaction_type.replace('_', ' ').title()
        
        rows.append([
            Paragraph(txn.timestamp.strftime('%Y-%m-%d %H:%M'), cell_style),
            Paragraph(txn.reference_id, cell_style),
            Paragraph(txn.description or '-', cell_style),
            Paragraph(type_str, cell_style),
            amount_styled,
            Paragraph(f"${float(txn.balance_after):,.2f}", cell_style)
        ])

    if len(rows) == 1:
        rows.append([
            Paragraph("No transactions recorded for this period.", cell_style),
            "", "", "", "", ""
        ])

    txn_table = Table(rows, colWidths=[1.1 * inch, 1.4 * inch, 2.1 * inch, 1.1 * inch, 0.9 * inch, 0.9 * inch], repeatRows=1)
    
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
    ]
    for i in range(len(table_headers)):
        table_headers[i].style.textColor = colors.white

    for r in range(1, len(rows)):
        if r % 2 == 0:
            t_style.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor("#f8fafc")))

    txn_table.setStyle(TableStyle(t_style))
    story.append(txn_table)
    story.append(Spacer(1, 20))

    footer_text = Paragraph(
        "<i>Notice: This statement is generated for educational simulation purposes. "
        "Apex Global Bank educational project demonstration.</i>",
        subtitle_style
    )
    story.append(KeepTogether([footer_text]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_receipt_pdf(transaction):
    """
    Generates a PDF transaction receipt for a single transaction.
    Returns an io.BytesIO buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#0f2b5c")

    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        alignment=1
    )

    sub_style = ParagraphStyle(
        'ReceiptSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        alignment=1
    )

    label_style = ParagraphStyle(
        'ReceiptLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    val_style = ParagraphStyle(
        'ReceiptVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )

    amt_style = ParagraphStyle(
        'ReceiptAmt',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=1
    )

    story = []

    story.append(Paragraph("APEX GLOBAL BANK", title_style))
    story.append(Paragraph("Transaction Receipt & Payment Confirmation (Educational Simulation)", sub_style))
    story.append(Spacer(1, 15))

    sign = "+" if transaction.is_credit else "-"
    story.append(Paragraph(f"{sign}${float(transaction.amount):,.2f}", amt_style))
    story.append(Paragraph(f"Status: <font color='#16a34a'><b>{transaction.status}</b></font>", sub_style))
    story.append(Spacer(1, 15))

    account = transaction.account
    user = account.user

    table_data = [
        [Paragraph("Transaction Reference", label_style), Paragraph(transaction.reference_id, val_style)],
        [Paragraph("Date & Time", label_style), Paragraph(transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), val_style)],
        [Paragraph("Transaction Type", label_style), Paragraph(transaction.transaction_type.replace('_', ' ').title(), val_style)],
        [Paragraph("Account Holder", label_style), Paragraph(user.full_name, val_style)],
        [Paragraph("Account Number", label_style), Paragraph(account.formatted_account_number, val_style)],
        [Paragraph("Description", label_style), Paragraph(transaction.description or 'Banking Operation', val_style)],
        [Paragraph("Sender Account", label_style), Paragraph(transaction.sender_account_number or account.account_number, val_style)],
        [Paragraph("Receiver Account", label_style), Paragraph(transaction.receiver_account_number or '-', val_style)],
        [Paragraph("Balance After Transaction", label_style), Paragraph(f"${float(transaction.balance_after):,.2f}", val_style)],
    ]

    receipt_table = Table(table_data, colWidths=[2.5 * inch, 4.0 * inch])
    receipt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))

    story.append(receipt_table)
    story.append(Spacer(1, 20))

    note = Paragraph("Educational Banking Management System Project. For educational and testing purposes only.", sub_style)
    story.append(note)

    doc.build(story)
    buffer.seek(0)
    return buffer
