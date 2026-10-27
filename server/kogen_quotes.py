"""Scoped customer intake, deterministic quotation, and fixed-register Composio sync."""
from __future__ import annotations
import asyncio,hashlib,json,re,sqlite3,uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import urllib.request
from kogen_pricing import calculate,check_size

CONFIG=Path(__file__).with_name('kogen_config.json')
_LOCKS={}
HINT='''
BÁO GIÁ KÖGEN MIỀN NAM CHO ĐẠI LÝ THÀNH PHẨM ĐÃ CÓ CÔNG CỤ CHUYÊN DỤNG.
Chỉ tự tính các hệ 2 ray/3 ray thường hoặc Slim trong bộ giá đã nạp. KHÔNG dùng aivon_report_create hay tự tính nhẩm để làm báo giá Kögen. KHÔNG lấy bảng giá cũ trong wiki thay cho công cụ. Giá đã có VAT 8%; vận chuyển/lắp đặt chưa có giá, hỏi địa chỉ công trình và ghi báo sau.
Khi đã có rộng và cao, bắt buộc gọi aivon_kogen_check_size ngay, chưa cần tên khách hay thông tin công trình. Diện tích thực dưới 3,1m²: nói rõ kích thước quá nhỏ không thể làm cửa, không hỏi tiếp để xuất báo giá và không tạo/gửi PDF. Kiểm tra trên diện tích thực trước khi làm tròn; không biến 3,05m² thành đủ điều kiện chỉ vì làm tròn thành 3,1m². Ngưỡng 3,1m² áp dụng cho mọi cấu hình đang có.\nHỏi lần lượt thông tin thực sự còn thiếu: tên người liên hệ/đại lý, số điện thoại, tên và địa chỉ công trình; hệ 2 hay 3 ray, thường hay Slim, số cánh, rộng/cao (xác nhận đơn vị và đổi mm), số bộ, 1 hay 2 chiều mở (3 ray bảng hiện có chỉ 1 chiều), màu, có ô fix không, không kính hay kính cường lực 8mm, có lấy tay nắm D350/D600 không và số lượng. Bản lề/khóa thêm chỉ tính khi khách yêu cầu. Không hỏi lại thông tin khách đã nói. Không tự chọn kính, tay nắm hay chiều mở còn thiếu.
Khi nhận được thông tin khách/công trình, gọi aivon_kogen_customer ngay để lưu/cập nhật; chỉ dùng thông tin khách đã cung cấp, không tự đặt tên/số điện thoại/địa chỉ. Dùng new_project=true khi khách yêu cầu công trình mới. Mặc định nối tiếp yêu cầu gần nhất của chính người đang nhắn. Nói ngắn gọn thông tin được lưu để bộ phận kinh doanh liên hệ.
Khi đủ dữ liệu và khách muốn báo giá, gọi aivon_kogen_quote; công cụ tự chọn khoảng, làm tròn lên 0,1m² cho cả chọn giá và tính tiền, áp giá trọn bộ/m², kính, phụ kiện và tạo PDF đúng mẫu. Sau đó gọi aivon_report_send với file_id nhận được. Không cần xin phép thêm để gửi vào chính cuộc trò chuyện này. Nếu diện tích vượt mốc cuối, công cụ áp đơn giá/m² của khoảng cuối của đúng cấu hình nhân diện tích khách yêu cầu làm tròn lên 0,1m²; không giới hạn diện tích tính tiền ở mốc tối đa. Nếu cấu hình, kính, màu hoặc phụ kiện chưa có giá, chuyển kinh doanh xác nhận; không mượn giá sản phẩm khác. Không tuyên bố đã lưu Google Sheets hoặc đã gửi PDF nếu công cụ chưa xác nhận. Không đưa link sổ khách hàng hay dữ liệu của khách khác cho người nhắn.
'''

LEAD_HEADERS=['Mã yêu cầu','Cập nhật lúc','Kênh','Tài khoản','Mã cuộc chat','Tên Zalo','Tên khách hàng','Điện thoại','Đại lý / Công ty','Tên công trình','Địa chỉ công trình','Khu vực','Ghi chú','Trạng thái']
QUOTE_HEADERS=['Mã báo giá','Mã yêu cầu','Ngày báo giá','Tên khách hàng','Điện thoại','Đại lý / Công ty','Công trình','Địa chỉ','Khu vực','Sản phẩm','Số bộ','Diện tích thực m²','Diện tích tính tiền m²','Tiền khung theo bảng','Điều chỉnh kính','Phụ kiện Jingchen','Phụ kiện thêm','Phụ phí ô fix','Tổng đã gồm VAT','VAT','Vận chuyển lắp đặt','Tên file PDF','Trạng thái gửi','Phiên bản bảng giá','Cấu hình chi tiết']

def now():
    import localefmt
    return datetime.now(localefmt.tz()).isoformat(timespec='seconds')
def _cfg():return json.loads(CONFIG.read_text(encoding='utf-8'))
def scope_key(scope,account_id):
    return hashlib.sha256((str(account_id)+'|'+scope['chat_id']+'|'+scope['sender_id']).encode()).hexdigest()
@contextmanager
def _db(root):
    path=Path(root)/'Aivon'/'kogen-quotes'
    path.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path/'records.sqlite3',timeout=15)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    for table in ('leads','quotes'):
        conn.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,scope TEXT NOT NULL,
            body TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,synced_version INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,last_error TEXT NOT NULL DEFAULT '')''')
    conn.commit()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
def _get(root,kind,rid=None,scope=None):
    with _db(root) as c:
        if rid:
            row=c.execute(f'SELECT * FROM {kind} WHERE id=?'+(' AND scope=?' if scope else ''),([rid,scope] if scope else [rid])).fetchone()
        else:row=c.execute(f'SELECT * FROM {kind} WHERE scope=? ORDER BY seq DESC LIMIT 1',(scope,)).fetchone()
        return dict(row) if row else None
def _put(root,kind,rid,scope,body):
    with _db(root) as c:
        c.execute(f'''INSERT INTO {kind}(id,scope,body,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET body=excluded.body,updated_at=excluded.updated_at,version={kind}.version+1''',
            (rid,scope,json.dumps(body,ensure_ascii=False),now()))
    return _get(root,kind,rid,scope)

def _unwrap(value):
    for _ in range(8):
        if isinstance(value,dict) and isinstance(value.get('content'),list):
            txt=[v.get('text','') for v in value['content'] if v.get('type')=='text']
            if len(txt)==1:
                try:
                    # Hub receipts may append an operational note after the JSON tool result.
                    value=json.JSONDecoder().raw_decode(txt[0].lstrip())[0]
                    continue
                except ValueError:raise RuntimeError('Composio không hoàn tất yêu cầu.')
        break
    return value
def _execute_sync(slug,args):
    cfg=_cfg()
    host=Path(__file__).parent
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',
        'Authorization':'Bearer '+(host/'.hub_token').read_text().strip(),'X-Aivon-Mode':'full'}
    payload={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'aivon_run_tool','arguments':{
        'name':'composio__COMPOSIO_MULTI_EXECUTE_TOOL','args':{'tools':[{'tool_slug':slug,'arguments':args,'account':cfg['sheets_account']}],
        'sync_response_to_workbench':False,'current_step':'SAVING_KOGEN_QUOTATION'}}}}
    req=urllib.request.Request('http://127.0.0.1:7979/hub/mcp',data=json.dumps(payload).encode(),headers=headers)
    raw=urllib.request.urlopen(req,timeout=45).read().decode()
    try:obj=json.loads(raw)
    except ValueError:obj=next(json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:'))
    r=_unwrap(obj.get('result',obj))
    if not isinstance(r,dict) or not r.get('successful'):raise RuntimeError('Kết nối Composio/Sheets chưa ghi được dữ liệu.')
    result=r.get('data',{}).get('results',[])
    if len(result)!=1 or result[0].get('error'):raise RuntimeError('Composio trả lỗi khi ghi sổ.')
    response=result[0].get('response') or {}
    if not response.get('successful'):raise RuntimeError('Google Sheets chưa xác nhận dữ liệu.')
    return response.get('data') or {}
async def _execute(slug,args):return await asyncio.to_thread(_execute_sync,slug,args)

def _row(kind,rid,body):
    if kind=='leads':
        return [rid,body['updated_at'],'zalo_personal',body['account_id'],body['chat_id'],body.get('zalo_name',''),body.get('customer_name',''),body.get('phone',''),body.get('company',''),body.get('project_name',''),body.get('project_address',''),body.get('market',''),body.get('notes',''),'Đang tư vấn']
    c=body['customer'];calc=body['calculation'];t=calc['totals']
    return [rid,body['lead_id'],body['created_at'],c.get('customer_name',''),c.get('phone',''),c.get('company',''),c.get('project_name',''),c.get('project_address',''),'Miền Nam',
        '; '.join(l['label'] for l in calc['lines']),t['total_quantity'],float(t['area_actual_m2']),float(t['area_billed_m2']),t['frame_amount'],t['glass_amount'],t['hardware_amount'],t['extra_amount'],t['fix_amount'],t['total_vat_included'],'Đã bao gồm 8%','Báo sau theo vị trí',body.get('filename',''),body.get('delivery_status','Chưa gửi'),calc['catalog_version'],json.dumps(calc['lines'],ensure_ascii=False)]

async def sync_record(root,kind,rid):
    lock=_LOCKS.setdefault(('sync',str(root),kind,rid),asyncio.Lock())
    async with lock:
        rec=_get(root,kind,rid)
        if not rec:return False
        if rec['synced_version']==rec['version']:return True
        cfg=_cfg();tab='Khach_hang' if kind=='leads' else 'Bao_gia';n=rec['seq']+1
        row=_row(kind,rid,json.loads(rec['body']))
        try:
            # A fixed row makes retries idempotent. Refuse to overwrite an ID moved by manual sorting.
            read=await _execute('GOOGLESHEETS_BATCH_GET',{'spreadsheet_id':cfg['spreadsheet_id'],'ranges':[f'{tab}!A{n}:A{n}']})
            value_ranges=read.get('valueRanges',read.get('value_ranges',[]))
            existing=value_ranges[0].get('values',[]) if value_ranges else []
            if existing and existing[0] and existing[0][0] not in ('',rid):
                raise RuntimeError('Dòng Google Sheets đã bị di chuyển; cần chủ kiểm tra sổ trước khi ghi.')
            await _execute('GOOGLESHEETS_VALUES_UPDATE',{'spreadsheet_id':cfg['spreadsheet_id'],'range':f'{tab}!A{n}:'+('N' if kind=='leads' else 'Y')+str(n),'values':[row],'value_input_option':'RAW','auto_expand_sheet':True})
            with _db(root) as c:c.execute(f'UPDATE {kind} SET synced_version=?,last_error=? WHERE id=? AND version=?',(rec['version'],'',rid,rec['version']))
            return True
        except Exception as e:
            with _db(root) as c:c.execute(f'UPDATE {kind} SET last_error=? WHERE id=?',(str(e)[:200],rid))
            return False

async def sync_loop(root):
    while True:
        try:
            for kind in ('leads','quotes'):
                with _db(root) as c:ids=[r[0] for r in c.execute(f'SELECT id FROM {kind} WHERE synced_version<version ORDER BY seq LIMIT 8')]
                for rid in ids:await sync_record(root,kind,rid)
        except asyncio.CancelledError:raise
        except Exception as exc:print('[kogen-sync]',type(exc).__name__,flush=True)
        await asyncio.sleep(60)

async def mark_delivery(root,quote_id,status):
    rec=_get(root,'quotes',quote_id)
    if not rec:return
    b=json.loads(rec['body']);b['delivery_status']=status
    _put(root,'quotes',quote_id,rec['scope'],b)
    # The periodic worker syncs this receipt; never delay the delivered file on Google availability.

def build(root,scope,account_id,check,export_pdf):
    if not CONFIG.exists():return [],{}
    sk=scope_key(scope,account_id)
    def clean(value,maxlen=500):
        s=str(value or '').strip()
        if len(s)>maxlen:raise ValueError('Thông tin khách hàng quá dài.')
        return ''.join(c for c in s if c in '\n\t' or ord(c)>=32)
    async def size_check(args):
        check()
        result=check_size(args.get("width_mm"),args.get("height_mm"))
        check()
        return json.dumps(dict(ok=True,**result),ensure_ascii=False)
    async def customer(args):
        check()
        rid=clean(args.get('lead_id'),60)
        rec=_get(root,'leads',rid,sk) if rid else (None if args.get('new_project') else _get(root,'leads',scope=sk))
        if rid and not rec:raise ValueError('Không có yêu cầu này của người nhắn trong cuộc trò chuyện hiện tại.')
        data=json.loads(rec['body']) if rec else {}
        for field in ('customer_name','phone','company','project_name','project_address','market','notes'):
            if field in args and args[field] is not None:
                value=clean(args[field],1500 if field=='notes' else 500)
                if value:data[field]=value
        if not any(data.get(k) for k in ('customer_name','phone','project_name','project_address')):raise ValueError('Chưa có thông tin khách hoặc công trình để lưu.')
        if data.get('phone') and not 7<=len(re.sub(r'\D','',data['phone']))<=15:raise ValueError('Số điện thoại chưa hợp lệ; hỏi khách xác nhận lại.')
        if data.get('market') not in (None,'','mien_nam','other','unknown'):raise ValueError('Khu vực thị trường chưa hợp lệ.')
        rid=rec['id'] if rec else 'KH-'+uuid.uuid4().hex[:16].upper()
        data.update({'account_id':str(account_id),'chat_id':scope['chat_id'],'sender_id':scope['sender_id'],'updated_at':now()})
        _put(root,'leads',rid,sk,data)
        synced=await sync_record(root,'leads',rid)
        missing=[k for k in ('customer_name','phone','project_name','project_address','market') if not data.get(k) or (k=='market' and data[k]=='unknown')]
        return json.dumps({'ok':True,'lead_id':rid,'saved_local':True,'saved_google_sheets':synced,'missing_fields':missing,
            'message':'Đã lưu thông tin vào Google Sheets.' if synced else 'Đã lưu tại Aivon, Google Sheets đang chờ đồng bộ; không nói đã ghi Sheets.'},ensure_ascii=False)
    async def quotation(args):
        check()
        rid=str(args.get('lead_id') or '')
        lead=_get(root,'leads',rid,sk) if rid else _get(root,'leads',scope=sk)
        if not lead:raise ValueError('Chưa có thông tin khách/công trình; dùng aivon_kogen_customer trước.')
        client=json.loads(lead['body'])
        missing=[k for k in ('customer_name','phone','project_name','project_address') if not client.get(k)]
        if missing:raise ValueError('Cần bổ sung trước khi xuất báo giá: '+', '.join(missing))
        if client.get('market')!='mien_nam':raise ValueError('Bộ giá hiện tại chỉ áp dụng miền Nam. Xác nhận vị trí công trình; khu vực khác cần kinh doanh báo riêng.')
        calc=calculate(args.get('items'))
        stable_client={k:v for k,v in client.items() if k!='updated_at'}
        fingerprint=hashlib.sha256(json.dumps({'customer':stable_client,'calculation':calc},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        async with _LOCKS.setdefault(('quote',str(root),sk),asyncio.Lock()):
            with _db(root) as c:
                old=[dict(r) for r in c.execute('SELECT * FROM quotes WHERE scope=? ORDER BY seq DESC LIMIT 20',(sk,))]
            previous=next((json.loads(r['body']) for r in old if json.loads(r['body']).get('fingerprint')==fingerprint and json.loads(r['body']).get('file_id')),None)
            if previous:
                return json.dumps({'ok':True,'quote_id':previous['quote_id'],'file_id':previous['file_id'],'total_vat_included':calc['totals']['total_vat_included'],'already_created':True},ensure_ascii=False)
            qid='KG-'+now()[:10].replace('-','')+'-'+uuid.uuid4().hex[:8].upper()
            quote={'quote_id':qid,'lead_id':lead['id'],'created_at':now(),'customer':client,'calculation':calc,'fingerprint':fingerprint,'delivery_status':'Chưa gửi'}
            result=await export_pdf(quote)
            check()
            quote.update({'file_id':result['file_id'],'filename':result['filename']})
            _put(root,'quotes',qid,sk,quote)
            synced=await sync_record(root,'quotes',qid)
            return json.dumps({'ok':True,'quote_id':qid,'file_id':quote['file_id'],'filename':quote['filename'],'total_vat_included':calc['totals']['total_vat_included'],
                'vat_note':'Đã gồm VAT 8%, không cộng thêm.','transport_installation':calc['transport_installation'],'saved_google_sheets':synced,'lines':calc['lines']},ensure_ascii=False)
    string={'type':'string'};integer={'type':'integer','minimum':0}
    fields={k:string for k in ('lead_id','customer_name','phone','company','project_name','project_address','notes')}
    fields['market']={'type':'string','enum':['mien_nam','other','unknown']};fields['new_project']={'type':'boolean'}
    item_props={'rails':{'type':'integer','enum':[2,3]},'variant':{'type':'string','enum':['standard','slim']},'leaves':{'type':'integer','enum':[2,3,4,6]},'width_mm':{'type':'integer','minimum':1},'height_mm':{'type':'integer','minimum':1},'quantity':{'type':'integer','minimum':1},'direction':{'type':'string','enum':['one_way','two_way']},'color':{'type':'string','enum':['gray','brown']},'glass':{'type':'string','enum':['none','tempered_8mm']},'has_fix':{'type':'boolean'},'handle':{'type':'string','enum':['none','d350','d600']},'handle_qty':integer,'extra_hinges':integer,'smart_lock_qty':integer}
    def tool(name,description,props,required):return {'fn':name,'name':name,'server':'aivon','description':description,'schema':{'type':'object','properties':props,'required':required,'additionalProperties':False}}
    specs=[tool('aivon_kogen_check_size','Kiểm tra diện tích thực tối thiểu 3,1m² ngay khi có rộng và cao (mm), không cần thông tin khách. Dưới ngưỡng thì không thể làm cửa, không xuất báo giá.',{'width_mm':{'type':'integer','minimum':1},'height_mm':{'type':'integer','minimum':1}},['width_mm','height_mm']),
        tool('aivon_kogen_customer','Lưu/cập nhật thông tin khách và công trình của CHÍNH người đang nhắn vào sổ cố định. Không đọc khách khác. Chỉ điền dữ liệu khách thực sự cung cấp.',fields,[]),
        tool('aivon_kogen_quote','Tính báo giá Kögen miền Nam chính xác theo bảng giá và tạo PDF có thương hiệu. Cần lưu đủ khách/công trình trước. Trả file_id để gửi bằng aivon_report_send.',{'lead_id':string,'items':{'type':'array','minItems':1,'maxItems':10,'items':{'type':'object','properties':item_props,'required':[k for k in item_props if k not in ('extra_hinges','smart_lock_qty')],'additionalProperties':False}}},['items'])]
    return specs,{'aivon_kogen_check_size':{'call':size_check},'aivon_kogen_customer':{'call':customer},'aivon_kogen_quote':{'call':quotation}}
