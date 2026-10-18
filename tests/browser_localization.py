"""Read-only browser verification against the existing local Streamlit service."""
from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'screenshots'/('bilingual-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(parents=True,exist_ok=False)
results={}
def hashes():return {str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'data').glob('*') if f.is_file()}
before=hashes()
with sync_playwright() as p:
 browser=p.chromium.launch(channel='msedge',headless=True)
 context=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1)
 page=context.new_page()
 def idle():
  print('Waiting for UI',flush=True)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  page.wait_for_timeout(600)
  assert not page.locator('[data-testid="stException"]').count(),page.locator('body').inner_text()[-3000:]
 def switch(lang,title):
  print('Switch',lang,title,flush=True)
  page.frame_locator('iframe[title="localization.wdi_language"]').get_by_role('button',name='English' if lang=='en' else 'العربية',exact=True).click()
  page.wait_for_timeout(1800)
  print('State',page.locator('h1').all_text_contents(),flush=True)
  if page.locator('[data-testid=stException]').count(): print(page.locator('body').inner_text()[-3000:],flush=True)
  page.get_by_role('heading',name=title,exact=True).wait_for(timeout=60000)
  idle()
  assert page.locator('html').get_attribute('lang')==lang
  if title in ('Customer Classification','تصنيف العملاء'):
   assert page.get_by_role('radio',name='👤 Final Status per Customer' if lang=='en' else '👤 موقف نهائي لكل عميل',exact=True).is_checked()
  assert page.locator('html').get_attribute('dir')==('rtl' if lang=='ar' else 'ltr')
 def nav(title):
  print('Navigate',title,flush=True)
  page.get_by_text(title,exact=True).first.click()
  page.wait_for_timeout(1800)
  print('State',page.locator('h1').all_text_contents(),flush=True)
  if page.locator('[data-testid=stException]').count(): print(page.locator('body').inner_text()[-3000:],flush=True)
  page.get_by_role('heading',name=title,exact=True).wait_for(timeout=60000)
  idle()
 def capture(name):
  page.locator('[data-testid="stMain"]').evaluate('(el)=>el.scrollTop=0')
  page.mouse.move(1910,90)
  page.screenshot(path=str(OUT/name))
 page.goto('http://localhost:8501')
 page.wait_for_timeout(3000)
 print(page.locator('body').inner_text()[:1000],flush=True)
 page.get_by_role('heading',name='مركز الرفع',exact=True).wait_for(timeout=120000)
 idle()
 results['first_visit_arabic']=page.locator('html').get_attribute('lang')=='ar'
 nav('تصنيف العملاء')
 search=page.get_by_role('textbox',name='بحث باسم العميل…',exact=True)
 search.fill('ناصر');search.press('Tab');idle()
 page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('الحالة',exact=True)).get_by_role('combobox').click()
 page.get_by_role('option',name='غير مهتم',exact=True).click();idle();print('Filters set',flush=True)
 switch('en','Customer Classification')
 assert page.get_by_role('textbox',name='Search customer name…',exact=True).input_value()=='ناصر'
 assert 'Not Interested' in page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Status',exact=True)).first.inner_text()
 print('Page, search and filter preserved',flush=True)
 results['current_page_search_and_status_preserved']=True
 switch('ar','تصنيف العملاء')
 assert page.get_by_role('textbox',name='بحث باسم العميل…',exact=True).input_value()=='ناصر'
 # Do not submit or save the rule: verify browser-side unsaved form state.
 page.get_by_role('tab',name='⚙️ قواعد الكلمات',exact=True).click()
 page.get_by_text('➕ إضافة / إدارة القواعد المخصصة',exact=False).first.click()
 page.get_by_role('textbox',name='الكلمة / العبارة المفتاحية',exact=True).fill('اختبار غير محفوظ')
 switch('en','Customer Classification')
 page.get_by_role('tab',name='⚙️ Keyword Rules',exact=True).click()
 field=page.get_by_role('textbox',name='Keyword / Phrase',exact=True)
 if not field.is_visible():page.get_by_text('➕ Add / Manage Custom Rules',exact=False).first.click()
 print('Unsaved field:',repr(field.input_value()),flush=True)
 assert field.input_value()=='اختبار غير محفوظ','Unsaved form field was reset'
 results['unsaved_form_preserved']=True
 # Reset display-only filters for the showcase images.
 page.get_by_role('tab',name='📋 Classification Results',exact=True).click()
 field=page.get_by_role('textbox',name='Search customer name…',exact=True)
 field.fill('');field.press('Tab');idle()
 page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Status',exact=True)).first.get_by_role('combobox').click()
 page.get_by_role('option',name='All',exact=True).click();idle()
 for ar,en,filename in [('تصنيف العملاء','Customer Classification','03_Key_Feature'),('أداء المندوبين','Sales Rep Performance','02_Analytics'),('لوحة التحكم التنفيذية','Executive Dashboard','01_Overview')]:
  nav(en);capture(filename+'_en.png')
  switch('ar',ar);capture(filename+'_ar.png')
  switch('en',en)
 results['same_three_screens_both_languages']=True
 page.reload()
 page.get_by_role('heading',name='Upload Center',exact=True).wait_for(timeout=120000)
 idle()
 assert page.locator('html').get_attribute('lang')=='en'
 results['preference_survives_refresh']=True
 page.set_viewport_size({'width':390,'height':844});idle()
 results['english_mobile_ltr']=page.locator('html').get_attribute('dir')=='ltr'
 page.screenshot(path=str(OUT/'mobile_en.png'))
 browser.close()
results['business_files_unchanged']=before==hashes()
assert results['business_files_unchanged']
(OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(OUT,results,flush=True)
