"""Regression checks for the owner-approved 2026-11-11 workbook and PDF policy."""
import sys,json,re,hashlib,unittest
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'server'))
import kogen_pricing as pricing

class KenwinPolicy(unittest.TestCase):
 def item(self,**changes):
  value=dict(leaves=4,width_mm=3800,height_mm=2800,variant='standard',direction='one_way',color='gray',glass='none',quantity=1,has_fix=True,fix_height_mm=400,handle='d600',handle_qty=2)
  value.update(changes);return value
 def test_workbook_rates(self):
  import openpyxl
  cat=pricing.catalog();source=ROOT/'server'/cat['source_file']
  self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),cat['source_sha256'])
  wb=openpyxl.load_workbook(source,data_only=True);count=0
  for key,p in cat['products'].items():
   rails,variant,leaves=key.split('_');sheet=wb['2-4 cánh' if rails=='2ray' else '3C-6C']
   start=(8 if leaves in ('2','3') else 12)+(10 if variant=='slim' else 0)
   for color,glasses in p['prices_by_color'].items():
    self.assertEqual(len(glasses),14)
    for glass,bands in glasses.items():
     for i,band in enumerate(bands):
      row=start+(20 if color=='wood_grain_trac' else 0)+i
      value=sheet[f"{cat['glass_columns'][glass]}{row}"].value
      if isinstance(value,str):value=int(re.sub(r'\D','',value))
      upper=re.findall(r'\d+(?:,\d+)?',str(sheet[f'C{row}'].value).replace('m2',''))[-1].replace(',','.')
      self.assertEqual((Decimal(band[0]),band[1]),(Decimal(upper),value),(key,color,glass,row))
      count+=1
   col='D' if leaves in ('2','3') else 'E'
   for direction,amount in p['hardware'].items():
    row=(41+(2 if variant=='slim' else 0)+(1 if direction=='two_way' else 0)) if rails=='2ray' else 41+(1 if variant=='slim' else 0)
    self.assertEqual(sheet[f'{col}{row}'].value,amount)
  self.assertEqual(count,980)
 def test_all_glass_choices_and_no_extra_charge(self):
  for glass in pricing.catalog()['glass_columns']:
   line=pricing.calculate_item(self.item(glass=glass))
   self.assertEqual(line['glass_amount'],0)
   self.assertEqual(line['color_amount'],0)
  with self.assertRaises(ValueError):pricing.calculate_item(self.item(glass='tempered_6mm'))
 def test_fix_and_hinges(self):
  for leaves in (2,3,4,6):
   for height in (2699,2700,2701):
    for fix in (False,True):
     for direction in (('one_way','two_way') if leaves in (2,4) else ('one_way',)):
      line=pricing.calculate_item(self.item(leaves=leaves,height_mm=height+(400 if fix else 0),has_fix=fix,fix_height_mm=400 if fix else None,direction=direction,extra_hinges=0))
      expected=(1 if leaves in (2,3) else 2) if height>2700 and direction=='one_way' else 0
      self.assertEqual(line['extra_hinges'],expected)
  with self.assertRaisesRegex(ValueError,'fix_height_mm'):pricing.calculate_item(self.item(fix_height_mm=None))
  with self.assertRaisesRegex(ValueError,'Ngô Long'):pricing.calculate_item(self.item(fix_shape='arched'))
  a=pricing.calculate_item(self.item(handle_color='black'));b=pricing.calculate_item(self.item(handle_color='silver'))
  self.assertEqual(a['line_total'],b['line_total'])
  # Recommended leaf dimensions must not block a valid quotation.
  pricing.calculate_item(self.item(width_mm=5000,height_mm=3000,fix_height_mm=100))
 def test_exact_new_glass_values(self):
  cat=pricing.catalog()
  for glass,expected in [('tempered_8mm',2730000),('laminated_8_38mm_clear',2880000),('insulated_5cl_9_5cl',3070000)]:
   self.assertEqual(cat['products']['2ray_standard_2']['prices_by_color']['gray'][glass][1][1],expected)
  self.assertEqual([b[1] for b in cat['products']['3ray_standard_6']['prices_by_color']['gray']['tempered_5mm'][-2:]],[2500000,2400000])

if __name__=='__main__':unittest.main()
