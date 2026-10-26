"""Generalized return intent: no development IDs or exact note answer lookup."""
import unittest
import classification_engine as e

class ReturnIntentTests(unittest.TestCase):
 def check(self,text,status):self.assertEqual(e.classify_note(text)['suggested_status'],status)
 def test_stopped_trade_postposed(self):
  self.check('تاجر شغال الوادي كان شغال وتوقف إن شاء الله نرجع نشتغل تاني','former')
 def test_stopped_with_descriptive_prefix(self):
  self.check('تاجر شغال علف الوادي كان شغال وتوقف نرجع نشتغل','former')
 def test_wish_alone_not_customer_acceptance(self):
  self.check('إن شاء الله نرجع نشتغل تاني','target')
 def test_former_wish_not_agreement(self):
  self.check('عميل سابق للوادي توقف إن شاء الله نرجع نشتغل','former')
 def test_former_explicit_acceptance(self):
  self.check('عميل سابق للوادي توقف ووافق على العودة للعمل ولم يبدأ التنفيذ','potential')
 def test_former_agreed_return(self):
  self.check('عميل سابق للوادي توقف واتفقنا معه على العودة للعمل','potential')
 def test_negotiated_return_preserved(self):
  self.check('عميل سابق للوادي توقف تم التفاوض على التساهل في التسديد للعودة','potential')
 def test_current_not_erased_by_wish(self):
  self.check('العميل يعمل بعلف الوادي إن شاء الله نرجع نشتغل مع موزع آخر','current')
 def test_no_wadi_reference_does_not_prove_former(self):
  self.assertNotEqual(e.classify_note('تاجر شغال المنافس كان شغال وتوقف نرجع نشتغل')['suggested_status'],'former')
 def test_rejection_not_acceptance(self):
  self.assertNotEqual(e.classify_note('عميل سابق للوادي توقف ولم يوافق على العودة للعمل')['suggested_status'],'potential')
 def test_later_actual_resumption_not_erased(self):
  self.check('شغال الوادي كان شغال وتوقف والان العميل يعمل بعلف الوادي بالفعل','current')
 def test_later_future_resumption_not_actual(self):
  self.check('شغال الوادي كان شغال وتوقف ووافق على العودة للعمل غدا','potential')
 def test_conditional_discount_return_is_negotiation(self):
  self.check('كان شغال الوادي وتوقف إن شاء الله نرجع نشتغل بس ظبط لي الخصم','potential')
 def test_salesperson_discount_offer_not_acceptance(self):
  self.check('عميل سابق للوادي توقف ونرجع نشتغل والمندوب عرض تعديل الخصم','former')
 def test_negated_conditional_not_customer_readiness(self):
  self.assertNotEqual(e.classify_note('عميل سابق للوادي توقف لم يقل بس ظبط لي الخصم')['suggested_status'],'potential')
 def test_supplier_acceptance_not_customer_acceptance(self):
  self.check('عميل سابق للوادي توقف ووافق الموزع على العودة للعمل ونرجع نشتغل','former')
 def test_customer_acceptance_after_supplier_mention(self):
  self.check('عميل سابق للوادي توقف واتفقنا مع المورد ثم العميل وافق على العودة للعمل','potential')
 def test_planned_supply_to_returning_trader_preserved(self):
  self.check('عميل سابق للوادي تم التفاوض مع التاجر على تجربة المنتج وسيتم نزول المنتج خلال الاسبوع القادم','potential')
 def test_future_start_not_first_actual_trade(self):
  self.check('اتفقنا معه على العودة للعمل بعلف الوادي ولم يبدأ التنفيذ','potential')

if __name__=='__main__':unittest.main()
