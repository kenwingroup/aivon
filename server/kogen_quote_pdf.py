"""PDF quotation using the owner's brand artwork and deterministic calculation result."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from xml.sax.saxutils import escape

ASSETS=Path(__file__).with_name('kogen_assets')
def vnd(value):return f'{int(value):,}'.replace(',','.')+' đ'
def number(value):return format(Decimal(str(value)),'f').rstrip('0').rstrip('.') if '.' in str(value) else str(value)
def render(path, quote):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, LongTable, Table, TableStyle, KeepTogether
    fonts=Path('C:/Windows/Fonts')
    if 'KogenArial' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('KogenArial',str(fonts/'arial.ttf')))
        pdfmetrics.registerFont(TTFont('KogenArialBold',str(fonts/'arialbd.ttf')))
        pdfmetrics.registerFontFamily('KogenArial',normal='KogenArial',bold='KogenArialBold')
    navy=colors.HexColor('#192139'); taupe=colors.HexColor('#9A8375')
    normal=ParagraphStyle('body',fontName='KogenArial',fontSize=9,leading=12,textColor=navy,wordWrap='CJK',spaceAfter=3)
    small=ParagraphStyle('small',parent=normal,fontSize=8,leading=10)
    title=ParagraphStyle('title',parent=normal,fontName='KogenArialBold',fontSize=16,leading=20,alignment=1,spaceAfter=6)
    white=ParagraphStyle('white',parent=small,textColor=colors.white,fontName='KogenArialBold',alignment=1)
    bold=ParagraphStyle('bold',parent=normal,fontName='KogenArialBold')
    def P(text,style=normal):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    width=A4[0]-56
    lead=quote['customer']; calc=quote['calculation']; total=calc['totals']
    flow=[P('BÁO GIÁ CỬA TRƯỢT QUAY KÖGEN',title),P('ĐẠI LÝ THÀNH PHẨM - THỊ TRƯỜNG MIỀN NAM',ParagraphStyle('sub',parent=normal,alignment=1)),Spacer(1,5)]
    info=[
        [P('Mã báo giá: '+quote['quote_id'],bold),P('Ngày: '+datetime.fromisoformat(quote['created_at']).strftime('%d/%m/%Y'),bold)],
        [P('Kính gửi: '+lead.get('customer_name','')),P('Điện thoại: '+lead.get('phone',''))],
        [P('Đại lý / Công ty: '+lead.get('company','')),P('Công trình: '+lead.get('project_name',''))],
        [P('Địa chỉ công trình: '+lead.get('project_address','')),P('Khu vực: Miền Nam')]]
    t=Table(info,colWidths=[width*.57,width*.43]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),4)]));flow.extend([t,Spacer(1,7)])
    rows=[[P(x,white) for x in ['STT','SẢN PHẨM VÀ CẤU HÌNH','DT THỰC\n(m²/bộ)','DT TÍNH\n(m²/bộ)','SL\n(bộ)','GIÁ / BỘ\nGỒM VAT','THÀNH TIỀN\nGỒM VAT']]]
    for i,line in enumerate(calc['lines'],1):
        name=line['label']+'\n'+str(line['width_mm'])+' × '+str(line['height_mm'])+' mm; '+('mở 2 chiều' if line['direction']=='two_way' else 'mở 1 chiều')
        details=('Kính cường lực 8mm' if line['glass']=='tempered_8mm' else 'Không kính')+'; '+('Nâu kaki' if line['color']=='brown' else 'Xám ngọc trai')+'; '+('có ô fix' if line['has_fix'] else 'không ô fix')
        details+='\nJingchen; '+('không lấy tay nắm' if line['handle']=='none' else f"{line['handle_qty']} tay nắm {line['handle'].upper()}/bộ")
        content=[P(name,bold),P(details,small)]
        picture=ASSETS/(line['product_key']+'.png')
        if picture.exists():content.append(Image(str(picture),width=112,height=51,kind='proportional',hAlign='LEFT'))
        rows.append([P(i),content,P(number(line['area_actual_m2']),small),P(number(line['area_billed_m2']),small),P(line['quantity']),P(vnd(line['unit_total']),small),P(vnd(line['line_total']),small)])
    widths=[27,width-27-47-47-25-78-82,47,47,25,78,82]
    table=LongTable(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),taupe),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#B8B3AF')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F4F2F0')])]))
    flow.extend([table,Spacer(1,9)])
    flow.append(P('CHI TIẾT CƠ SỞ TÍNH GIÁ',bold))
    for i,line in enumerate(calc['lines'],1):
        basis=(vnd(line['base_price'])+'/bộ theo mức tối thiểu') if line['base_unit']=='set' else number(line['area_billed_m2'])+'m² × '+vnd(line['base_price'])+'/m²'
        if line.get('max_band_applied'):flow.append(P(line['pricing_note'],small))
        flow.append(P(f"{i}. Mỗi bộ: khung {basis} = {vnd(line['frame_amount'])}; điều chỉnh kính {vnd(line['glass_amount'])}; phụ kiện Jingchen {vnd(line['hardware_amount'])}; phụ kiện thêm {vnd(line['extra_amount'])}; ô fix {vnd(line['fix_amount'])}. Tổng {vnd(line['unit_total'])}/bộ.",small))
    summary=Table([[P('TỔNG GIÁ TRỊ CỬA - ĐÃ BAO GỒM VAT 8%',bold),P(vnd(total['total_vat_included']),bold)],
        [P('Vận chuyển và lắp đặt'),P('BÁO RIÊNG THEO VỊ TRÍ')],
        [P('Đặt cọc 50% giá trị cửa trước sản xuất'),P(vnd(total['deposit_50_percent']))]],colWidths=[width*.69,width*.31])
    summary.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EBE5DF')),('BOX',(0,0),(-1,-1),.5,taupe),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    flow.extend([Spacer(1,6),KeepTogether([summary]),Spacer(1,8),P('ĐIỀU KIỆN BÁO GIÁ',bold)])
    notes=[
        'Diện tích thực tối thiểu mỗi bộ là 3,1m² trước khi làm tròn; dưới ngưỡng không nhận làm cửa. Diện tích mỗi bộ = rộng × cao; làm tròn lên 0,1m² để chọn khoảng giá và tính tiền. Khoảng đầu tính trọn bộ; các khoảng tiếp theo tính theo m².',
        'Vượt mốc diện tích cuối bảng: áp đơn giá/m² của khoảng cuối của đúng cấu hình, nhân diện tích yêu cầu làm tròn lên 0,1m²; không giới hạn diện tích tính tiền ở mốc tối đa.',
        'Không kính: trừ 100.000đ/m² so với bảng. Kính cường lực 8mm: cộng 265.000đ/m². Các giá trên đã bao gồm VAT 8%, không cộng VAT lần nữa.',
        'Ô fix: cộng 100.000đ/m² cho hệ 2 ray hoặc 150.000đ/m² cho hệ 3 ray. Bộ phụ kiện Jingchen chưa bao gồm tay nắm; tay nắm và phụ kiện thêm tính theo lựa chọn ghi trên báo giá.',
        'Chưa bao gồm vận chuyển và lắp đặt. Kinh doanh xác nhận chi phí sau khi nắm địa chỉ, khoảng cách và điều kiện thực tế công trình.',
        'Khách hàng chốt kích thước, chiều mở, kính, màu sắc và phụ kiện; ký xác nhận bản vẽ kỹ thuật trước sản xuất. Thanh toán đủ trước giao hàng 01 ngày.',
        'Sơn tĩnh điện Metallic bảo hành 10 năm; phụ kiện nhập khẩu bảo hành 24 tháng theo tiêu chuẩn nhà sản xuất. Bảng giá nguồn áp dụng từ 09/07/2026 đến khi có thông báo mới.'
    ]
    for text in notes:flow.append(P('• '+text,small))
    flow.append(P('Nguồn: bảng giá Kögen 2 ray và 3 ray miền Nam 2026 do Kenwin cung cấp; quy tắc kính, VAT và làm tròn được xác nhận ngày 24/10/2026; ngưỡng tối thiểu và cách áp giá vượt mốc được xác nhận ngày 27/10/2026.',small))
    def page(canvas,doc):
        if (ASSETS/'header.png').exists():canvas.drawImage(str(ASSETS/'header.png'),28,A4[1]-88,width=width,height=73,mask='auto')
        if (ASSETS/'footer.png').exists():canvas.drawImage(str(ASSETS/'footer.png'),0,0,width=A4[0],height=37,mask='auto')
        canvas.setFont('KogenArial',7)
        canvas.setFillColor(navy)
        canvas.drawRightString(A4[0]-28,45,quote['quote_id']+' | '+str(doc.page))
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=28,rightMargin=28,topMargin=103,bottomMargin=62,title='Báo giá Kögen '+quote['quote_id'],author='Kenwin Group - Ngô Non').build(flow,onFirstPage=page,onLaterPages=page)
