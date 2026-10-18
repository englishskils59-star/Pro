from playwright.sync_api import sync_playwright
from pathlib import Path
out=Path(r'D:\All pro\Pro\screenshots\2026-10-18\final-1845')
out.mkdir(parents=True,exist_ok=False)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    page.goto('http://localhost:8501')
    page.get_by_text('12,315 زيارة · 3,700 عميل',exact=True).wait_for(timeout=60000)
    for title,name in [('تصنيف العملاء','03_Key_Feature.png'),('أداء المندوبين','02_Analytics.png'),('لوحة التحكم التنفيذية','01_Overview.png')]:
        page.get_by_text(title,exact=True).first.click()
        page.get_by_role('heading',name=title,exact=True).wait_for(timeout=60000)
        page.wait_for_timeout(9000)
        page.get_by_role('button',name='Stop',exact=True).wait_for(state='hidden',timeout=60000)
        page.evaluate('document.fonts.ready')
        if name=='02_Analytics.png':
            page.mouse.move(1850,800)
            page.mouse.wheel(0,450)
            page.wait_for_timeout(500)
        page.mouse.move(1910,100)
        page.screenshot(path=str(out/name),type='png')
        print(name,flush=True)
    browser.close()

