"""Capture key screens from the existing local service, without changing records."""
from pathlib import Path
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright,expect
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'screenshots'/('bilingual-final-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(exist_ok=False)
def hashes():return {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'data').glob('*') if f.is_file()}
before=hashes()
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 context=b.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1)
 page=context.new_page()
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def ready(title,lang):
  page.get_by_role('heading',name=title,exact=True).wait_for(timeout=120000)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  button=page.frame_locator('iframe[title="localization.wdi_language"]').get_by_role('button',name='العربية' if lang=='ar' else 'English',exact=True)
  button.wait_for(state='visible')
  expect(button).to_have_attribute('aria-pressed','true')
  assert page.locator('html').get_attribute('lang')==lang
  assert not page.locator('[data-testid=stException]').count()
  page.evaluate('document.fonts.ready')
  page.wait_for_timeout(1500)
  if title not in ('مركز الرفع','Upload Center'):
   page.locator('[data-testid=stPlotlyChart] .main-svg').first.wait_for(state='visible',timeout=120000)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  page.wait_for_timeout(1500)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
 def capture(name):
  page.locator('[data-testid=stMain]').evaluate('(el)=>el.scrollTop=0')
  if name.startswith('02_'):
   page.locator('[data-testid=stMain]').evaluate('(el)=>el.scrollTop=450')
  page.mouse.move(1910,90)
  page.wait_for_timeout(500)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  assert not page.locator('[data-testid=stSkeleton]:visible').count(),'Visible loading placeholder'
  page.screenshot(path=str(OUT/name))
  print(name,page.locator('iframe[title="localization.wdi_language"]').bounding_box(),flush=True)
 page.goto('http://localhost:8501');ready('مركز الرفع','ar')
 screens=[('تصنيف العملاء','Customer Classification','03_Key_Feature'),('أداء المندوبين','Sales Rep Performance','02_Analytics'),('لوحة التحكم التنفيذية','Executive Dashboard','01_Overview')]
 if '--reps-only' in sys.argv:screens=screens[1:2]
 for ar,en,name in screens:
  page.get_by_text(ar,exact=True).first.click();ready(ar,'ar');capture(name+'_ar.png')
  page.frame_locator('iframe[title="localization.wdi_language"]').get_by_role('button',name='English',exact=True).click();ready(en,'en')
  capture(name+'_en.png')
  page.frame_locator('iframe[title="localization.wdi_language"]').get_by_role('button',name='العربية',exact=True).click();ready(ar,'ar')
 print('JS errors:',errors,flush=True)
 assert not errors
 page.frame_locator('iframe[title="localization.wdi_language"]').get_by_role('button',name='English',exact=True).click();ready(en,'en')
 page.reload();ready('Upload Center','en')
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(700)
 page.screenshot(path=str(OUT/'mobile_en.png'))
 b.close()
assert before==hashes(),'Business files changed'
(OUT/'capture-checks.json').write_text(json.dumps({'png_dimensions':[1920,1080],'business_files_unchanged':True,'javascript_errors':errors,'language_refresh_persistence':True},indent=2),encoding='utf-8')
print(OUT,flush=True)
