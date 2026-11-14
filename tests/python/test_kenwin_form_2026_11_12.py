"""Monthly serials, required sender, payment and QR regressions for the approved 12/11 form."""
import sys,tempfile,unittest,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch,AsyncMock
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'server'))
import kogen_quotes,kogen_pricing,kogen_quote_pdf,chatbot_reports

class MonthlySerial(unittest.TestCase):
 def test_month_year_reset_and_parallel_unique(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as root:
   self.assertEqual(kogen_quotes._next_quote_id(root,'2026-11-12T10:00:00+07:00'),'BG-T11/2026-001')
   with ThreadPoolExecutor(max_workers=5) as pool:
    numbers=list(pool.map(lambda _:kogen_quotes._next_quote_id(root,'2026-11-12T10:00:00+07:00'),range(15)))
   self.assertEqual({int(n.rsplit('-',1)[1]) for n in numbers},set(range(2,17)))
   self.assertEqual(kogen_quotes._next_quote_id(root,'2026-12-01T00:00:00+07:00'),'BG-T12/2026-001')
   self.assertEqual(kogen_quotes._next_quote_id(root,'2027-11-01T00:00:00+07:00'),'BG-T11/2027-001')
   self.assertEqual(kogen_quotes._next_quote_id(root,'2026-11-12T10:00:00+07:00'),'BG-T11/2026-017')

class FormFlow(unittest.IsolatedAsyncioTestCase):
 async def test_required_sender_pdf_and_month_reuse(self):
  from pypdf import PdfReader
  scope=dict(kenh='zalo_personal',chat_id='test-group',sender_id='test-user',chat_type='group',session_id='')
  item=dict(leaves=4,width_mm=3090,height_mm=2900,variant='standard',direction='one_way',color='gray',glass='none',quantity=1,has_fix=False,handle='d600',handle_qty=2)
  with tempfile.TemporaryDirectory(dir=ROOT) as root:
   with patch.object(chatbot_reports,'_scope',return_value=scope),patch.object(kogen_quotes,'sync_record',new=AsyncMock(return_value=False)),patch.object(kogen_quotes,'now',return_value='2026-11-12T10:00:00+07:00'):
    _,routes=chatbot_reports.build(root,'test-bot','test-account')
    save=routes['aivon_kogen_customer']['call'];create=routes['aivon_kogen_quote']['call']
    lead=json.loads(await save(dict(company='Sample',phone='0900000000',project_address='TP.HCM',market='mien_nam')))
    self.assertEqual(lead['missing_fields'],['prepared_by'])
    with self.assertRaisesRegex(ValueError,'prepared_by'):await create({'items':[item]})
    await save(dict(prepared_by='Nguyễn Văn An'))
    quote=json.loads(await create({'items':[item]}))
    self.assertEqual(quote['quote_id'],'BG-T11/2026-001')
    self.assertNotIn('/',quote['filename'])
    file=next(Path(root).rglob(quote['file_id']+'.pdf'));reader=PdfReader(file)
    text=' '.join(' '.join(p.extract_text() for p in reader.pages).split())
    for label in ('Người gửi báo giá:', 'Nguyễn Văn An', 'BG-T11/2026-001', 'Tạm ứng 50%', 'Quyết toán trước khi giao hàng', '12,565,000'):
     self.assertIn(label,text)
    self.assertNotIn('Quyết toán trước khi xuất cửa',text)
    self.assertNotIn('thanh toán 100%',text)
    self.assertGreaterEqual(len(reader.pages),1)
    self.assertGreaterEqual(sum(len(page.images) for page in reader.pages),3) # letterhead, door, supplied QR
    self.assertEqual(json.loads(await create({'items':[item]}))['file_id'],quote['file_id'])
    with patch.object(kogen_quotes,'now',return_value='2026-12-01T10:00:00+07:00'):
     new=json.loads(await create({'items':[item]}));self.assertEqual(new['quote_id'],'BG-T12/2026-001')
     self.assertNotEqual(new['file_id'],quote['file_id'])

if __name__=='__main__':unittest.main()
