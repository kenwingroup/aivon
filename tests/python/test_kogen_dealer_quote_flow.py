import asyncio,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch,AsyncMock
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'server'))
import chatbot_reports,kogen_quotes
async def main():
 scope=dict(kenh='zalo_personal',chat_id='test-chat',sender_id='test-chat',chat_type='private',session_id='')
 with tempfile.TemporaryDirectory(dir='.') as root:
  with patch.object(chatbot_reports,'_scope',return_value=scope),patch.object(kogen_quotes,'sync_record',new=AsyncMock(return_value=False)):
   tools,routes=chatbot_reports.build(root,'test-bot','test-account')
   customer=json.loads(await routes['aivon_kogen_customer']['call'](dict(prepared_by='Người gửi kiểm thử',company='Test Dealer',phone='0900000000',project_address='Test address',market='mien_nam')))
   assert customer['missing_fields']==[],customer
   args=dict(items=[dict(leaves=4,width_mm=3000,height_mm=2500,variant='standard',direction='one_way',color='gray',glass='none',quantity=1,has_fix=False,handle='d600',handle_qty=2)])
   quote=json.loads(await routes['aivon_kogen_quote']['call'](args))
   assert quote['ok'],quote
   repeat=json.loads(await routes['aivon_kogen_quote']['call'](args))
   assert repeat['file_id']==quote['file_id']
   import zalo_cli,zalo_personal_channel
   with patch.object(zalo_personal_channel,'ket_noi_theo_id',return_value={ 'id':'test-account'}),patch.object(zalo_cli,'home_of',return_value=root),patch.object(zalo_cli,'send_files',new=AsyncMock(return_value=(True,{'success':True},''))) as send:
    result=json.loads(await routes['aivon_report_send']['call']({'file_id':quote['file_id']}))
    assert result['ok'],result
    again=json.loads(await routes['aivon_report_send']['call']({'file_id':quote['file_id']}))
    assert again['already_sent'] and send.await_count==1
    assert send.call_args.args[2]=='test-chat'
    manifest_path=next(Path(root).rglob(quote['file_id']+'.json'))
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['catalog_version']='old';manifest['status']='created'
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    try:
     await routes['aivon_report_send']['call']({'file_id':quote['file_id']})
     raise AssertionError('Stale quotation was accepted')
    except ValueError as error:
     assert 'aivon_kogen_quote' in str(error)
    assert send.await_count==1
   assert kogen_quotes._missing_customer_fields({'phone':'0900000000','project_address':'Test'})==['company','prepared_by']
   print('PASS: dealer-only intake, real PDF, reuse, scoped mocked send, no duplicate send, missing name rejected')
if __name__ == '__main__':
 asyncio.run(main())
