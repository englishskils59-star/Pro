import unittest
import classification_engine as e
import classification_context as c

class AbstentionFixTests(unittest.TestCase):
 def check(self,note,status):self.assertEqual(e.classify_note(note)['suggested_status'],status,note)
 def test_quantity_stock(self):
  for n in ['موجود لديه 6 طن الوادي','عنده ٣طن الوادي','لديه 2.5 طن علف الوادي','لسه باقي عنده الوادي من اخر نقلة']:self.check(n,'current')
 def test_number_and_unit_join(self):
  self.check('مزرعة 8000 بياض عمر 20 يوميتعامل مع علف الوادى بياض بادى 1','current')
  self.check('مزرعة8000 عمر20يوميتعامل مع علف الوادي','current')
 def test_future(self):
  for n in ['متوقع يبدأ الشهر القادم بعلف الوادي','هيبدأ معانا خلال الفترة القادمة','سيبدأ بعلف الوادي الشهر القادم']:self.check(n,'potential')
 def test_former(self):self.check('يشتغل في مكة و كان شغال الوادي من فترة','former')
 def test_absence(self):
  for n in ['لم يكن التاجر موجود و سيتم تكرار الزيارة','التاجر لم يكن موجود','لم يكن العميل متواجدا']:self.check(n,'no_meeting')
 def test_stock_negation_and_offer(self):
  for n in ['ليس لديه 6 طن الوادي','غير موجود لديه 6 طن الوادي','سيتم توفير مخزون لديه 6 طن الوادي','كان موجود لديه 6 طن الوادي','لديه 6 طن المنافس وتم ذكر الوادي','لديه 6 طن الوادي للنيل','لديه 6 طن الوادي مخزون يخص جاره']:
   self.assertNotEqual(e.classify_note(n)['suggested_status'],'current',n)
 def test_third_party_stock(self):self.assertNotEqual(e.classify_note('جاره موجود لديه 6 طن الوادي')['suggested_status'],'current')
 def test_negated_future_and_other_party(self):
  for n in ['غير متوقع يبدأ الشهر القادم بعلف الوادي','متوقع لا يبدأ بعلف الوادي','متوقع يبدأ جاره الشهر القادم بعلف الوادي','متوقع يبدأ الشهر القادم بعلف المنافس وذكر الوادي']:self.assertNotEqual(e.classify_note(n)['suggested_status'],'potential',n)
 def test_mention_followup_and_closure(self):
  for n in ['متابعة العميل','ذكر علف الوادي','مزرعة متوقفة عن العمل','الشهر القادم إن شاء الله']:self.check(n,'unclassified')
 def test_past_negated_or_competitor(self):
  for n in ['ما كان شغال الوادي','كان شغال المنافس وذكر الوادي','توقف المزرعة بسبب التطهير']:self.assertNotEqual(e.classify_note(n)['suggested_status'],'former',n)
 def test_actual_resumption(self):self.check('كان شغال الوادي من فترة والعميل يعمل بالفعل بعلف الوادي','current')
 def test_salesperson_absence_not_customer_absence(self):self.assertNotEqual(e.classify_note('لم يكن المندوب موجود وسيتم تكرار الزيارة')['suggested_status'],'no_meeting')
 def test_distribution(self):self.check('متابعة كميات العميل وتوزيعه لعلف الوادي على حساب المنتجات الموجودة','current')
 def test_numeric_order_is_not_delivery(self):
  self.check('تم طلب9 طن اليوم','potential')
  self.check('تم طلب 9 طن الوادي اليوم','potential')
 def test_numeric_delivery_and_existing_trade(self):
  self.check('تم توريد9 طن علف الوادي بالفعل','current')
  self.check('شغال الوادي وتم طلب9 طن اليوم','current')
 def test_stock_and_real_refusal_are_not_silently_resolved(self):
  self.check('موجود لديه 6 طن الوادي لكنه غير مهتم بالوادي','unclassified')
 def test_numeric_order_counterparty(self):
  self.check('تم طلب9 طن المنافس اليوم','target')
  self.check('تم طلب9 طن المنافس وتم ذكر الوادي','target')
  self.assertNotEqual(e.classify_note('جاره تم طلب9 طن الوادي له')['suggested_status'],'potential')
  self.assertNotEqual(e.classify_note('تم طلب9 طن الوادي لجاره')['suggested_status'],'potential')
 def test_followup_does_not_copy_or_erase_customer_status(self):
  import pandas as pd
  frame=pd.DataFrame({'Customer Name':['عميل اختبار']*2,'Visit Date':['2026-01-01','2026-01-02'],'Visit Notes':['موجود لديه 6 طن الوادي','متابعة العميل']})
  result=e.classify_dataframe(frame)
  self.assertEqual(result.iloc[1]['Display Status'],'Unclassified')
  self.assertEqual(e.build_customer_journey(result).iloc[0]['Latest Status'],'Current Customer')
  self.assertIn('[2026-01-02] Unclassified',e.build_customer_journey(result).iloc[0]['Status History'])
 def test_conjoined_past_not_current(self):
  self.check('مزرعة شغال فيدميكس وكان شغال الوادي من فترة','former')
 def test_past_with_explicit_agreed_return(self):
  self.check('كان بيوكل الوادي قبل كده تم الاتفاق معه على استخدام الوادي','potential')
 def test_negated_return_agreement_is_not_accepted(self):
  self.assertNotEqual(e.classify_note('كان بيوكل الوادي قبل كده لم يتم الاتفاق معه على استخدام الوادي')['suggested_status'],'potential')
 def test_original_normalization_boundary(self):self.assertIn('20 يوم يتعامل',c.normalize_note('20يوميتعامل'))
if __name__=='__main__':unittest.main()
