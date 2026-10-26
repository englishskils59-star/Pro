const fs=require('fs');
const {chromium}=require('C:/Users/eslam.abdelhay/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});const p=await b.newPage({viewport:{width:1920,height:1080}});p.setDefaultTimeout(45000);console.log('browser ready');
await p.goto('http://127.0.0.1:8501/',{waitUntil:'domcontentloaded'});console.log('page opened');
for(let pass=0;pass<2;pass++){
 await p.getByText('تصنيف العملاء',{exact:true}).first().waitFor({timeout:90000});await p.getByText('تصنيف العملاء',{exact:true}).first().click();
 await p.getByText('📋 كل الزيارات',{exact:true}).first().waitFor({timeout:90000});await p.getByText('📋 كل الزيارات',{exact:true}).first().click();
 await p.getByRole('button',{name:'Stop',exact:true}).waitFor({state:'hidden',timeout:90000});
 console.log('classification loaded',pass);fs.writeFileSync(__dirname+'/browser_debug.txt',await p.locator('body').innerText());
 let text=await p.locator('body').innerText();console.log(text.slice(0,1700));
 if(!text.includes('13,503')||!/تم تصنيفهم\s+13,503/.test(text)||!/غير مصنف\s+0/.test(text))throw Error('Incorrect totals');
 if(await p.locator('[data-testid="stException"]').count())throw Error('Application exception');
 fs.writeFileSync(__dirname+'/browser_'+pass+'.txt',text);await p.screenshot({path:__dirname+'/classification_'+pass+'.png'});
 if(pass===0)await p.reload({waitUntil:'domcontentloaded'});
}
await p.getByText('لوحة التحكم التنفيذية',{exact:true}).first().click();await p.getByText('EXECUTIVE DASHBOARD',{exact:true}).waitFor({timeout:90000});await p.locator('[data-testid="stPlotlyChart"] .js-plotly-plot svg.main-svg').first().waitFor({timeout:90000});await p.getByRole('button',{name:'Stop',exact:true}).waitFor({state:'hidden',timeout:90000});
if(await p.locator('[data-testid="stException"]').count())throw Error('Dashboard exception');
await p.screenshot({path:__dirname+'/dashboard.png'});fs.writeFileSync(__dirname+'/dashboard.txt',await p.locator('body').innerText());
fs.writeFileSync(__dirname+'/browser_verified.json',JSON.stringify({visits:13503,classified:13503,unclassified:0,reloadVerified:true,dashboardChartsLoaded:true},null,2));console.log('Browser verified: 13,503 visits, 13,503 classified, zero unclassified, refresh and dashboard verified');await b.close();})().catch(e=>{console.error(e);process.exit(1)});
