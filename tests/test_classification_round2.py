import unittest
import pandas as pd
import classification_engine as e

class RoundTwoDefinitions(unittest.TestCase):
 def tearDown(self):e.set_custom_rules([])
 def check(self,text,status):self.assertEqual(e.classify_note(text)['suggested_status'],status,text)
 def test_indirect_current(self):
  for s in ['بيسحب الوادي من الموزع','عنده مخزون الوادي من التاجر','بيستخدم بريمو الوادي من خلال موزع','العميل يشتري علف الوادي من موزع','العميل لديه مخزون علف الوادي']:
   with self.subTest(s=s):self.check(s,'current')
 def test_not_client_stock_or_trade(self):
  for s in ['الموزع بيستخدم الوادي','جاره هو بيسحب الوادي','العميل ذكر أن جاره بيسحب الوادي','الموزع عنده مخزون الوادي','عنده مخزون الوادي يخص جاره','اسم الموزع الوادي','بريمو من الموزع']:
   with self.subTest(s=s):self.assertNotIn(e.classify_note(s)['suggested_status'],['current','new'])
 def test_offer_not_actual(self):
  for s in ['عرضنا توفير مخزون الوادي للعميل','سوف نوفر له مخزون الوادي','عرضنا شراء من الوادي','اتفقنا مع الموزع على توفير الوادي للعميل']:
   with self.subTest(s=s):self.assertNotIn(e.classify_note(s)['suggested_status'],['current','new'])
 def test_negative_indirect(self):
  for s in ['لا بيسحب الوادي من الموزع','لم يستخدم العميل علف الوادي','ليس عنده مخزون الوادي','لن يشتري علف الوادي']:
   with self.subTest(s=s):self.assertNotIn(e.classify_note(s)['suggested_status'],['current','new'])
 def test_agreement_potential(self):
  for s in ['اتفقنا على أول طلبية من الوادي','تم الاتفاق على بداية التعامل','العميل مستعد لبدء التعامل مع الوادي','العميل وعد بالطلب من الوادي','تم الاتفاق على طلبية']:
   with self.subTest(s=s):self.check(s,'potential')
 def test_first_actual(self):
  for s in ['تم تنفيذ أول طلبية من الوادي','بدأ أول تعامل مع الوادي','العميل استلم أول طلبية من الوادي','تم طلب نقلة من المصنع وهذه أول مرة يتم السحب من المصنع','تاجر يعمل بعلف المنافس تم اقناع التاجر بعلف الوادي وتم تنفيذ أول طلبية']:
   with self.subTest(s=s):self.check(s,'new')
 def test_no_evidence_first(self):
  for s in ['أول زيارة للتعارف','أول ظهور في الملف','اتفقنا على أول طلبية','عميل جديد','بدأ العمل']:
   with self.subTest(s=s):self.assertNotEqual(e.classify_note(s,True)['suggested_status'],'new')
 def test_actual_without_first(self):
  for s in ['بدأ التعامل مع الوادي','تم الطلب من الوادي','يشتري علف الوادي','شغال الوادي']:
   with self.subTest(s=s):self.check(s,'current')
 def test_competitor_and_refusal(self):
  for s in ['شغال منافس لكنه غير مهتم بالوادي','يتعامل مع المنافس ويرفض التعامل مع الوادي','شراء من المنافس؛ رفض التعامل مع الوادي']:
   with self.subTest(s=s):self.check(s,'not_interested')
 def test_increase_not_new_relationship(self):
  for s in ['بيستخدم الوادي واتفقنا على زيادة المسحوبات','بيسحب الوادي من الموزع؛ تم الاتفاق على زيادة التعامل','شغال الوادي واتفقنا على زيادة السحب']:
   with self.subTest(s=s):self.check(s,'current')
 def test_real_mixed_refusal_stays_review(self):
  self.check('بيستخدم الوادي لكنه غير مهتم بالتعامل مع الوادي','unclassified')
 def test_former_return_not_current_or_new(self):
  for s in ['كان يتعامل معنا وتوقف لكنه يريد الرجوع','كان يتعامل معنا وتوقف ويفكر في الرجوع','كان بيسحب الوادي من الموزع','كان يتعامل معنا وتوقف؛ اتفقنا على العودة']:
   with self.subTest(s=s):self.assertNotIn(e.classify_note(s)['suggested_status'],['current','new'])
 def test_vague_future(self):
  for s in ['إن شاء الله','الفترة القادمة','إن شاء الله الفترة القادمة']:
   with self.subTest(s=s):self.check(s,'unclassified')
 def test_never_infer_unknown_brand(self):
  for s in ['بيستخدم بريمو من الموزع','عنده مخزون منتج الموزع','اسم الموزع أحمد']:
   with self.subTest(s=s):self.assertNotEqual(e.classify_note(s)['suggested_status'],'current')
 def test_new_not_competitor_or_future(self):
  for s in ['تم تنفيذ أول طلبية من المنافس','سيتم تنفيذ أول طلبية من الوادي','لم يتم تنفيذ أول طلبية من الوادي']:
   with self.subTest(s=s):self.assertNotIn(e.classify_note(s)['suggested_status'],['new','current'])
 def test_journey_retains_approved_prior_status(self):
  frame=pd.DataFrame({'Customer Name':['أحمد']*2,'Visit Date':pd.to_datetime(['2026-01-01','2026-02-01']),'Visit Notes':['تم الطلب','متابعة العميل'],'Override Source':['Manual','Rules'],'Display Status':['Current Customer','Unclassified']})
  out=e.classify_dataframe(frame,preserve_manual=True)
  self.assertEqual(out.iloc[1]['Display Status'],'Unclassified')
  journey=e.build_customer_journey(out)
  self.assertEqual(journey.iloc[0]['Latest Status'],'Current Customer')
  self.assertIn('[2026-01-01] Current Customer',journey.iloc[0]['Status History'])
  self.assertIn('[2026-02-01] Unclassified',journey.iloc[0]['Status History'])

if __name__=='__main__':unittest.main()
