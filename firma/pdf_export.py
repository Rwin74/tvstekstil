"""Portable, embedded-font PDF reports. No network calls during export."""
from io import BytesIO
from datetime import datetime
from html import escape
from threading import Lock
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from .config import ROOT

LOCK = Lock()
GREEN = colors.HexColor('#14594c')
INK = colors.HexColor('#20332f')
MUTED = colors.HexColor('#647770')
LABELS = {'research':'Araştırılacak','qualified':'Uygun','contacted':'İletişime geçildi','replied':'Yanıt geldi','not_suitable':'Uygun değil','unknown':'Belirsiz','possible':'Olası eşleşme','confirmed':'Doğrulandı','no':'Uygun değil','potential':'Butik adayı','multibrand':'Çok markalı seçki','supplier_invitation':'Tedarikçi başvuru ifadesi','boutique':'Butik','concept':'Konsept mağaza','retailer':'Perakende mağaza','website':'Site incelendi','search':'Arama özeti','unreviewed':'İncelenmedi'}
COUNTRIES = {'TR':'Türkiye','FR':'Fransa','GB':'Birleşik Krallık','US':'Amerika Birleşik Devletleri','DE':'Almanya','IT':'İtalya','ES':'İspanya','NL':'Hollanda','BE':'Belçika','CH':'İsviçre'}
SOURCE_LABELS = {'email':'E-posta','phone':'Telefon','whatsapp':'WhatsApp','instagram':'Instagram','buyer_assessment':'Alıcı değerlendirmesi','evidence':'Ürün kanıtı','website':'Web sitesi','contact_person':'Yetkili'}


def build_pdf(leads):
    with LOCK:
        if 'Atlas' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('Atlas',str(ROOT/'admin/butik/fonts/LiberationSans-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('AtlasBold',str(ROOT/'admin/butik/fonts/LiberationSans-Bold.ttf')))
            pdfmetrics.registerFontFamily('Atlas',normal='Atlas',bold='AtlasBold',italic='Atlas',boldItalic='AtlasBold')
    styles = {
        'body':ParagraphStyle('body',fontName='Atlas',fontSize=10,leading=15,textColor=INK,spaceAfter=7,splitLongWords=True),
        'small':ParagraphStyle('small',fontName='Atlas',fontSize=8,leading=12,textColor=MUTED,spaceAfter=5,splitLongWords=True),
        'title':ParagraphStyle('title',fontName='AtlasBold',fontSize=24,leading=29,textColor=GREEN,spaceAfter=14),
        'section':ParagraphStyle('section',fontName='AtlasBold',fontSize=12,leading=17,textColor=GREEN,spaceBefore=13,spaceAfter=8,keepWithNext=True),
        'tr':ParagraphStyle('tr',fontName='Atlas',fontSize=10,leading=15,textColor=GREEN,backColor=colors.HexColor('#eef6f1'),borderPadding=7,spaceBefore=4,spaceAfter=12),
    }
    def p(text,style='body'):
        clean=''.join(c for c in str(text) if ord(c)>=32 or c in '\n\t')
        return Paragraph(escape(clean).replace('\n','<br/>'),styles[style])
    def section(text): return p(text,'section')
    def blocks(text,style='body'):
        # Bounded paragraphs let headings stay with the first lines without
        # pushing a multi-page note onto a mostly empty next page.
        text=str(text);result=[]
        while len(text)>1000:
            boundary=text.rfind(' ',0,1000)
            if boundary<1: boundary=1000
            result.append(p(text[:boundary],style));text=text[boundary:].lstrip(' ')
        if text: result.append(p(text,style))
        return result
    def bilingual(row,key,label):
        if not row.get(key) and not row.get(key+'_tr'): return []
        result=[section(label),*blocks(row.get(key) or 'Belirtilmedi')]
        if row.get(key+'_tr'): result.extend([p('Türkçe karşılığı','small'),*blocks(row[key+'_tr'],'tr')])
        return result
    stream=BytesIO()
    doc=SimpleDocTemplate(stream,pagesize=A4,rightMargin=44,leftMargin=44,topMargin=65,bottomMargin=51,title='Firma Atlas - Kayıtlı Butikler',author='Firma Atlas')
    story=[p('KAYITLI BUTİKLER','small'),p('Yeni iş bağlantıları\nFirma dosyası','title'),p(f'{len(leads)} firma  |  {datetime.now():%d.%m.%Y %H:%M}','small'),Spacer(1,16),p('İletişim bilgileri, ürün değerlendirmeleri ve görüşme notları tek dosyada.'),p('Türkçe karşılıklar, girilmiş veya çeviri servisiyle hazırlanmış metinlerdir. Orijinal metinler korunur. Eksik çeviriler uydurulmaz. Öncelik puanı kesin satın alma talebi değildir.','small'),section('Dosyadaki firmalar')]
    for i,row in enumerate(leads,1): story.append(p(f'{i:02d}  {row["name"]}'))
    for i,row in enumerate(leads,1):
        story.extend([PageBreak(),p(f'FİRMA {i:02d} / {len(leads):02d}','small'),p(row['name'],'title')])
        if row.get('name_tr'): story.extend([p('Başlığın Türkçe karşılığı','small'),p(row['name_tr'],'tr')])
        story.append(p(f"{COUNTRIES.get(row.get('country'),row.get('country') or 'Ülke belirtilmedi')}  |  {LABELS.get(row.get('status'),row.get('status',''))}  |  Öncelik: {row.get('priority',0)}/100",'small'))
        story.append(section('İletişim ve konum'))
        fields=[('website','Web sitesi'),('email','E-posta'),('phone','Telefon'),('whatsapp','WhatsApp'),('instagram','Instagram'),('contact_person','Yetkili'),('city','Doğrulanan şehir'),('target_city','Arama hedefi')]
        for key,label in fields:
            table=Table([[p(label,'small'),p(row.get(key) or 'Belirtilmedi')]],colWidths=[110,397],hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f4f7f5')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
            story.append(table)
        story.extend(bilingual(row,'product','Ürün / ürün grubu'))
        story.append(section('Alıcı değerlendirmesi'))
        for key,label in [('fit','Ürün uygunluğu'),('buyer_type','İşletme türü'),('opportunity','Alıcı sinyali'),('assessment','İnceleme düzeyi')]:
            story.append(p(f"{label}: {LABELS.get(row.get(key),row.get(key) or 'Belirsiz')}"))
        for reason in row.get('reasons',[]): story.append(p('- '+reason))
        if row.get('assessed_at'): story.append(p('İnceleme tarihi: '+row['assessed_at'],'small'))
        for key,label in [('evidence','Ürün ve arama açıklaması'),('supplier_evidence','Tedarikçi başvuru ifadesi'),('notes','Görüşme ve takip notları')]: story.extend(bilingual(row,key,label))
        story.append(section('Kaynaklar ve kayıt bilgileri'))
        for key,label in [('source_url','Arama kaynağı'),('supplier_source','Başvuru kaynağı')]:
            if row.get(key): story.append(p(label+': '+row[key],'small'))
        for source in row.get('sources',[]):
            story.append(p(f"{SOURCE_LABELS.get(source.get('field'),source.get('field','Bilgi'))}: {source.get('value','')}\n{source.get('url','')}\n{source.get('checked_at','')}",'small'))
        story.append(p(f"Kayıt: {row.get('id','-')}\nOluşturulma: {row.get('created_at','-')} | Güncelleme: {row.get('updated_at','-')}",'small'))
    def frame(canvas,doc):
        canvas.saveState(); w,h=A4
        canvas.setFillColor(GREEN);canvas.rect(0,h-13,w,13,fill=1,stroke=0)
        canvas.setFont('AtlasBold',10);canvas.drawString(44,h-38,'firma atlas')
        canvas.setFillColor(MUTED);canvas.setFont('Atlas',8);canvas.drawRightString(w-44,h-38,'BUTİK İLETİŞİM DOSYASI')
        canvas.setStrokeColor(colors.HexColor('#d9e5df'));canvas.line(44,37,w-44,37)
        canvas.drawString(44,24,'Özel çalışma dosyası | Firma Atlas');canvas.drawRightString(w-44,24,f'Sayfa {doc.page}')
        canvas.restoreState()
    doc.build(story,onFirstPage=frame,onLaterPages=frame)
    return stream.getvalue()
