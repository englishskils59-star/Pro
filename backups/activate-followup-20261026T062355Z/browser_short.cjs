const fs=require('fs');const {chromium}=require('C:/Users/eslam.abdelhay/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});const p=await b.newPage({viewport:{width:1920,height:1080}});p.setDefaultTimeout(180000);
await p.route("https://fonts.googleapis.com/**",route=>route.abort());await p.route("https://fonts.gstatic.com/**",route=>route.abort());
try{
console.log('launch');await p.goto('http://localhost:8501/');console.log('goto');
for(let n=0;n<2;n++){
await p.getByText('تصنيف العملاء',{exact:true}).first().click();console.log('classification clicked',n);
await p.getByText('تم تصنيفهم',{exact:true}).waitFor();console.log('metrics visible',n);
await p.waitForTimeout(2500);let t=await p.locator('body').innerText();fs.writeFileSync(__dirname+'/reload_'+n+'.txt',t);console.log(t.slice(800,1500));
if(!/تم تصنيفهم\s+13,503/.test(t)||!/غير مصنف\s+0/.test(t))throw Error('Wrong metrics');await p.screenshot({path:__dirname+'/reload_'+n+'.png'});console.log('screenshot',n);
if(n===0){await p.reload();console.log('reload');}}
await p.getByText('لوحة التحكم التنفيذية',{exact:true}).first().click();console.log('dashboard clicked');await p.getByText('EXECUTIVE DASHBOARD',{exact:true}).waitFor();await p.locator('[data-testid="stPlotlyChart"] .js-plotly-plot svg.main-svg').first().waitFor();await p.waitForTimeout(1000);
if(await p.locator('[data-testid="stException"]').count())throw Error('App exception');await p.screenshot({path:__dirname+'/dashboard.png'});fs.writeFileSync(__dirname+'/browser_verified.json',JSON.stringify({visits:13503,classified:13503,unclassified:0,reloadVerified:true,dashboardChartsLoaded:true}));console.log('BROWSER_OK');
}catch(e){fs.writeFileSync(__dirname+'/debug_error.txt',await p.locator('body').innerText());console.error(e);throw e}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
