from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

def create_pdf_report(analysis, ai_summary=None):
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm)
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name='Small',parent=styles['BodyText'],fontSize=8,leading=11))
    story=[]; d=analysis['dataset']; navy=colors.HexColor('#10243a'); teal=colors.HexColor('#0e9f8a')
    story += [Paragraph('TRACEPOINT',styles['Title']),Paragraph('EXECUTIVE DATA INTELLIGENCE REPORT',styles['Heading2']),Spacer(1,5*mm),Paragraph('Dataset overview',styles['Heading2'])]
    rows=[['Metric','Value'],['Records',f"{d['rows']:,}"],['Columns',str(d['columns'])],['Numeric / categorical',f"{d['numeric_columns']} / {d['categorical_columns']}"],['Completeness',f"{d['completeness']}%"],['Missing cells',f"{d['missing_cells']:,} ({d['missing_percentage']}%)"],['Duplicate rows',f"{d['duplicate_rows']:,}"]]
    t=Table(rows,colWidths=[85*mm,85*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#f1f6f8')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d5e0e7')),('PADDING',(0,0),(-1,-1),7)])); story += [t,Spacer(1,5*mm),Paragraph('Executive findings',styles['Heading2'])]
    for item in analysis.get('insights',[]): story.append(Paragraph('• '+str(item),styles['BodyText'])); story.append(Spacer(1,2*mm))
    story += [Spacer(1,3*mm),Paragraph('Management questions and answers',styles['Heading2'])]
    for q in analysis.get('questions',[]): story += [Paragraph('<b>'+q['question']+'</b>',styles['BodyText']),Paragraph(q['answer'],styles['Small']),Spacer(1,2*mm)]
    story += [Paragraph('Prediction assessment',styles['Heading2'])]
    f=analysis.get('forecast') or {}
    forecast_text = (f"Exploratory estimate for {f.get('column')}: {f.get('next_estimate')} (range {f.get('lower_estimate')}–{f.get('upper_estimate')}). {f.get('note','')}" if f.get('next_estimate') is not None else f.get('reason','No reliable forecast generated.'))
    story.append(Paragraph(forecast_text, styles['BodyText']))
    story += [Spacer(1,4*mm),Paragraph('Data quality review',styles['Heading2'])]
    for o in analysis.get('outliers',[]): story.append(Paragraph(f"{o['column']}: {o['count']} potential IQR outliers (bounds {o['lower_bound']} to {o['upper_bound']}).",styles['Small']))
    if ai_summary and ai_summary.get('available'):
        story += [Spacer(1,4*mm),Paragraph('AI-assisted commentary',styles['Heading2']),Paragraph(str(ai_summary.get('summary','')),styles['BodyText'])]
        for x in ai_summary.get('recommendations',[]): story.append(Paragraph('• '+str(x),styles['BodyText']))
    story += [Spacer(1,6*mm),Paragraph('Methodology and limitations',styles['Heading2']),Paragraph('Statistics and findings are computed locally from the uploaded dataset. IQR flags are screening signals, not confirmed errors. Correlation is association, not causation. Forecasts are exploratory linear estimates and may not capture seasonality, structural changes or external drivers. Management should validate context before acting.',styles['Small'])]
    def footer(canvas,doc):
        canvas.saveState(); canvas.setStrokeColor(teal); canvas.line(16*mm,12*mm,194*mm,12*mm); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#607080')); canvas.drawString(16*mm,8*mm,'TRACEPOINT • Local Data Intelligence'); canvas.drawRightString(194*mm,8*mm,f'Page {doc.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer); buf.seek(0); return buf
