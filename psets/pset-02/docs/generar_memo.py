"""Genera el memo en seis páginas con ReportLab (herramienta de documentación)."""
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT = Path(__file__).resolve().parent
BLUE = colors.HexColor('#17324d')
TEAL = colors.HexColor('#167d8d')
PALE = colors.HexColor('#edf4f7')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyMemo', fontName='Helvetica', fontSize=10,
                          leading=14.2, spaceAfter=9, textColor=BLUE))
styles.add(ParagraphStyle(name='CellMemo', parent=styles['BodyMemo'], fontSize=8.4,
                          leading=11, spaceAfter=0))
styles.add(ParagraphStyle(name='SectionMemo', fontName='Helvetica-Bold', fontSize=18,
                          leading=23, textColor=BLUE, spaceAfter=15))
styles.add(ParagraphStyle(name='SmallMemo', fontName='Helvetica', fontSize=8.5,
                          leading=11, textColor=TEAL, spaceAfter=12))


def p(text, style='BodyMemo'):
    text = escape(text).replace('→', ' / ').replace('—', '-').replace('–', '-')
    text = re.sub(r'`([^`]+)`', r'<b>\1</b>', text)
    return Paragraph(text, styles[style])


def box(d, x, y, w, h, title, lines):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=PALE, strokeColor=TEAL, strokeWidth=0.9))
    d.add(String(x + 10, y + h - 20, title, fontName='Helvetica-Bold', fontSize=10, fillColor=BLUE))
    for i, line in enumerate(lines):
        d.add(String(x + 10, y + h - 37 - i * 14, line, fontName='Helvetica', fontSize=8.5, fillColor=BLUE))


def architecture():
    d = Drawing(490, 205)
    nodes = [(0,140,'UCI AI4I',['CSV: 10.000 filas']), (173,140,'Kestra',['Descarga y secuencia']),
             (346,140,'Snowflake RAW',['Texto + metadatos']), (346,30,'dbt',['Bronze / Silver / Gold']),
             (173,30,'Spark local[2]',['Joins y validaciones']), (0,30,'Snowflake OBT',['Lista para análisis'])]
    for x,y,title,lines in nodes:
        box(d,x,y,144,55,title,lines)
    box(d,190,100,110,25,'PostgreSQL',[])
    for x,y,x2,y2 in [(144,167,173,167),(317,167,346,167),(418,140,418,85),
                       (346,57,317,57),(173,57,144,57),(245,140,245,125)]:
        d.add(Line(x,y,x2,y2,strokeColor=TEAL,strokeWidth=1.2))
    d.add(String(0,8,'Docker Compose: Kestra, PostgreSQL y runner Spark/pipeline',
                 fontName='Helvetica',fontSize=8.5,fillColor=TEAL))
    return d


def star():
    d = Drawing(490,210)
    box(d,0,112,152,86,'DIM_PRODUCT',['product_key (PK)', 'product_id', 'product_type'])
    box(d,338,112,152,86,'DIM_SOURCE',['source_key (PK)', 'source_url', 'source_name'])
    box(d,170,10,150,185,'FACT_READING',['reading_key (PK)', 'udi', 'product_key (FK)',
        'source_key (FK)', 'Temperaturas / rpm', 'Torque / desgaste', 'machine_failure'])
    d.add(Line(152,155,170,155,strokeColor=TEAL,strokeWidth=1.4))
    d.add(Line(320,155,338,155,strokeColor=TEAL,strokeWidth=1.4))
    return d


def blocks(text):
    chunks = re.split(r'\n\s*\n', text.strip())
    result = []
    for chunk in chunks:
        if chunk.startswith('|'):
            rows = []
            for line in chunk.splitlines():
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                if all(re.fullmatch(r'[- :]+', c) for c in cells):
                    continue
                rows.append([p(c,'CellMemo') for c in cells])
            table = Table(rows, colWidths=[95,137,258], hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),PALE), ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LINEBELOW',(0,0),(-1,0),1,TEAL),
                ('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#cbd9e0')),
                ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            result.extend([table,Spacer(1,12)])
        else:
            result.append(p(' '.join(chunk.splitlines())))
    return result


def footer(canvas, doc):
    canvas.setStrokeColor(TEAL)
    canvas.line(48,43,A4[0]-48,43)
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(BLUE)
    canvas.drawString(48,29,'PSet 2 | AI4I - Detección de fallas presentes | 12 nov 2026')
    canvas.drawRightString(A4[0]-48,29,f'{doc.page} / 6')


def main():
    text = (ROOT/'memo_tecnico.md').read_text(encoding='utf-8')
    parts = re.split(r'^## ', text, flags=re.MULTILINE)[1:]
    sections = []
    for part in parts:
        title,body = part.split('\n',1)
        sections.append((title,body))
    story = []
    for page, indices in enumerate(([0],[1],[2],[3],[4],[5])):
        if page:
            story.append(PageBreak())
        story.append(p('CIENCIA DE DATOS / PIPELINE END-TO-END','SmallMemo'))
        if page == 0:
            story.append(p('PSet 2 - Detección de fallas','SectionMemo'))
            story.append(p('Autor: Ron | Fecha: 12 de noviembre de 2026','SmallMemo'))
        for index in indices:
            title,body = sections[index]
            story.append(p(title,'SectionMemo'))
            if index == 0:
                diagram = architecture()
                diagram.scale(0.83, 0.83)
                diagram.width *= 0.83
                diagram.height *= 0.83
                story.extend([diagram,Spacer(1,12)])
            if index == 3:
                story.extend([star(),Spacer(1,12)])
            story.extend(blocks(body))
    doc = SimpleDocTemplate(str(ROOT/'PSet2_memo_Ron.pdf'), pagesize=A4,
                            leftMargin=48,rightMargin=48,topMargin=43,bottomMargin=57,
                            title='PSet 2 - Detección de fallas presentes con AI4I', author='Ron')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


if __name__ == '__main__':
    main()
