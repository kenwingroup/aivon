"""Deterministic dealer finished-door pricing. Never accepts a model-supplied price."""
import json
from pathlib import Path
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

CATALOG_PATH = Path(__file__).with_name('kogen_catalog.json')
def catalog():return json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
def money(value):return int(Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
def integer(value,name,minimum=0,maximum=100):
    try:d=Decimal(str(value))
    except Exception:raise ValueError(name+' không hợp lệ.') from None
    if not d.is_finite() or d!=d.to_integral_value() or d<minimum or d>maximum:
        raise ValueError(name+' không hợp lệ.')
    return int(d)

def check_size(width_mm,height_mm,cat=None):
    """Business minimum is checked on actual area, before upward price rounding."""
    cat=cat or catalog()
    width=integer(width_mm,'Chiều rộng mm',1,30000)
    height=integer(height_mm,'Chiều cao mm',1,10000)
    raw=Decimal(width)*Decimal(height)/Decimal(1000000)
    area=(raw/Decimal('.1')).to_integral_value(rounding=ROUND_CEILING)*Decimal('.1')
    minimum=Decimal(cat['minimum_area_m2'])
    accepted=raw>=minimum
    message=('Diện tích đạt ngưỡng tối thiểu; tiếp tục xác nhận cấu hình và điều kiện kỹ thuật.' if accepted else
        'Kích thước quá nhỏ, không thể làm cửa. Diện tích thực '+format(raw.normalize(),'f').replace('.',',')+
        ' m² nhỏ hơn mức tối thiểu '+format(minimum,'f').replace('.',',')+' m².')
    return {'width_mm':width,'height_mm':height,'area_actual_m2':str(raw),'area_billed_m2':str(area),
        'minimum_area_m2':str(minimum),'meets_minimum_area':accepted,'message':message}

def calculate_item(item, cat=None):
    cat=cat or catalog()
    rails=integer(item.get('rails'), 'Số ray',2,3)
    leaves=integer(item.get('leaves'), 'Số cánh',2,6)
    variant=str(item.get('variant') or '')
    key=f'{rails}ray_{variant}_{leaves}'
    p=cat['products'].get(key)
    if not p:raise ValueError('Chưa có bảng giá cho cấu hình này; chuyển kinh doanh xác nhận.')
    width=integer(item.get('width_mm'),'Chiều rộng mm',1,30000)
    height=integer(item.get('height_mm'),'Chiều cao mm',1,10000)
    size=check_size(width,height,cat)
    if not size['meets_minimum_area']:raise ValueError(size['message'])
    quantity=integer(item.get('quantity',1),'Số bộ',1,100)
    direction=str(item.get('direction') or '')
    if direction not in p['hardware']:raise ValueError('Chưa có giá phụ kiện cho chiều mở này.')
    color=str(item.get('color') or '')
    if color not in (['gray','brown'] if rails==2 else ['gray']):
        raise ValueError('Màu này chưa có giá chuẩn cho hệ được chọn; chuyển kinh doanh xác nhận.')
    glass=str(item.get('glass') or '')
    if glass not in cat['glass_adjustment_per_m2']:raise ValueError('Chỉ có giá không kính hoặc kính cường lực 8mm; kính khác cần báo sau.')
    has_fix=item.get('has_fix')
    if not isinstance(has_fix,bool):raise ValueError('Cần xác nhận cửa có ô fix hay không.')
    handle=str(item.get('handle') or '')
    if handle not in ('none','d350','d600'):raise ValueError('Cần chọn tay nắm: không lấy, D350 hoặc D600.')
    handle_qty=integer(item.get('handle_qty',0),'Số tay nắm mỗi bộ',0,20)
    if (handle=='none') != (handle_qty==0):raise ValueError('Loại và số lượng tay nắm chưa khớp.')
    extra_hinges=integer(item.get('extra_hinges',0),'Bản lề thêm mỗi bộ',0,100)
    smart_lock_qty=integer(item.get('smart_lock_qty',0),'Khóa Andes thêm mỗi bộ',0,10)
    if variant=='slim' and smart_lock_qty:
        raise ValueError('Bảng Slim chưa có khóa Andes; cần kinh doanh xác nhận, không tự áp giá hệ thường.')
    raw=Decimal(size['area_actual_m2'])
    area=Decimal(size['area_billed_m2'])
    band=next((b for b in p['bands'] if area<=Decimal(b[0])),None)
    max_band_applied=band is None
    if max_band_applied:
        if cat.get('oversize_pricing')!='last_band_rate_actual_area' or p['bands'][-1][2]!='m2':
            raise ValueError('Chưa có quy tắc giá cho diện tích vượt bảng của cấu hình này.')
        band=p['bands'][-1]
    frame=Decimal(band[1])*(area if band[2]=='m2' else 1)
    glass_amount=area*cat['glass_adjustment_per_m2'][glass]
    hardware=p['hardware'][direction]
    extras=extra_hinges*150000+handle_qty*({'none':0,'d350':230000,'d600':695000}[handle])+smart_lock_qty*5990000
    fix=area*(100000 if rails==2 else 150000) if has_fix else Decimal(0)
    per_set=money(frame+glass_amount+hardware+extras+fix)
    return {
        'product_key':key,'label':f'Cửa trượt quay {rails} ray '+('Slim ' if variant=='slim' else '')+f'{leaves} cánh',
        'profile':p['profile'],'source_page':p['page'],'width_mm':width,'height_mm':height,'quantity':quantity,
        'area_actual_m2':str(raw),'area_billed_m2':str(area),'band_upper_m2':band[0],
        'minimum_area_m2':size['minimum_area_m2'],'max_band_applied':max_band_applied,
        'pricing_note':('Vượt mốc '+str(p['bands'][-1][0])+' m²: áp đơn giá/m² khoảng cuối, nhân diện tích thực làm tròn lên 0,1 m²; không giới hạn diện tích tính tiền.' if max_band_applied else ''),
        'base_price':band[1],'base_unit':band[2], 'direction':direction,'color':color,'glass':glass,'has_fix':has_fix,
        'handle':handle,'handle_qty':handle_qty,'extra_hinges':extra_hinges,'smart_lock_qty':smart_lock_qty,
        'frame_amount':money(frame),'glass_amount':money(glass_amount),'hardware_amount':hardware,
        'extra_amount':extras,'fix_amount':money(fix),'unit_total':per_set,'line_total':per_set*quantity,
        'glass_adjustment_per_m2':cat['glass_adjustment_per_m2'][glass],
    }

def calculate(items):
    if not isinstance(items,list) or not 1<=len(items)<=10:raise ValueError('Mỗi báo giá cần 1-10 cấu hình cửa.')
    cat=catalog()
    lines=[calculate_item(i,cat) for i in items]
    totals={k:sum(x[k]*x['quantity'] for x in lines) for k in ['frame_amount','glass_amount','hardware_amount','extra_amount','fix_amount']}
    totals['total_vat_included']=sum(x['line_total'] for x in lines)
    totals['total_quantity']=sum(x['quantity'] for x in lines)
    totals['area_actual_m2']=str(sum(Decimal(x['area_actual_m2'])*x['quantity'] for x in lines))
    totals['area_billed_m2']=str(sum(Decimal(x['area_billed_m2'])*x['quantity'] for x in lines))
    totals['deposit_50_percent']=money(Decimal(totals['total_vat_included'])/2)
    return {'catalog_version':cat['version'],'lines':lines,'totals':totals,'vat_included_percent':8,
        'transport_installation':'Chưa bao gồm; báo riêng sau khi xác nhận địa chỉ, điều kiện vận chuyển và lắp đặt.'}
