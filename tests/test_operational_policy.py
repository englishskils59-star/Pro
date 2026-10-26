import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import pandas as pd
import classification_engine as e
import storage_manager as sm

class OperationalPolicyTests(unittest.TestCase):
 def test_followups(self):
  for note in ['متابعة','متابعة العميل','متابعة التاجر','متابعة المخزن','متابعه','متابعة مخزون قائم','متابعة العميل تليفونيا']:
   with self.subTest(note=note):self.assertEqual(e.classify_note(note)['suggested_status'],'current')
 def test_followup_exceptions(self):
  for note,status in [('متابعة لإقناعه ببدء التعامل','potential'),('متابعة عميل سابق متوقف','former'),('متابعة العميل ولم يكن موجودًا','no_meeting'),('متابعة العميل رفض الشروط المعروضة','not_interested'),('متابعة العميل تم تنفيذ أول طلبية من الوادي','new'),('يتعامل بمنافس ويفكر في تجربة الوادي','potential')]:
   with self.subTest(note=note):self.assertEqual(e.classify_note(note)['suggested_status'],status)
 def test_negative_and_other_party(self):
  for note in ['لم تتم متابعة العميل','سيتم متابعة العميل','متابعة العميل لا يتعامل معنا','متابعة جاره','متابعة العميل يتعامل بالمنافس','متابعة العميل لم يكن مهتما','متابعة العميل لم يوافق على العودة']:
   with self.subTest(note=note):self.assertNotEqual(e.classify_note(note)['suggested_status'],'current')
 def test_default_honest(self):
  result=e.classify_note('ملاحظة بلا تفاصيل')
  self.assertEqual(result['suggested_status'],'target');self.assertEqual(result['confidence'],0);self.assertEqual(result['score'],0);self.assertEqual(result['matched_keywords'],[])
  self.assertIn('مستهدف افتراضيًا',result['reason'])
 def row(self,note,date='2026-02-01',**kw):
  return dict({'Customer Name':'عميل تجريبي','Governorate':'محافظة اختبار','District':'منطقة اختبار','Visit Date':date,'Visit Notes':note},**kw)
 def test_history_new_becomes_current_and_cites_source(self):
  refs=pd.DataFrame([self.row('تم تنفيذ أول طلبية من الوادي','2026-01-01')])
  out=e.classify_dataframe(pd.DataFrame([self.row('تفاصيل غير كافية')]),reference_records=refs).iloc[0]
  self.assertEqual(out['Display Status'],'Current Customer');self.assertEqual(out['Classification Basis'],'History');self.assertIn('2026-01-01',out['Classification Reason']);self.assertEqual(out['Matched Keywords'],'')
 def test_no_future_self_or_name_only(self):
  row=self.row('تفاصيل غير كافية')
  for ref in [self.row('شغال الوادي','2026-02-02'),self.row('شغال الوادي','2026-02-01'),dict(self.row('شغال الوادي','2026-01-01'),Governorate='محافظة اخرى')]:
   self.assertEqual(e.classify_dataframe(pd.DataFrame([row]),reference_records=pd.DataFrame([ref])).iloc[0]['Classification Basis'],'DefaultTarget')
 def test_no_fallback_chain(self):
  ref=self.row('شغال الوادي','2026-01-01',**{'Display Status':'Current Customer','Classification Basis':'History','Classification Reason':'حالة تاريخية موثوقة','Override Source':'Rules'})
  out=e.classify_dataframe(pd.DataFrame([self.row('نص غير حاسم')]),reference_records=pd.DataFrame([ref])).iloc[0]
  self.assertEqual(out['Classification Basis'],'DefaultTarget')
 def test_ambiguous_same_date_history(self):
  refs=pd.DataFrame([self.row('شغال الوادي','2026-01-01'),self.row('غير مهتم','2026-01-01')])
  out=e.classify_dataframe(pd.DataFrame([self.row('تفاصيل غير كافية')]),reference_records=refs).iloc[0]
  self.assertEqual(out['Classification Basis'],'DefaultTarget')
 def test_history_not_override_explicit_visit(self):
  refs=pd.DataFrame([self.row('شغال الوادي','2026-01-01')])
  out=e.classify_dataframe(pd.DataFrame([self.row('متابعة العميل ولم يكن موجودا')]),reference_records=refs).iloc[0]
  self.assertEqual(out['Display Status'],'No Meeting')
 def test_manual_specific_and_released_unclassified(self):
  df=pd.DataFrame([self.row('متابعة'),self.row('متابعة','2026-02-02')])
  keys=sm._visit_key_series(df)
  with TemporaryDirectory() as t,patch.object(sm,'get_data_dir',return_value=Path(t)):
   overrides=pd.DataFrame({'Key':keys,'Manual Status':['Potential Customer','Unclassified']})
   overrides.to_parquet(Path(t)/'overrides.parquet');old=(Path(t)/'overrides.parquet').read_bytes()
   out,n=sm.apply_saved_overrides(e.classify_dataframe(df))
   self.assertEqual(list(out['Display Status']),['Potential Customer','Current Customer']);self.assertEqual(n,1)
   self.assertEqual(out.iloc[0]['Classification Basis'],'Manual');self.assertEqual(out.iloc[0]['Matched Keywords'],'')
   self.assertEqual((Path(t)/'overrides.parquet').read_bytes(),old)
 def test_manual_unclassified_in_memory_reprocessed(self):
  row=self.row('متابعة',**{'Display Status':'Unclassified','Override Source':'Manual'})
  out=e.classify_dataframe(pd.DataFrame([row]),preserve_manual=True).iloc[0]
  self.assertEqual(out['Display Status'],'Current Customer');self.assertEqual(out['Classification Basis'],'Followup')
 def test_no_meeting_journey_keeps_current(self):
  frame=pd.DataFrame([self.row('متابعة','2026-01-01'),self.row('متابعة العميل ولم يكن موجودا')])
  frame['Visit Date']=pd.to_datetime(frame['Visit Date']);out=e.classify_dataframe(frame)
  self.assertEqual(e.build_customer_journey(out).iloc[0]['Latest Status'],'Current Customer')
