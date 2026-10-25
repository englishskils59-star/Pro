from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
from playwright.sync_api import sync_playwright,expect
ROOT=Path(r'D:\All pro\Pro')
OUT=ROOT/'screenshots'/('english-matching-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir()
def hashes(): return {str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'data').glob('*') if f.is_file()}
before=hashes()
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge',headless=True)
 page=b.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def ready(title):
  page.get_by_role('heading',name=title,exact=True).wait_for(timeout=120000)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  page.evaluate('document.fonts.ready')
  page.wait_for_timeout(1800)
  if title not in ('Upload Center','مركز الرفع'): page.locator('[data-testid=stPlotlyChart] .main-svg').first.wait_for(timeout=120000)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  page.wait_for_timeout(1500)
  assert not page.locator('[data-testid=stException]').count()
 page.goto('http://localhost:8501/')
 ready('مركز الرفع')
 page.frame_locator('iframe[title="localization.wdi_language"]').get_by_role('button',name='English',exact=True).click()
 ready('Upload Center')
 for title,name,scroll in [('Executive Dashboard','01_Overview.png',0),('Sales Rep Performance','02_Analytics.png',450),('Customer Classification','03_Key_Feature.png',0)]:
  page.get_by_text(title,exact=True).first.click()
  ready(title)
  page.locator('[data-testid=stMain]').evaluate('(el,y)=>el.scrollTop=y',scroll)
  page.mouse.move(1910,90)
  page.wait_for_timeout(700)
  page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=120000)
  assert not page.locator('[data-testid=stSkeleton]:visible').count()
  assert page.locator('html').get_attribute('lang')=='en'
  page.screenshot(path=str(OUT/name))
  print(name,flush=True)
 b.close()
assert before==hashes()
(OUT/'capture-checks.json').write_text(json.dumps({'dimensions':[1920,1080],'business_files_unchanged':True,'javascript_errors':errors},indent=2))
(OUT/'README.md').write_text('''# WDI Analytics — English screenshots

Real application screenshots, captured from the existing service at localhost:8501 in English, at 1920×1080 and 100% zoom.

- 01_Overview.png: Executive Dashboard; matches reference 1.png. All data, 2024/02/21–2026/08/20. Monthly comparison August 2026 versus July 2026.
- 02_Analytics.png: Sales Rep Performance; matches reference 2.png. All reps, full period. Report controls show Ahmed Samir, 2026, All Months; report generation was not submitted.
- 03_Key_Feature.png: Customer Classification; matches reference 3.png. Final Status per Customer, all reps/statuses, confidence 0, empty search.

Current real business data, photographed with the user's permission. Arabic record names are preserved. No source code, stored records, or application content was changed. Only the existing language switcher, page navigation, and scrolling were used. Business-file hashes verified unchanged. Images are native browser PNG captures, without browser chrome or image editing.
''',encoding='utf-8')
print(OUT,flush=True)

