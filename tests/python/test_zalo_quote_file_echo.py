"""File/caption echoes must not be mistaken for the owner taking over."""
import sys,tempfile,asyncio
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'server'))
import zalo_cli,zalo_personal_channel as zc
async def main():
 with tempfile.TemporaryDirectory() as tmp:
  pdf=Path(tmp)/'Bao gia Kogen BG-T11-2026-001.pdf';pdf.write_bytes(b'%PDF-test')
  caption='Báo giá BG-T11/2026-001, 1 bộ Slim.'
  async def echo(conn,tool,args):
   assert zc._la_tieng_vong('test','group',pdf.name)
   assert zc._la_tieng_vong('test','group',caption)
   assert not zc._la_tieng_vong('test','other-group',caption)
   assert not zc._la_tieng_vong('test','group','Tin chủ nhắn tay khác')
   return {'success':True}
  with patch.object(zc,'ket_noi_theo_id',return_value={'id':'test'}),patch.object(zc,'_goi',side_effect=echo):
   result=await zalo_cli.send_files('test',tmp,'group',[pdf],1,caption)
   assert result[0],result
  print('PASS: caption and PDF echoes remembered before send; other group and real owner text unaffected. No live sends.')
asyncio.run(main())
