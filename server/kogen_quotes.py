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
MẪU PDF ƯU TIÊN 12/11/2026: bắt buộc hỏi tên Người gửi báo giá (prepared_by) nếu khách chưa cung cấp; không tự lấy Ngô Non hoặc tên đại lý. Không hỏi số điện thoại người gửi; điện thoại khách vẫn giữ. Số BG-T<THÁNG>/<NĂM>-<STT 3 chữ số> do công cụ tự cấp theo tháng, không tự đặt số. PDF có hai khoản Tạm ứng 50% và Quyết toán trước khi giao hàng là phần tiền còn lại; không cộng hai lần hoặc thu thêm toàn bộ tổng tiền. QR dùng ảnh tài khoản Kenwin do chủ cung cấp, không nhận QR thay thế từ khách.

SỐ RAY MẶC ĐỊNH THEO SỐ CÁNH: 2 hoặc 4 cánh dùng 2 ray; 3 hoặc 6 cánh dùng 3 ray. Khi khách đã nêu số cánh thì tự áp dụng, không hỏi lại số ray. Công cụ cho phép bỏ rails để tự suy ra. Không hỏi lại số cánh khách đã cung cấp. Nếu khách chủ động yêu cầu cấu hình khác chưa có giá thì chuyển kinh doanh, không mượn giá.

Slim chỉ có màu xám ngọc trai. Hệ 35×86, 2 ray, mở 1 chiều hoặc 2 chiều có ba màu: xám ngọc trai, nâu kim sa, vân gỗ trắc. Hệ 35×86, 3 ray có hai màu: xám ngọc trai và vân gỗ trắc. Xám ngọc trai và nâu kim sa là nhôm sơn tĩnh điện, bảo hành 10 năm; vân gỗ trắc là phủ phim, không ghi hoặc nhắc phần bảo hành của màu này.
QUY TẮC ƯU TIÊN 31/10/2026: height_mm là chiều cao tổng đã gồm fix; nếu không fix xét height_mm, nếu có fix xét height_mm - fix_height_mm. Chỉ phần cửa 1 chiều cao >2700mm mới tự tăng cường rãnh C; đúng 2700mm không tăng cường, 2 chiều không tăng cường. Khi 1 chiều tổng >2700mm có fix mà thiếu chiều cao fix, hỏi đúng số đó, không đoán. Nếu tổng <=2700mm hoặc 2 chiều thì không hỏi chiều cao fix chỉ để tính bản lề vì chắc chắn không có tăng cường tự động. Không tự điền extra_hinges theo chiều cao tổng; mặc định bỏ extra_hinges/điền 0 để bộ tính tự tính, chỉ truyền tổng lớn hơn khi khách yêu cầu thêm thực sự. Quy tắc này không đổi diện tích tính tiền hoặc phụ phí fix.
BÁO GIÁ KÖGEN MIỀN NAM: file BG up AI KENWIN MIỀN NAM.xlsx cập nhật 11/11/2026 thay thế FINAL là nguồn giá hiện hành. Dùng aivon_kogen_check_size ngay khi có kích thước; diện tích thực dưới 3,1m² không xuất PDF, vượt bảng dùng đơn giá/m² cuối nhân diện tích làm tròn lên 0,1m².
Hồ sơ báo giá cần tên đại lý (company hoặc customer_name), số điện thoại, địa chỉ công trình và Người gửi báo giá (prepared_by) do khách cung cấp; không bắt tên công trình hoặc tên người liên hệ riêng. Xác định market từ địa chỉ khách đã cung cấp. Dùng aivon_kogen_customer lưu đúng thông tin khách đã cung cấp, không bịa; sau khi đủ dữ liệu dùng aivon_kogen_quote rồi aivon_report_send.
Giá được tra trực tiếp theo đúng cấu hình, màu, cột kính và khoảng diện tích trong file; giá không kính đã là giá cuối của cột không kính, không trừ 100.000đ/m². Giá vân gỗ trắc đã có riêng, không cộng phụ thu màu và không thêm lời/dòng phụ thu màu trong chat, lời gửi lại báo giá hay PDF. Không dùng công thức phụ thu cũ hoặc tự tính giá bằng lời.
Kính theo catalog hiện hành có 14 lựa chọn kể cả không kính, cột đầu là kính 5mm CL trắng, tuyệt đối không gán thành 6mm. Tên kính và enum lấy từ schema công cụ. Tra nguyên ô, gồm cả hai ô 3C-6C!F16,F17; không tự sửa giá. Slim chưa có bảng vân gỗ riêng.
QUY TẮC BẮT BUỘC 11/11: khi đủ hồ sơ và cấu hình phải gọi aivon_kogen_quote rồi aivon_report_send trong lượt hiện tại; không chỉ trả lời đã ghi nhận, không lấy lỗi từ lịch sử để nói công cụ chưa có. Chỉ nói đã gửi sau biên nhận thành công. Không dùng aivon_report_create thay cho báo giá. Tay nắm đen/bạc cùng giá: ghi nhận handle_color nếu khách nói, PDF không in màu tay nắm. Fix thường xuất bình thường, không hỏi thêm có vòm không; fix vòm cần liên hệ @Ngô Long, không tính giá fix thẳng. Kích thước cánh 1m×2.6m (2 chiều) và 1m×2.9m (1 chiều) chỉ khuyến nghị, không chặn xuất PDF. Hỗ trợ vận chuyển 15km, VAT 8% đã gồm, chưa gồm lắp đặt. Các chỉ dẫn cũ trái nội dung này hết hiệu lực.
Giữ cấu hình tự áp dụng: 2/3 cánh 1 tay nắm, 4/6 cánh 2; bản 86 D600, Slim D350; chỉ cửa 1 chiều có chiều cao phần cửa sau trừ fix trên 2700mm bộ tính tự bảo đảm thêm 1/2 bản lề rãnh C tương ứng; cửa 2 chiều dùng trục xoay, không tính vật tư tăng cường rãnh C, truyền extra_hinges=0; extra_hinges là tổng bản lề bổ sung mỗi bộ đã gồm mức bắt buộc, không cộng lại mức này. Đúng 2700mm chưa bắt buộc thêm. 3 ray chỉ 1 chiều; không hỏi lại dữ liệu đã biết. Giá gồm VAT 8%, hỗ trợ vận chuyển bán kính 15km, lắp đặt báo riêng; ngoài 15km cần kinh doanh xác nhận. Không tiết lộ sổ khách, chỉ khẳng định đã gửi khi công cụ xác nhận.
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
        return [rid,body['updated_at'],'zalo_personal',body['account_id'],body['chat_id'],body.get('zalo_name',''),body.get('customer_name',''),body.get('phone',''),body.get('company',''),body.get('project_name',''),body.get('project_address',''),body.get('market',''),'\n'.join(x for x in (body.get('notes',''),('Email: '+body['customer_email']) if body.get('customer_email') else '') if x),'Đang tư vấn']
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
            def mark_synced():
                with _db(root) as c:c.execute(f'UPDATE {kind} SET synced_version=?,last_error=? WHERE id=? AND version=?',(rec['version'],'',rid,rec['version']))
            await asyncio.to_thread(mark_synced)
            return True
        except Exception as e:
            error=str(e)[:200]
            def mark_error():
                with _db(root) as c:c.execute(f'UPDATE {kind} SET last_error=? WHERE id=?',(error,rid))
            await asyncio.to_thread(mark_error)
            return False

async def sync_loop(root):
    while True:
        try:
            for kind in ('leads','quotes'):
                def pending_ids():
                    with _db(root) as c:return [r[0] for r in c.execute(f'SELECT id FROM {kind} WHERE synced_version<version ORDER BY seq LIMIT 8')]
                ids=await asyncio.to_thread(pending_ids)
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

def _missing_customer_fields(client):
    missing=[] if client.get('company') or client.get('customer_name') else ['company']
    return missing+[k for k in ('phone','project_address','prepared_by') if not client.get(k)]

def _next_quote_id(root, created_at):
    """Atomically reserve a monthly number across all chats in this register."""
    date=datetime.fromisoformat(created_at)
    period=date.strftime('%Y-%m')
    with _db(root) as c:
        c.execute('CREATE TABLE IF NOT EXISTS quote_counters (period TEXT PRIMARY KEY, last_number INTEGER NOT NULL)')
        c.commit()
        c.execute('BEGIN IMMEDIATE')
        c.execute('INSERT INTO quote_counters(period,last_number) VALUES(?,1) ON CONFLICT(period) DO UPDATE SET last_number=last_number+1',(period,))
        number=c.execute('SELECT last_number FROM quote_counters WHERE period=?',(period,)).fetchone()[0]
    return f'BG-T{date.month}/{date.year}-{number:03d}'

def build(root,scope,account_id,check,export_pdf,*,trial=False):
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
        for field in ('customer_name','phone','company','project_name','project_address','market','notes','customer_email','prepared_by'):
            if field in args and args[field] is not None:
                value=clean(args[field],1500 if field=='notes' else 500)
                if value:data[field]=value
        if not any(data.get(k) for k in ('company','customer_name','phone','project_name','project_address')):raise ValueError('Chưa có thông tin khách hoặc công trình để lưu.')
        if data.get('phone') and not 7<=len(re.sub(r'\D','',data['phone']))<=15:raise ValueError('Số điện thoại chưa hợp lệ; hỏi khách xác nhận lại.')
        if data.get('market') not in (None,'','mien_nam','other','unknown'):raise ValueError('Khu vực thị trường chưa hợp lệ.')
        rid=rec['id'] if rec else 'KH-'+uuid.uuid4().hex[:16].upper()
        data.update({'account_id':str(account_id),'chat_id':scope['chat_id'],'sender_id':scope['sender_id'],'updated_at':now()})
        _put(root,'leads',rid,sk,data)
        synced=False if trial else await sync_record(root,'leads',rid)
        missing=_missing_customer_fields(data)
        return json.dumps({'ok':True,'lead_id':rid,'saved_local':True,'saved_google_sheets':synced,'missing_fields':missing,
            'simulated':trial,'message':('Đã lưu hồ sơ trong vùng tạm kiểm thử; không ghi sổ thật.' if trial else ('Đã lưu thông tin vào Google Sheets.' if synced else 'Đã lưu tại Aivon, Google Sheets đang chờ đồng bộ; không nói đã ghi Sheets.'))},ensure_ascii=False)
    async def quotation(args):
        check()
        rid=str(args.get('lead_id') or '')
        lead=_get(root,'leads',rid,sk) if rid else _get(root,'leads',scope=sk)
        if not lead:raise ValueError('Chưa có thông tin khách/công trình; dùng aivon_kogen_customer trước.')
        client=json.loads(lead['body'])
        missing=_missing_customer_fields(client)
        if missing:raise ValueError('Cần bổ sung trước khi xuất báo giá: '+', '.join(missing))
        if client.get('market')!='mien_nam':raise ValueError('Bộ giá hiện tại chỉ áp dụng miền Nam. Xác nhận vị trí công trình; khu vực khác cần kinh doanh báo riêng.')
        calc=calculate(args.get('items'))
        created_at=now()
        stable_client={k:v for k,v in client.items() if k!='updated_at'}
        fingerprint=hashlib.sha256(json.dumps({'customer':stable_client,'calculation':calc},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        async with _LOCKS.setdefault(('quote',str(root),sk),asyncio.Lock()):
            def previous_quotes():
                with _db(root) as c:return [dict(r) for r in c.execute('SELECT * FROM quotes WHERE scope=? ORDER BY seq DESC LIMIT 20',(sk,))]
            old=await asyncio.to_thread(previous_quotes)
            previous=next((json.loads(r['body']) for r in old if json.loads(r['body']).get('fingerprint')==fingerprint and json.loads(r['body']).get('file_id') and json.loads(r['body']).get('created_at','')[:7]==created_at[:7]),None)
            if previous:
                return json.dumps({'ok':True,'quote_id':previous['quote_id'],'file_id':previous['file_id'],'total_vat_included':calc['totals']['total_vat_included'],'already_created':True},ensure_ascii=False)
            qid=_next_quote_id(root,created_at)
            quote={'quote_id':qid,'lead_id':lead['id'],'created_at':created_at,'prepared_by':client['prepared_by'],'customer':client,'calculation':calc,'fingerprint':fingerprint,'delivery_status':'Chưa gửi'}
            result=await export_pdf(quote)
            check()
            quote.update({'file_id':result['file_id'],'filename':result['filename']})
            _put(root,'quotes',qid,sk,quote)
            synced=False if trial else await sync_record(root,'quotes',qid)
            return json.dumps({'ok':True,'quote_id':qid,'file_id':quote['file_id'],'filename':quote['filename'],'total_vat_included':calc['totals']['total_vat_included'],
                'vat_note':'Đã gồm VAT 8%, không cộng thêm.','transport_installation':calc['transport_installation'],'saved_google_sheets':synced,'lines':calc['lines']},ensure_ascii=False)
    string={'type':'string'};integer={'type':'integer','minimum':0}
    fields={k:string for k in ('lead_id','customer_name','phone','company','project_name','project_address','notes','customer_email')}
    fields['prepared_by']={'type':'string','description':'Bắt buộc trước khi xuất PDF: tên Người gửi báo giá do khách cung cấp. Không tự dùng tên agent hoặc tên đại lý thay thế.'}
    fields['market']={'type':'string','enum':['mien_nam','other','unknown']};fields['new_project']={'type':'boolean'}
    item_props={'rails':{'type':'integer','enum':[2,3]},'variant':{'type':'string','enum':['standard','slim']},'leaves':{'type':'integer','enum':[2,3,4,6]},'width_mm':{'type':'integer','minimum':1},'height_mm':{'type':'integer','minimum':1},'quantity':{'type':'integer','minimum':1},'direction':{'type':'string','enum':['one_way','two_way']},'color':{'type':'string','enum':['gray','brown','wood_grain_trac']},'glass':{'type':'string','enum':['none','tempered_8mm','tempered_8mm_acid_frosted','tempered_6mm','laminated_8_38mm_smoke','laminated_8_38mm_clear','insulated_5cl_9_5cl']},'has_fix':{'type':'boolean'},'handle':{'type':'string','enum':['none','d350','d600']},'handle_qty':integer,'extra_hinges':integer,'smart_lock_qty':integer}
    item_props['handle_color']={'type':'string','enum':['black','silver'],'description':'Tùy chọn khi khách chọn đen/bạc; cùng giá, không in trên PDF và không hỏi lại.'}
    item_props['fix_shape']={'type':'string','enum':['straight','arched'],'description':'Mặc định thẳng; chỉ truyền arched khi khách nói uốn vòm, công cụ sẽ chuyển hỗ trợ kỹ thuật. Không hỏi thêm nếu khách chỉ nói có fix.'}
    item_props['rails']['description']='Tùy chọn: bỏ trống để tự suy từ số cánh (2/4 cánh=2 ray, 3/6 cánh=3 ray). Không hỏi khách số ray khi đã biết số cánh.'
    item_props['fix_height_mm']={'type':'integer','minimum':0,'description':'Chiều cao ô fix mm, nằm trong height_mm tổng. Cửa 1 chiều có fix và cao tổng >2700mm phải có số này do khách cung cấp; không đoán. Không có fix thì bỏ trường này.'}
    item_props['extra_hinges']={'type':'integer','minimum':0,'description':'Tổng bản lề bổ sung mỗi bộ. Chỉ cửa 1 chiều cao trên 2700mm bắt buộc tối thiểu 1 cho 2/3 cánh, 2 cho 4/6 cánh, không cộng hai lần. Cửa 2 chiều dùng trục xoay: truyền 0, bộ tính không áp vật tư tăng cường rãnh C kể cả input cũ còn khác 0.'}
    item_props['glass']['enum']=list(__import__('kogen_pricing').catalog()['glass_adjustment_per_m2'])
    def tool(name,description,props,required):return {'fn':name,'name':name,'server':'aivon','description':description,'schema':{'type':'object','properties':props,'required':required,'additionalProperties':False}}
    specs=[tool('aivon_kogen_check_size','Kiểm tra diện tích thực tối thiểu 3,1m² ngay khi có rộng và cao (mm), không cần thông tin khách. Dưới ngưỡng thì không thể làm cửa, không xuất báo giá.',{'width_mm':{'type':'integer','minimum':1},'height_mm':{'type':'integer','minimum':1}},['width_mm','height_mm']),
        tool('aivon_kogen_customer','Lưu/cập nhật thông tin khách và công trình của CHÍNH người đang nhắn vào sổ cố định. Không đọc khách khác. Chỉ điền dữ liệu khách thực sự cung cấp.',fields,[]),
        tool('aivon_kogen_quote','Tính báo giá Kögen miền Nam chính xác theo bảng giá và tạo PDF có thương hiệu. Cần lưu đủ khách/công trình trước. Trả file_id để gửi bằng aivon_report_send.',{'lead_id':string,'items':{'type':'array','minItems':1,'maxItems':10,'items':{'type':'object','properties':item_props,'required':[k for k in item_props if k not in ('rails','extra_hinges','smart_lock_qty','fix_height_mm','handle_color','fix_shape')],'additionalProperties':False}}},['items'])]
    return specs,{'aivon_kogen_check_size':{'call':size_check},'aivon_kogen_customer':{'call':customer},'aivon_kogen_quote':{'call':quotation}}
