import unittest
import pandas as pd
import classification_engine as e

class ClassificationBehaviorTests(unittest.TestCase):
 def tearDown(self): e.set_custom_rules([])
 def status(self,note): return e.classify_note(note)['suggested_status']
 def test_interest_and_refusal(self):
  self.assertEqual(self.status('غير مهتم'),'not_interested')
  self.assertEqual(self.status('مهتم'),'potential')
 def test_negated_order(self):
  self.assertNotEqual(self.status('لم يتم الطلب'),'current')
  self.assertEqual(self.status('تم الطلب'),'current')
 def test_future_not_completed(self):
  for s in ['سيتم الطلب','سيتم تحميل بضاعة','هيطلب','سوف يتم الطلب','تم الاتفاق على طلبية']:
   with self.subTest(s=s): self.assertNotEqual(self.status(s),'current')
 def test_supplier(self):
  self.assertEqual(self.status('شراء من الوادي'),'current')
  self.assertEqual(self.status('شراء من المنافس'),'target')
  self.assertNotEqual(self.status('تم الشراء من المنافس'),'current')
 def test_followup_is_current(self):
  self.assertEqual(self.status('متابعة العميل'),'current')
 def test_former(self): self.assertEqual(self.status('كان يتعامل معنا وتوقف'),'former')
 def test_absence(self): self.assertEqual(self.status('لم يكن متواجدًا'),'no_meeting')
 def test_first_visit_not_first_deal(self):
  self.assertNotEqual(e.classify_note('أول زيارة للتعارف',True)['suggested_status'],'new')
 def test_refusal_and_return_follow_operational_policy(self):
  self.assertEqual(self.status('رفض التعامل، لكنه مهتم بالتجربة'),'not_interested')
  self.assertEqual(self.status('كان يتعامل معنا وتوقف لكنه يريد الرجوع'),'potential')
 def test_negation_scope(self):
  self.assertEqual(self.status('لم تتم المقابلة؛ تم الطلب من الوادي'),'current')
  self.assertEqual(self.status('لم يكن مهتمًا لكنه تم الطلب من الوادي'),'current')
 def test_boundaries(self):
  self.assertNotEqual(self.status('اندفع العميل'),'current')
  self.assertNotEqual(self.status('مهتمون بالنقاش'),'potential')
 def test_repeated_evidence(self):
  a=e.classify_note('تم الطلب');b=e.classify_note('تم الطلب تم الطلب تم الطلب')
  self.assertEqual(a['score'],b['score']);self.assertEqual(a['confidence'],b['confidence'])
 def test_custom_duplicates_and_overlap(self):
  e.set_custom_rules([{'keyword':'تم الطلب','status':'current','score':100}]*3)
  self.assertEqual(e.classify_note('تم الطلب')['score'],100)
  self.assertEqual(self.status('غير مهتم لكنه مهتم'),'not_interested')
 def test_spelling_and_spacing(self):
  self.assertEqual(self.status('غَيْرُ   مُهْتَمّ'),'not_interested')
  self.assertEqual(self.status('شراء من الوادى'),'current')
  self.assertEqual(self.status('ومهتم'),'potential')
 def test_empty_missing(self):
  for value in ['',None,float('nan'),pd.NA]:
   with self.subTest(value=str(value)): self.assertEqual(self.status(value),'target')
 def test_batch_contract_invalid_dates_identity(self):
  frame=pd.DataFrame({'Customer Name':['','أحمد','احمد'], 'Visit Date':['bad','2026-01-01','2026-02-01'],'Visit Notes':['متابعة العميل','أول زيارة للتعارف','تم الطلب']})
  before=frame.copy(deep=True);out=e.classify_dataframe(frame)
  pd.testing.assert_frame_equal(frame,before)
  self.assertEqual(len(out),3);self.assertEqual(set(out['Customer Name']),set(frame['Customer Name']))
  self.assertTrue(set(out['Suggested Status']).issubset(e.STATUS_DISPLAY))
  self.assertFalse(out['Visit Notes'].isna().any())
  self.assertTrue(pd.api.types.is_numeric_dtype(out['Confidence Score']))
 def test_no_future_leakage(self):
  first=pd.DataFrame({'Customer Name':['أحمد'],'Visit Date':pd.to_datetime(['2026-01-01']),'Visit Notes':['متابعة العميل']})
  later=pd.concat([first,pd.DataFrame({'Customer Name':['أحمد'],'Visit Date':pd.to_datetime(['2026-02-01']),'Visit Notes':['تم الطلب']})],ignore_index=True)
  self.assertEqual(e.classify_dataframe(first).iloc[0]['Display Status'],e.classify_dataframe(later).iloc[0]['Display Status'])
 def test_manual_retained(self):
  df=pd.DataFrame({'Customer Name':['أحمد'],'Visit Date':pd.to_datetime(['2026-01-01']),'Visit Notes':['متابعة العميل'],'Override Source':['Manual'],'Display Status':['Current Customer'],'Suggested Status':['current']})
  out=e.classify_dataframe(df,preserve_manual=True)
  self.assertEqual(out.iloc[0]['Display Status'],'Current Customer')
  self.assertIn('يدوي',out.iloc[0]['Classification Reason'])
 def test_generic_purchase_abstains(self): self.assertEqual(self.status('شراء'),'target')
 def test_reason_is_evidence_index(self): self.assertIn('ليست احتمال',e.classify_note('تم الطلب')['reason'])

class AdditionalBoundaryTests(unittest.TestCase):
 def tearDown(self):e.set_custom_rules([])
 def test_negation_does_not_swallow_next_proposition(self):
  self.assertEqual(e.classify_note('لم يتم الطلب والعميل مهتم')['suggested_status'],'potential')
 def test_new_future_not_completed(self):
  self.assertNotEqual(e.classify_note('سوف بدأ العمل')['suggested_status'],'new')
 def test_cache_invalidates_with_rules(self):
  self.assertEqual(e.classify_note('عبارة مراجعة خاصة')['suggested_status'],'target')
  e.set_custom_rules([{'keyword':'عبارة مراجعة خاصة','status':'potential','score':60}])
  self.assertEqual(e.classify_note('عبارة مراجعة خاصة')['suggested_status'],'potential')
  e.set_custom_rules([])
  self.assertEqual(e.classify_note('عبارة مراجعة خاصة')['suggested_status'],'target')
 def test_same_phrase_conflicting_custom_labels(self):
  e.set_custom_rules([{'keyword':'عبارة خاصة','status':'current','score':100},{'keyword':'عبارة خاصة','status':'not_interested','score':100}])
  self.assertEqual(e.classify_note('عبارة خاصة')['suggested_status'],'target')
 def test_empty_and_duplicate_indices(self):
  empty=e.classify_dataframe(pd.DataFrame(columns=['Visit Date','Visit Notes']))
  self.assertEqual(len(empty),0);self.assertIn('Raw Score',empty)
  df=pd.DataFrame({'Visit Date':['bad','2020-01-01'],'Visit Notes':['مهتم','تم الطلب']},index=[1,1])
  out=e.classify_dataframe(df)
  self.assertEqual(len(out),2);self.assertEqual(out.iloc[0]['Visit Notes'],'تم الطلب')
 def test_missing_date_column(self):
  out=e.classify_dataframe(pd.DataFrame({'Visit Notes':['تم الطلب']}))
  self.assertEqual(out.iloc[0]['Suggested Status'],'current')
 def test_no_meeting_preserves_customer_standing(self):
  frame=pd.DataFrame({'Customer Name':['أحمد','أحمد'],'Visit Date':pd.to_datetime(['2026-01-01','2026-02-01']),'Visit Notes':['تم الطلب','لم تتم المقابلة']})
  out=e.classify_dataframe(frame)
  self.assertEqual(e.build_customer_journey(out).iloc[0]['Latest Status'],'Current Customer')

if __name__=='__main__':unittest.main()
