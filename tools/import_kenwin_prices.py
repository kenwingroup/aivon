from pathlib import Path
import openpyxl,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'server/kogen_assets/pricing/BG up AI KENWIN MIEN NAM.xlsx'
w=openpyxl.load_workbook(source,data_only=True)
c=json.loads((ROOT/'server/kogen_catalog_final.json').read_text(encoding='utf-8'))
options=[('none','D','Không kính'),('tempered_5mm','F','Kính 5mm CL trắng'),('tempered_8mm','H','Kính 8mm CL trắng'),('laminated_8_38mm_clear','J','Kính 8.38mm trắng'),('insulated_5cl_9_5cl','L','Kính hộp 5CL+9+5CL'),('laminated_8_38mm_acid_frosted','N','Kính 8.38mm nhúng Acid mờ'),('laminated_8_38mm_smoke','P','Kính 8.38mm film xám khói'),('tempered_8mm_smoke','R','Kính 8mm CL xám khói'),('tempered_10mm','T','Kính 10mm CL trắng'),('tempered_12mm','V','Kính 12mm CL trắng'),('insulated_5cl_9_5cl_gold_grid','X','Kính hộp 5CL+9+5CL có nan vàng'),('laminated_8_76mm_semi_tempered_clear','Z','Kính 8.76mm bán cường lực film trong'),('tempered_8mm_reflective_smoke','AB','Kính 8mm CL phản quang xám khói'),('insulated_5cl_clear_9_5cl_smoke','AD','Kính hộp 5CL trắng +9+ 5CL xám khói')]
import re
for key,p in c['products'].items():
 rails,variant,leaves=key.split('_');s=w['2-4 cánh' if rails=='2ray' else '3C-6C'];start=(8 if leaves in ('2','3') else 12)+(10 if variant=='slim' else 0)
 for color,prices in p['prices_by_color'].items():
  startrow=start+(20 if color=='wood_grain_trac' else 0)
  n=4 if leaves in ('2','3') else 6
  prices.clear()
  for glass,col,label in options:
   bands=[]
   for i in range(n):
    row=startrow+i
    upper=re.findall(r'\d+(?:,\d+)?',str(s[f'C{row}'].value).replace('m2',''))[-1].replace(',','.')
    val=s[f'{col}{row}'].value
    if isinstance(val,str):val=int(re.sub(r'\D','',val))
    assert isinstance(val,(int,float)),(key,color,glass,row,val)
    bands.append([upper,int(val),'set' if i==0 else 'm2'])
   prices[glass]=bands
 p['bands']=p['prices_by_color']['gray']['none']
c.update(version='MN-KENWIN-2026-11-11-direct-v1',source_file='kogen_assets/pricing/'+source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),quote_layout_version='BG-KENWIN-20261112-v5',glass_labels={g:label for g,col,label in options},glass_adjustment_per_m2={g:0 for g,col,label in options},glass_columns={g:col for g,col,label in options})
(ROOT/'server/kogen_catalog_kenwin.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
