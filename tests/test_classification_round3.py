import unittest
import pandas as pd
import classification_engine as e

class HumanReviewPatterns(unittest.TestCase):
 def check(self,note,status):self.assertEqual(e.classify_note(note)['suggested_status'],status)
 def test_negotiated_offer_not_completed(self):
  for s in ['تم الحديث عن علف الوادي وإمكانية تشغيله من موزع','تكلمنا عن علف الوادي والمتابعة لاحقا','تم الاتفاق على طلب نقلة غدا','تم طلب نقلة','العميل مستعد للعمل معنا من موزع']:
   with self.subTest(s=s):self.check(s,'potential')
 def test_presentation_without_engagement(self):self.check('تم عرض العلف','target')
 def test_nonfeed_does_not_prove_feed(self):
  self.assertNotEqual(e.classify_note('شغال فيدمكس وكتكوت الوادي دفع ثمنها من موزع')['suggested_status'],'current')
  self.assertNotEqual(e.classify_note('يعمل بخلايا تبريد من شركة الوادي')['suggested_status'],'current')
 def test_feed_distinct_from_nonfeed(self):self.check('شغال علف الوادي وكتكوت شركة أخرى','current')
 def test_hypothetical_provider_refusal(self):
  self.check('لو رفض الموزع توفير علف الوادي سيفكر في موزع بديل','potential')
  self.check('رافض العمل من خلال موزع ومحتاج العمل مباشر','potential')
 def test_actual_refusal_not_hypothetical(self):self.check('غير مهتم بعلف الوادي ولا يريد التعامل','not_interested')
 def test_real_conflicting_interest_kept(self):self.check('غير مهتم لكنه مهتم','not_interested')
 def test_credit_request_not_refusal(self):self.check('عرضت عليه العلف والأسعار ومحتاج أجل لتشغيل المزرعة','potential')
 def test_credit_incompatibility_explicit(self):self.check('العميل غير مناسب له العمل كاش','not_interested')
 def test_owner_authorized_new_start(self):self.check('تم البدء في العمل بعلف الوادي والبدء في السحب','new')
 def test_start_plan_not_new(self):self.assertNotEqual(e.classify_note('سيتم البدء في العمل بعلف الوادي والبدء في السحب')['suggested_status'],'new')
 def test_owner_authorized_increase(self):self.check('عميل شغال من موزعه واتفقنا على زيادة المسحوبات','current')
 def test_owner_authorized_inventory_followup(self):self.check('متابعة الكمية المتبقية في المخزن وتم الترتيب على طلب32 طن غدا','current')
 def test_monthly_quantity_not_increase(self):self.check('عميل شغال من تاجر مجهول كميته خمسة طن شهري','target')
 def test_ordinary_followup_is_current(self):self.check('متابعة العميل','current')
 def test_first_future_order_with_increase_not_current(self):
  self.check('هيتم طلب نقلة كأول مرة وزيادة مسحوباته','potential')
 def test_past_tense_elsewhere_does_not_erase_actual(self):self.check('تعمل بالفعل بعلف الوادي وعملت سابقا من موزع آخر','current')
 def test_former_negotiated_return(self):self.check('عميل سابق للوادي تم التفاوض على التساهل في التسديد للعودة','potential')
 def test_previous_promise_is_not_previous_trade(self):
  self.check('تم الوعد سابقا بأنه سيتم العمل معنا بدلا من المنافس','potential')
 def test_former_barrier_no_return(self):
  self.check('عميل سابق للوادي تم التفاوض لكن نزول المنتج صعبة في الفترة الحالية','former')
  self.check('يتعامل بعلف المنافس وكان شغال الوادي وتوقف','former')

class DatedSupplierReferenceTests(unittest.TestCase):
 def batch(self,note,date='2026-02-01',refdate='2026-01-01',status='Current Customer'):
  source=pd.DataFrame({'Customer Name':['موزع تجريبي'],'Visit Date':[refdate],'Display Status':[status],'Governorate':['محافظة'],'Override Source':['Manual'],'Visit Notes':['بيانات مرجعية']})
  row=pd.DataFrame({'Customer Name':['عميل تجريبي'],'Visit Date':[date],'Visit Notes':[note]})
  return e.classify_dataframe(row,reference_records=source).iloc[0]
 def test_past_reference_cited(self):
  row=self.batch('شغال من موزع تجريبي كميته خمسة طن شهري')
  self.assertEqual(row['Display Status'],'Current Customer');self.assertIn('2026-01-01',row['Classification Reason']);self.assertIn('Manual',row['Classification Reason'])
 def test_future_not_used(self):self.assertNotEqual(self.batch('شغال من موزع تجريبي',refdate='2026-03-01')['Display Status'],'Current Customer')
 def test_same_day_ambiguous_not_used(self):self.assertNotEqual(self.batch('شغال من موزع تجريبي',refdate='2026-02-01')['Display Status'],'Current Customer')
 def test_former_supplier_not_current(self):self.assertNotEqual(self.batch('شغال من موزع تجريبي',status='Former Customer')['Display Status'],'Current Customer')
 def test_explicit_competitor_prevents_reference(self):self.assertNotEqual(self.batch('شغال من موزع تجريبي لكنه يستخدم علف المنافس')['Display Status'],'Current Customer')
 def test_name_mention_only_not_used(self):self.assertNotEqual(self.batch('تم ذكر موزع تجريبي')['Display Status'],'Current Customer')
 def test_unknown_supplier_no_mapping(self):self.assertNotEqual(self.batch('شغال من موزع آخر')['Display Status'],'Current Customer')
 def test_negated_relation_does_not_activate_reference(self):
  self.assertNotEqual(self.batch('مش شغال من موزع تجريبي')['Display Status'],'Current Customer')
  self.assertNotEqual(self.batch('لا يشتري من موزع تجريبي')['Display Status'],'Current Customer')
 def test_historical_relation_does_not_activate_current(self):
  self.assertNotEqual(self.batch('كان شغال من موزع تجريبي وتوقف')['Display Status'],'Current Customer')
 def test_record_identity_not_fuzzy(self):self.assertNotEqual(self.batch('شغال من موزع تجريب')['Display Status'],'Current Customer')
 def test_last_status_prevents_old_current_leak(self):
  refs=pd.DataFrame({'Customer Name':['موزع تجريبي']*2,'Visit Date':['2026-01-01','2026-01-20'],'Display Status':['Current Customer','Former Customer']})
  row=pd.DataFrame({'Visit Notes':['شغال من موزع تجريبي'],'Visit Date':['2026-02-01']})
  self.assertNotEqual(e.classify_dataframe(row,reference_records=refs).iloc[0]['Display Status'],'Current Customer')

if __name__=='__main__':unittest.main()
