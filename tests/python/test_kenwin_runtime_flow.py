"""Isolated quotation integration checks. All external delivery and Sheets calls are mocked."""
import asyncio,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'server'))
import chatbot_reports,kogen_quotes,kogen_pricing

class QuoteFlow(unittest.IsolatedAsyncioTestCase):
 async def test_delivery_failures_scope_and_pdf(self):
  with tempfile.TemporaryDirectory(dir='.') as root:
   scope=dict(kenh='zalo_personal',chat_id='test-group',sender_id='sender-one',chat_type='group',session_id='')
   with patch.object(chatbot_reports,'_scope',side_effect=lambda *_:dict(scope)),patch.object(kogen_quotes,'sync_record',new=AsyncMock(return_value=False)):
    _,routes=chatbot_reports.build(root,'test-bot','test-account')
    lead=json.loads(await routes['aivon_kogen_customer']['call'](dict(prepared_by='Người gửi kiểm thử',company='Test Dealer',phone='0900000000',project_address='TP.HCM',market='mien_nam')))
    self.assertEqual(lead['missing_fields'],[])
    item=dict(leaves=4,width_mm=3800,height_mm=2800,variant='standard',direction='one_way',color='gray',glass='none',quantity=1,has_fix=True,fix_height_mm=400,handle='d600',handle_qty=2)
    create=routes['aivon_kogen_quote']['call']
    first=json.loads(await create({'items':[item]}))
    self.assertEqual(first['total_vat_included'],27746000)
    file=next(Path(root).rglob(first['file_id']+'.pdf'))
    self.assertTrue(file.read_bytes().startswith(b'%PDF'))
    from pypdf import PdfReader
    pdf=PdfReader(file)
    text=' '.join(' '.join(page.extract_text() for page in pdf.pages).split())
    for expected in ('Tên đại lý:', 'Tổng DT (m2)', 'Đơn giá TB/m2', 'LƯU Ý', '15km', '10 ngày', 'ĐỂ ĐẢM BẢO CỬA VẬN HÀNH ỔN ĐỊNH', 'cao 2.6m', 'cao 2.9m', '27,746,000'):
     self.assertIn(expected,text)
    for obsolete in ('Email:', 'Để đảm bảo kỹ thuật:', 'chưa bao gồm chi phí lắp đặt và vận chuyển'):
     self.assertNotIn(obsolete,text)
    self.assertEqual(first['file_id'],json.loads(await create({'items':[item]}))['file_id'])
    # Another sender in the same group cannot reuse this sender's customer or lead.
    scope['sender_id']='sender-two'
    _,other=chatbot_reports.build(root,'test-bot','test-account')
    with self.assertRaises(ValueError):await other['aivon_kogen_quote']['call']({'lead_id':lead['lead_id'],'items':[item]})
    scope['sender_id']='sender-one'
    import zalo_cli,zalo_personal_channel
    with patch.object(zalo_personal_channel,'ket_noi_theo_id',return_value={'id':'test-account'}),patch.object(zalo_cli,'home_of',return_value=root):
     with patch.object(zalo_cli,'send_files',new=AsyncMock(return_value=(False,None,'delivery uncertain'))) as send:
      sent=json.loads(await routes['aivon_report_send']['call']({'file_id':first['file_id']}))
      self.assertFalse(sent['ok'])
      with self.assertRaisesRegex(ValueError,'không tự gửi lặp'):
       await routes['aivon_report_send']['call']({'file_id':first['file_id']})
      self.assertEqual(send.await_count,1)
      self.assertEqual(send.call_args.args[2],'test-group');self.assertEqual(send.call_args.args[4],1)
     # Old layout must be rejected before any send attempt.
     changed=json.loads(await create({'items':[dict(item,glass='tempered_5mm')]}))
     manifest_path=next(Path(root).rglob(changed['file_id']+'.json'))
     manifest=json.loads(manifest_path.read_text(encoding='utf-8'));manifest['quote_layout_version']='old'
     manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
     with patch.object(zalo_cli,'send_files',new=AsyncMock()) as send:
      with self.assertRaisesRegex(ValueError,'phiên bản cũ'):
       await routes['aivon_report_send']['call']({'file_id':changed['file_id']})
      send.assert_not_called()
    with self.assertRaisesRegex(ValueError,'Ngô Long'):await create({'items':[dict(item,fix_shape='arched')]})
    # A dead or switched turn loses access to its existing handlers.
    scope['chat_id']='different-chat'
    with self.assertRaises(PermissionError):await create({'items':[item]})

 async def test_verified_contact(self):
  from channels.zalo_personal import _quotation_contact_directory,tag_ten_trong_cau
  uid='2157325870369359849';text='Liên hệ @Ngô Long để được hỗ trợ.'
  with patch('zalo_cli.run_cli',new=AsyncMock(return_value=(True,{'gridInfoMap':{'test-group':{'memVerList':[uid+'_1']}}},''))):
   directory=await _quotation_contact_directory('home','test-group',text,[])
   self.assertEqual(tag_ten_trong_cau(text,directory)[0][1],uid)
  with patch('zalo_cli.run_cli',new=AsyncMock(return_value=(True,{'gridInfoMap':{'test-group':{'memVerList':[]}}},''))):
   self.assertEqual(await _quotation_contact_directory('home','test-group',text,[{'uid':uid,'name':'Ngô Long'}]),[])
  with patch('zalo_cli.run_cli',new=AsyncMock()) as tool:
   await _quotation_contact_directory('home','test-group','Fix thường',[])
   tool.assert_not_called()

class TrialFlow(unittest.IsolatedAsyncioTestCase):
 async def test_trial_cannot_write_vault_sync_sheets_or_send(self):
  scope=dict(kenh='zalo_personal',chat_id='test-group',sender_id='sender-one',chat_type='group',session_id='')
  with tempfile.TemporaryDirectory(dir='.') as vault:
   with patch.object(chatbot_reports,'_scope',return_value=scope),patch.object(kogen_quotes,'sync_record',new=AsyncMock(side_effect=AssertionError('No live sync in trial'))) as sync,patch('zalo_cli.send_files',new=AsyncMock(side_effect=AssertionError('No live send in trial'))) as send:
    _,routes=chatbot_reports.build(vault,'test-bot','test-account',trial=True)
    customer=json.loads(await routes['aivon_kogen_customer']['call'](dict(prepared_by='Người gửi kiểm thử',company='Sample',phone='0900000000',project_address='TP.HCM',market='mien_nam')))
    self.assertTrue(customer['simulated'])
    item=dict(leaves=4,width_mm=3800,height_mm=2800,variant='standard',direction='one_way',color='gray',glass='none',quantity=1,has_fix=True,fix_height_mm=400,handle='d600',handle_qty=2)
    quote=json.loads(await routes['aivon_kogen_quote']['call']({'items':[item]}))
    self.assertEqual(quote['total_vat_included'],27746000)
    result=json.loads(await routes['aivon_report_send']['call']({'file_id':quote['file_id']}))
    self.assertTrue(result['ok'] and result['simulated'])
    again=json.loads(await routes['aivon_report_send']['call']({'file_id':quote['file_id']}))
    self.assertTrue(again['already_sent'] and again['simulated'])
    self.assertEqual(list(Path(vault).iterdir()),[])
    sync.assert_not_called();send.assert_not_called()

if __name__=='__main__':unittest.main()
