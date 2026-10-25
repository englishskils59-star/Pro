import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
import classification_engine as e
import storage_manager as sm
from classification_corrections import record_correction,approved_labels,evaluation_groups

class CorrectionTests(unittest.TestCase):
 def test_explicit_provenance_and_version_history(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'review.sqlite3'
   self.assertEqual(approved_labels(path),[]);self.assertFalse(path.exists())
   with self.assertRaises(ValueError):record_correction(path,record_id='1',text='تم الطلب',approved_status='Current Customer',approved_by='',source='review')
   self.assertFalse(path.exists())
   record_correction(path,record_id='1',text='تم الطلب',approved_status='Current Customer',approved_by='reviewer',source='test-only')
   record_correction(path,record_id='1',text='تم الطلب',approved_status='Potential Customer',approved_by='reviewer',source='test-only')
   rows=approved_labels(path)
   self.assertEqual(len(rows),1);self.assertEqual(rows[0]['revision'],2)
   self.assertEqual(rows[0]['approved_status'],'Potential Customer')
   self.assertEqual(rows[0]['original_text'],'تم الطلب')
 def test_duplicate_groups(self):
  rows=[{'original_text':s} for s in ['تم الطلب من الوادي','تَمّ الطلب من الوادى','تم الطلب من الوادي اليوم','غير مهتم']]
  groups=evaluation_groups(rows,similarity=.8)
  self.assertEqual(groups[0],groups[1]);self.assertEqual(groups[0],groups[2]);self.assertNotEqual(groups[0],groups[3])
 def test_saved_override_survives_reclassification_without_live_writes(self):
  df=pd.DataFrame({'Customer Name':['أحمد'],'Visit Date':pd.to_datetime(['2026-01-01']),'Sales Rep Name':['مندوب'],'Visit Notes':['متابعة العميل']})
  key=sm._visit_key_series(df).iloc[0]
  with tempfile.TemporaryDirectory() as t, patch.object(sm,'get_data_dir',return_value=Path(t)):
   pd.DataFrame({'Key':[key],'Manual Status':['Current Customer']}).to_parquet(Path(t)/'overrides.parquet')
   out,n=sm.apply_saved_overrides(e.classify_dataframe(df))
   self.assertEqual(n,1);self.assertEqual(out.iloc[0]['Display Status'],'Current Customer')
   self.assertEqual(out.iloc[0]['Matched Keywords'],'');self.assertIn('يدوي',out.iloc[0]['Classification Reason'])
   again,_=sm.apply_saved_overrides(e.classify_dataframe(out))
   self.assertEqual(again.iloc[0]['Display Status'],'Current Customer')
   self.assertEqual(again.iloc[0]['Confidence Score'],100)
   (Path(t)/'overrides.parquet').unlink()
   cleared,n=sm.apply_saved_overrides(e.classify_dataframe(out))
   self.assertEqual(n,0)
   self.assertEqual(cleared.iloc[0]['Display Status'],'Unclassified')
   self.assertNotEqual(cleared.iloc[0]['Override Source'],'Manual')

if __name__=='__main__': unittest.main()
