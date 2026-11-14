"""BG mẫu form: original artwork, Arial typography, itemized rows and exact form wording."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
from datetime import datetime
from collections import OrderedDict
from xml.sax.saxutils import escape

ASSETS=Path(__file__).with_name('kogen_assets')
LAYOUT_VERSION='BG-KENWIN-20261112-v5'
BORDER_WIDTH=0.3  # Original thin stroke, uniformly black.
PAGE=(612,792)
LEFT=22.3
WIDTH=561.3
COLS=[18,24,105,140,34,42,26,26,37,18,43,48.3]
GLASS_LABELS={'none':'Không kính','tempered_8mm':'Kính 8mm cường lực','tempered_8mm_acid_frosted':'Kính 8mm cường lực nhúng acid mờ','tempered_6mm':'Kính 6mm cường lực','laminated_8_38mm_smoke':'Kính dán an toàn 8.38mm xám khói','laminated_8_38mm_clear':'Kính dán an toàn 8.38mm trong'}

def vnd(value):return f'{int(value):,}'

def number(value):
    text=format(Decimal(str(value)),'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text

def render(path,quote):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,Image,Spacer,Table,TableStyle,LongTable,KeepTogether
    import reportlab
    # Keep Arial on Windows and use installed Unicode fonts on Linux runners/containers.
    families=[(Path('C:/Windows/Fonts'),('arial.ttf','arialbd.ttf','ariali.ttf','arialbi.ttf')),
              (Path('/usr/share/fonts/truetype/dejavu'),('DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSans-Oblique.ttf','DejaVuSans-BoldOblique.ttf')),
              (Path(reportlab.__file__).parent/'fonts',('Vera.ttf','VeraBd.ttf','VeraIt.ttf','VeraBI.ttf'))]
    fontdir,files=next((directory,files) for directory,files in families if all((directory/f).is_file() for f in files))
    for name,file in zip(('KogenArial','KogenArialBold','KogenArialItalic','KogenArialBoldItalic'),files):
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
    pdfmetrics.registerFontFamily('KogenArial',normal='KogenArial',bold='KogenArialBold',italic='KogenArialItalic',boldItalic='KogenArialBoldItalic')
    navy=colors.HexColor('#132247');taupe=colors.HexColor('#A18F83')
    pale=colors.HexColor('#EDF1F6');sand=colors.HexColor('#F0EBE7')
    normal=ParagraphStyle('form',fontName='KogenArial',fontSize=8,leading=10.8,textColor=colors.HexColor('#29313D'),spaceAfter=0,splitLongWords=True)
    bold=ParagraphStyle('form-bold',parent=normal,fontName='KogenArialBold',textColor=navy)
    italic=ParagraphStyle('form-italic',parent=normal,fontName='KogenArialItalic')
    bolditalic=ParagraphStyle('form-bold-italic',parent=normal,fontName='KogenArialBoldItalic')
    center=ParagraphStyle('form-center',parent=normal,alignment=1)
    head=ParagraphStyle('form-head',parent=bold,alignment=1)
    red=ParagraphStyle('form-adjustment',parent=normal,textColor=navy,alignment=1)
    redcenter=ParagraphStyle('form-adjustment-center',parent=normal,textColor=navy,alignment=1)
    whitehead=ParagraphStyle('form-total',parent=head,textColor=colors.white)
    section=ParagraphStyle('form-section',parent=bold,fontSize=9,leading=12,spaceBefore=0)
    title=ParagraphStyle('form-title',parent=head,fontSize=11,leading=14)
    grid=colors.black;gray=pale
    def P(text,style=normal):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    def C(text,b=False):return P(text,head if b else center)
    def M(value,style=None):
        text=vnd(value)
        base=style or normal
        # Fit using the selected font's real metrics: DejaVu is wider than Arial.
        # An amount must stay on one line, including in the bold totals rows.
        available=min(COLS[10:])-2.4
        size=min(base.fontSize,available/pdfmetrics.stringWidth(text,base.fontName,1))
        sty=ParagraphStyle('money',parent=base,fontSize=size,alignment=1,splitLongWords=False)
        return P(text,sty)
    calc=quote['calculation'];client=quote['customer'];total=calc['totals'];lines=calc['lines']
    directions={x['direction'] for x in lines};color_codes={x['color'] for x in lines}
    direction='1 CHIỀU' if directions=={'one_way'} else '2 CHIỀU' if directions=={'two_way'} else '1 CHIỀU / 2 CHIỀU'
    color=' / '.join({'brown':'NÂU KIM SA','gray':'XÁM NGỌC TRAI','wood_grain_trac':'VÂN GỖ TRẮC'}.get(c,c) for c in sorted(color_codes))
    flow=[P('BÁO GIÁ CỬA NHÔM KÖGEN TRƯỢT QUAY '+direction+' - MÀU '+color,title),Spacer(1,8)]
    name=client.get('company') or client.get('customer_name','')
    address=client.get('project_address','')
    info=[
        [C('THÔNG TIN KHÁCH HÀNG',True),'',C('THÔNG TIN BÁO GIÁ',True),''],
        [P('Tên đại lý:'),P(name),P('Người gửi báo giá:'),P(quote['prepared_by'])],
        [P('Điện thoại:'),P(client.get('phone','')),P('Ngày báo giá:'),P(datetime.fromisoformat(quote['created_at']).strftime('%d/%m/%Y'))],
        [P('Địa chỉ công trình:'),P(address),P('Số báo giá:'),P(quote['quote_id'])]]
    table=Table(info,colWidths=[158.6,205.8,93.9,103.0],rowHeights=[16,None,None,None])
    table.setStyle(TableStyle([('SPAN',(0,0),(1,0)),('SPAN',(2,0),(3,0)),('BACKGROUND',(0,0),(-1,0),pale),('LINEBELOW',(0,0),(-1,0),BORDER_WIDTH,grid),('GRID',(0,0),(-1,-1),BORDER_WIDTH,grid),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(-1,-1),'CENTER'),('LEFTPADDING',(0,0),(-1,-1),1.2),('RIGHTPADDING',(0,0),(-1,-1),1.2),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    flow.extend([table,Spacer(1,6),P('Công ty cổ phần tập đoàn Kenwin cám ơn Quý khách hàng đã quan tâm tới sản phẩm của chúng tôi, và trân trọng gửi bản báo giá tốt nhất tới công trình của Quý khách hàng như sau:',normal),Spacer(1,8)])
    rows=[
        [C('STT',True),C('Mã SP',True),C('Thiết kế minh họa',True),C('Tên cửa',True),C('Kính',True),C('Hãng\nphụ kiện',True),C('Kích thước\n(mm)',True),'',C('Tổng DT',True),C('SL',True),C('Đơn giá',True),C('Thành tiền',True)],
        ['','','','','','',C('Rộng',True),C('Cao',True),C('m2/mdài',True),'',C('VNĐ/ đơn vị\ntính',True),C('vnđ',True)]]
    heights=[None,None]
    styles=[('GRID',(0,0),(-1,-1),BORDER_WIDTH,grid),('BACKGROUND',(0,0),(-1,1),gray),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(-1,-1),'CENTER'),('LEFTPADDING',(0,0),(-1,-1),1.2),('RIGHTPADDING',(0,0),(-1,-1),1.2),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('SPAN',(6,0),(7,0))]
    for col in (0,1,2,3,4,5,9):styles.append(('SPAN',(col,0),(col,1)))
    glass_groups=OrderedDict()
    for index,line in enumerate(lines,1):
        start=len(rows);qty=line['quantity'];area=Decimal(line['area_billed_m2']);summed=area*qty
        slim='SLIM ' if '_slim_' in line['product_key'] else ''
        label=f"Cửa trượt quay {slim}{line['label'].split()[-2]} cánh "+('mở 2 chiều' if line['direction']=='two_way' else 'mở 1 chiều')+', nhôm Kogen'
        thickness='2.0-5.0mm' if slim else '1.6-5.0mm'
        finish=('Phủ phim vân gỗ trắc' if line['color']=='wood_grain_trac' else 'Sơn tĩnh điện '+('nâu kim sa' if line['color']=='brown' else 'xám ngọc trai')+', bảo hành 10 năm')
        description=label+'\n-- Độ dày nhôm kỹ thuật: từ '+thickness+'\n- Bản cánh: '+line['profile'].replace('x','*')+'mm\n- Ray Inox thế hệ mới\n- '+finish
        if line.get('has_fix') and line.get('fix_height_mm') is not None:
            description+='\n- Cao ô fix: '+str(line['fix_height_mm'])+'mm; cao phần cửa: '+str(line['door_height_mm'])+'mm'
        fix_image_keys={'2ray_standard_4','2ray_slim_2','2ray_standard_2','2ray_slim_4','3ray_slim_3','3ray_slim_6','3ray_standard_3','3ray_standard_6'}
        image_folder='with_fix' if line.get('has_fix') and line['product_key'] in fix_image_keys else 'final_workbook'
        picture=ASSETS/image_folder/(line['product_key']+'.png')
        if not picture.exists():raise FileNotFoundError('Thiếu ảnh minh họa gốc từ bảng FINAL cho '+line['product_key'])
        illustration_source=str(picture)
        if image_folder=='with_fix':
            # Crop white canvas only in the in-memory preview; original artwork stays untouched.
            from PIL import Image as PILImage, ImageChops
            from io import BytesIO
            with PILImage.open(picture) as original:
                rgb=PILImage.new('RGB',original.size,'white')
                if 'A' in original.getbands():rgb.paste(original,mask=original.getchannel('A'))
                else:rgb.paste(original.convert('RGB'))
                mask=ImageChops.difference(rgb,PILImage.new('RGB',rgb.size,'white')).convert('L').point(lambda value:255 if value>25 else 0)
                bounds=mask.getbbox()
                if bounds:
                    left,top,right,bottom=bounds
                    rgb=rgb.crop((max(0,left-8),max(0,top-8),min(rgb.width,right+8),min(rgb.height,bottom+8)))
                illustration_source=BytesIO()
                rgb.save(illustration_source,format='PNG');illustration_source.seek(0)
        illustration=Image(illustration_source,width=COLS[2]-12,height=105,kind='proportional',hAlign='CENTER')
        glass_label=line.get('glass_label') or GLASS_LABELS.get(line['glass'],line['glass'])
        rows.append([C(index),C('D'+str(index)),illustration,P(description),C(glass_label),C('Jingchen'),C(line['width_mm']),C(line['height_mm']),C(number(area) if line['base_unit']=='m2' else 'Bộ'),C(qty),M(line['base_price']),M(line['frame_amount']*qty)])
        heights.append(max(56,P(description).wrap(COLS[3]-2.4,1000)[1]+8))
        hinges='5' if line['product_key'].startswith('3ray') else '4'
        leaves=line['label'].split()[-2]
        hinge_description=('Bản lề trục xoay chịu lực trên dưới' if line['direction']=='two_way' else f'Bản lề chịu lực cao cấp rãnh C Châu Âu ({hinges} bản lề/cánh)')
        hardware=f'Bộ phụ kiện {"Slim " if slim else ""}{leaves} cánh dùng bánh xe 4 con lăn:\n + Bánh xe Metro 4 con lăn kết hợp giảm chấn 2 chiều thương hiệu OPK System\n+ {hinge_description}\n+ Bộ ke đúc kết hợp bộ chốt tự động thế hệ mới\n+ Bộ khóa 2 mặt cao cấp'
        rows.append(['','','',P(hardware),'','','','',C('Bộ'),C(qty),M(line['hardware_amount']),M(line['hardware_amount']*qty)])
        heights.append(max(80,P(hardware).wrap(COLS[3]-2.4,1000)[1]+8))
        extras=[]
        if line.get('color_amount'):
            extras.append(('Phụ thu màu vân gỗ trắc','m2',qty,line['color_surcharge_per_m2'],line['color_amount']*qty,''))
        if line['handle']!='none':
            length='350' if line['handle']=='d350' else '600';price=230000 if length=='350' else 695000
            extras.append(('Tay nắm nhôm đúc nguyên khối CNC '+length,'chiếc',line['handle_qty']*qty,price,line['handle_qty']*qty*price,''))
        if line.get('extra_hinges'):extras.append(('Tăng cường bản lề chịu lực','chiếc',line['extra_hinges']*qty,150000,line['extra_hinges']*qty*150000,'Jingchen'))
        if line.get('smart_lock_qty'):extras.append(('Khóa điện tử thông minh ANDES bản đặc biệt dài 640mm','Bộ',line['smart_lock_qty']*qty,5990000,line['smart_lock_qty']*qty*5990000,'Andes'))
        if line['has_fix']:
            rate=100000 if line['product_key'].startswith('2ray') else 150000
            extras.append(('Phụ phí ô fix','m2',qty,rate,line['fix_amount']*qty,''))
        for desc,unit,quantity,price,amount,brand in extras:
            rows.append(['','','',P(desc),'',C(brand),'','',C(number(area) if unit=='m2' else unit),C(quantity),M(price),M(amount)])
            heights.append(None)
        end=len(rows)-1
        for col in (0,1,2):styles.append(('SPAN',(col,start),(col,end)))
        # Glass and dimensions describe the door row only. Empty cells beneath
        # span the accessory rows, matching the approved reference layout.
        for col in (4,6,7):
            styles.append(('SPAN',(col,start+1),(col,end)))
        if line.get('smart_lock_qty'):
            styles.append(('SPAN',(5,start),(5,start+1)))
        else:
            styles.append(('SPAN',(5,start),(5,end)))
        styles.append(('NOSPLIT',(0,start),(-1,end)))
        key=(line['glass'],glass_label,line['glass_adjustment_per_m2'])
        group=glass_groups.setdefault(key,{'amount':0,'area':Decimal(0)})
        group['amount']+=line['glass_amount']*qty;group['area']+=summed
    items=LongTable(rows,colWidths=COLS,rowHeights=heights,repeatRows=2,hAlign='LEFT',splitByRow=True)
    items.setStyle(TableStyle(styles));flow.extend([items,Spacer(1,10)])
    gross=sum(total.get(k,0) for k in ('frame_amount','hardware_amount','extra_amount','fix_amount','color_amount'))
    total_area=Decimal(total['area_billed_m2'])
    average=int((Decimal(total['total_vat_included'])/total_area).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    summary=[
        [C('TỔNG GIÁ TRỊ ĐƠN HÀNG',True),'','','','','','','',C('Tổng DT (m2)'),' ',C('Đơn giá TB/m2'),C('Thành tiền (vnđ)')],
        [C('Cộng giá trị đơn hàng'),'','','','','','','',C(number(total_area)),'',M(average,head),M(gross,head)]]
    summary_styles=[('GRID',(0,0),(-1,-1),BORDER_WIDTH,grid),('LEFTPADDING',(0,0),(-1,-1),1.2),('RIGHTPADDING',(0,0),(-1,-1),1.2),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(-1,-1),'CENTER'),('SPAN',(0,0),(7,0)),('SPAN',(8,0),(9,0)),('SPAN',(0,1),(7,1)),('SPAN',(8,1),(9,1)),('BACKGROUND',(0,0),(-1,0),pale),('BACKGROUND',(10,1),(10,1),sand)]
    for (kind,label,rate),group in glass_groups.items():
        if all(line.get('direct_workbook_price') for line in lines):continue
        if kind=='none':text='Chiết khấu gia công không kính 100k/m2'
        else:text=label+' +'+vnd(rate)+'đ/m2'
        amount=group['amount'];value='('+vnd(-amount)+')' if amount<0 else vnd(amount)
        no=len(summary);summary.append([P(text,redcenter),'','','','','','','','','','',P(value,red)])
        summary_styles.append(('SPAN',(0,no),(7,no)))
    deposit=int((Decimal(total['total_vat_included'])/2).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    balance=total['total_vat_included']-deposit
    no=len(summary);summary.append([P('TỔNG CỘNG',whitehead),'','','','','','','','','','',M(total['total_vat_included'],whitehead)])
    summary_styles.extend([('SPAN',(0,no),(7,no)),('SPAN',(8,no),(10,no)),('BACKGROUND',(0,no),(-1,no),navy)])
    for text,amount in [('Tạm ứng 50%',deposit),('Quyết toán trước khi giao hàng',balance)]:
        row=len(summary)
        summary.append([C(text),'','','','','','','','','','',M(amount,head)])
        summary_styles.extend([('SPAN',(0,row),(7,row)),('SPAN',(8,row),(10,row))])
    totals_table=Table(summary,colWidths=COLS);totals_table.setStyle(TableStyle(summary_styles))
    notes=[
        Paragraph('LƯU Ý',section),Spacer(1,4),
        P('- Báo giá tại xưởng đã bao gồm hỗ trợ vận chuyển trong bán kính 15km. Hỗ trợ VAT 8%.'),Spacer(1,4),
        P('- Báo giá chưa bao gồm chi phí lắp đặt.'),Spacer(1,4),
        P('- Báo giá có hiệu lực trong 10 ngày kể từ ngày báo giá.'),Spacer(1,10),
        Paragraph('QUY CÁCH VẬT TƯ, SẢN PHẨM VÀ BẢO HÀNH',section),Spacer(1,4),
        *([P('- Nhôm sơn tĩnh điện màu xám ngọc trai và nâu kim sa bảo hành 10 năm'),Spacer(1,4)] if color_codes & {'gray','brown'} else []),
        P('-  Phụ kiện chính hãng bảo hành 02 năm'),Spacer(1,4),
        Paragraph('ĐỂ ĐẢM BẢO CỬA VẬN HÀNH ỔN ĐỊNH',section),Spacer(1,4),
        P('- Kích thước cánh tối đa cửa trượt quay 2 chiều khuyến nghị: Rộng 1m, cao 2.6m',normal),Spacer(1,4),
        P('- Kích thước cánh tối đa cửa trượt quay 1 chiều khuyến nghị: Rộng 1m, cao 2.9m',normal),Spacer(1,10),
        Paragraph('THANH TOÁN',section),Spacer(1,4)]
    # Customer text is always escaped; only these fixed payment labels contain markup.
    notes.extend([
        Paragraph('<b>- Lần 1:</b> Bên A tạm ứng 50% giá trị đơn hàng trước khi đưa vào sản xuất.',normal),Spacer(1,4),
        Paragraph('<b>- Lần 2:</b> Bên A thanh toán phần còn lại trước khi giao hàng.',normal)])
    qr=ASSETS/'payment_vietcombank.jpg'
    if not qr.is_file():raise FileNotFoundError('Thiếu ảnh QR tài khoản Kenwin đã được chủ cung cấp.')
    qr_image=Image(str(qr),width=151,height=171,kind='proportional',hAlign='CENTER')
    qr_box=Table([[qr_image]],colWidths=[157])
    qr_box.setStyle(TableStyle([('BOX',(0,0),(-1,-1),BORDER_WIDTH,grid),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    footer=Table([[notes,qr_box]],colWidths=[WIDTH-170,170])
    footer.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),('LEFTPADDING',(1,0),(1,0),13),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    signatures=Table([[C('XÁC NHẬN KHÁCH HÀNG',True),C('NGƯỜI LẬP',True),C('XÁC NHẬN CÔNG TY',True)]],colWidths=[335,130,96.3])
    signatures.setStyle(TableStyle([('LEFTPADDING',(0,0),(0,0),1.2),('LEFTPADDING',(1,0),(2,0),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    flow.extend([totals_table,Spacer(1,16),footer,Spacer(1,14),signatures,Spacer(1,24)])
    def page(canvas,doc):
        header=ASSETS/'header.png'
        if header.exists():canvas.drawImage(str(header),LEFT,PAGE[1]-16-WIDTH*146/1082,width=WIDTH,height=WIDTH*146/1082,mask='auto')
        if doc.page>1:
            canvas.setFillColor(navy);canvas.setFont('KogenArial',8);canvas.drawRightString(LEFT+WIDTH,18,quote['quote_id']+' | '+str(doc.page))
    doc=BaseDocTemplate(str(path),pagesize=PAGE,title='Báo giá cửa nhôm Kögen '+quote['quote_id'],author='Kenwin Group',leftMargin=LEFT,rightMargin=PAGE[0]-LEFT-WIDTH,topMargin=100,bottomMargin=34)
    frame=Frame(LEFT,34,WIDTH,PAGE[1]-100-34,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='form')
    doc.addPageTemplates(PageTemplate(id='BG-mau',frames=[frame],onPage=page));doc.build(flow)
