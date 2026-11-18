import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {constants} from 'node:fs';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const [origin,output,...options]=process.argv.slice(2);
const liveHost=options.includes('--live-host');
if(options.some(value=>value!=='--live-host'))throw Error('Unknown browser-check option');
if(!origin||!output)throw Error('Usage: node tests/browser-check.mjs <local-url> <evidence-directory>');
fs.mkdirSync(output,{recursive:true});
function browserPath(){if(process.env.BROWSER_EXECUTABLE)return process.env.BROWSER_EXECUTABLE;for(const name of ['google-chrome','chromium','chromium-browser'])for(const folder of (process.env.PATH||'').split(path.delimiter)){const file=path.join(folder,name);try{fs.accessSync(file,constants.X_OK);return file}catch{}}throw Error('No existing Chrome/Chromium found')}
const browser=await chromium.launch({executablePath:browserPath(),headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1536,height:1120},reducedMotion:'reduce',acceptDownloads:true,...(process.env.BROWSER_TIMEZONE?{timezoneId:process.env.BROWSER_TIMEZONE}:{})});
const errors=[],checks=[],http=[];
page.on('pageerror',error=>errors.push(error.message));
page.on('response',response=>{const url=new URL(response.url());if(url.pathname.startsWith('/api/'))http.push({method:response.request().method,path:url.pathname+url.search,status:response.status(),...(response.request().method()==='POST'?{source:response.request().postDataJSON()?.mode}:{} )})});
const check=(condition,message)=>{assert.ok(condition,message);checks.push(message)};
async function jobFinished(){await page.waitForFunction(()=>document.querySelector('#job-source').textContent.includes('COMPLETED'),null,{timeout:60000})}
async function nav(name){await page.locator(`[data-view=${name}]`).click()}
async function count(){return Number((await page.locator('#chart-range').textContent()).match(/(\d+) SAMPLES/)[1])}
async function settled(){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))}
let liveSummary=null;
try{
 const response=await page.goto(origin);check(response.status()===200,'Dashboard serves over real HTTP');
 await page.locator('#profile-cards .profile-card').first().waitFor();
 if(await page.locator('#source').inputValue()!=='live')await page.locator('#source').selectOption('live');
 check(!http.some(item=>item.path.includes('/api/snapshot')),'Initial load does not inspect host telemetry');
 check(await page.locator('#cpu-value').textContent()==='—%','Unknown CPU is shown as unknown');
 if(liveHost){
 await page.locator('#monitor').click();
 await page.waitForFunction(()=>!document.querySelector('#cpu-value').textContent.includes('—'),null,{timeout:10000});
 check((await page.locator('#host-name').textContent())!=='This Linux host','Monitoring reads real host identity');
 check((await count())>=2,'Live CPU receives interval samples through HTTP');
 await nav('processes');
 check((await page.locator('#process-rows tr').count())>1,'Actual process table is populated');
 await nav('overview');await page.locator('#monitor').click();
 const paused=await count();
 // This delay verifies an absence over a complete polling period, not rendering.
 await page.waitForTimeout(3300);
 check(await count()===paused,'Pause prevents further scheduled samples');
 await page.locator('#monitor').click();
 await page.waitForFunction(before=>Number(document.querySelector('#chart-range').textContent.match(/(\d+) SAMPLES/)[1])>before,paused);
 await page.locator('#monitor').click();
 checks.push('Resume collects a new live sample');
 await page.locator('#profile-cards [data-profile=baseline]').click();
 await jobFinished();
 const live=await page.evaluate(()=>fetch('/api/job').then(r=>r.json()));
 check(live.source==='live'&&live.results.length===5,'Quick baseline executes five fixed live checks');
 liveSummary={source:live.source,status:live.status,checks:live.results.map(r=>({id:r.id,status:r.status,returncode:r.returncode,assessment:r.assessment,truncated:r.truncated}))};
 await page.locator('.check-result summary').first().click();
 check((await page.locator('.check-output').first().textContent()).length>0,'Live command evidence expands in the actual interface');
 }
 await page.locator('#source').selectOption('demo');
 await nav('overview');
 await page.waitForFunction(()=>document.querySelector('#host-name').textContent==='demo-workstation');
 check(await page.locator('#demo-banner').isVisible(),'Synthetic mode is visibly labeled');
 await page.waitForFunction(()=>document.querySelector('#findings').textContent.includes('capacity'));
 check((await page.locator('#disk-value').textContent()).includes('87'),'Synthetic capacity finding is driven by fixture data');
 if(!liveHost){
  await page.locator('#monitor').click();
  const paused=await count();
  await page.waitForTimeout(3300);
  check(await count()===paused,'Pause prevents scheduled fixture samples');
  await page.locator('#monitor').click();
  await page.waitForFunction(before=>Number(document.querySelector('#chart-range').textContent.match(/(\d+) SAMPLES/)[1])>before,paused);
  checks.push('Resume collects a new fixture sample over HTTP');
  await nav('processes');check((await page.locator('#process-rows tr').count())===4,'Fixture process table is populated');await nav('overview');
 }

 await page.locator('#profile-cards [data-profile=baseline]').click();
 await page.waitForFunction(()=>document.querySelector('#job-source').textContent.includes('RUNNING'));
 check(await page.locator('#source').isDisabled(),'Source cannot switch during a running diagnostic');
 await jobFinished();
 const demo=await page.evaluate(()=>fetch('/api/job').then(r=>r.json()));
 check(demo.source==='demo'&&demo.results[0].assessment==='review','Demo check produces an inspectable review finding');
 await page.locator('.check-result summary').first().click();
 check((await page.locator('.check-output').first().textContent())===demo.results[0].output,'Rendered tool output equals actual backend result');
 await settled();await page.screenshot({path:path.join(output,'diagnostics-desktop.png'),fullPage:true});
 const downloadEvent=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadEvent;await download.saveAs(path.join(output,'demo-report.json'));
 const exported=JSON.parse(fs.readFileSync(path.join(output,'demo-report.json'),'utf8'));
 check(exported.source==='demo'&&exported.latest_diagnostic.id===demo.id,'Downloaded JSON identifies source and exact displayed job');
 check(exported.latest_diagnostic.results[0].output===demo.results[0].output,'Export preserves exact synthetic command evidence');
 await page.locator('#profile-list [data-profile=startup]').click();
 await page.locator('#cancel').click();
 await page.waitForFunction(()=>document.querySelector('#job-source').textContent.includes('CANCELLED'));
 const cancelled=await page.evaluate(()=>fetch('/api/job').then(r=>r.json()));
 check(cancelled.results.length<cancelled.planned.length,'Cancelling a diagnostic leaves later checks unrun');
 await page.locator('#profile-list [data-profile=storage]').click();await jobFinished();
 check((await page.locator('#check-results').textContent()).includes('Limited'),'Missing sensors appear as limited coverage');
 await nav('evidence');
 check((await page.locator('#coverage').textContent()).includes('Unverified'),'Coverage explicitly reports unverified hardware areas');
 await nav('overview');
 await page.waitForFunction(()=>Number(document.querySelector('#chart-range').textContent.match(/(\d+) SAMPLES/)[1])>=4,null,{timeout:15000});
 await page.locator('#toast').evaluate(node=>node.classList.remove('visible'));
 await settled();await page.screenshot({path:path.join(output,'overview-desktop.png'),fullPage:true});
 await page.locator('#monitor').click();
 await page.locator('#walkthrough').click();check(await page.locator('#tour-dialog').isVisible(),'Guided tour opens through the real control');
 await page.keyboard.press('Escape');check(!(await page.locator('#tour-dialog').isVisible()),'Tour supports keyboard dismissal');
 await nav('processes');
 // Deliberately hostile process text is supplied as a fixture to test text rendering.
 await page.route('**/api/snapshot?mode=demo',async route=>{const response=await route.fetch();const data=await response.json();data.processes[0].name='<img src=x onerror=alert(1)>';await route.fulfill({json:data})});
 await page.locator('#monitor').click();
 await page.waitForFunction(()=>document.querySelector('#process-rows').textContent.includes('<img'));
 check(await page.locator('#process-rows img').count()===0,'Untrusted process names render as text, without HTML execution');
 await page.locator('#monitor').click();await page.unroute('**/api/snapshot?mode=demo');
 for(const width of [360,768]){await page.setViewportSize({width,height:900});for(const section of ['overview','diagnostics','processes','evidence']){await nav(section);await settled();check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${section} remains contained at ${width}px`)}if(width===360){await nav('overview');await settled();await page.screenshot({path:path.join(output,'overview-mobile.png'),fullPage:true});await nav('diagnostics');await settled();await page.screenshot({path:path.join(output,'diagnostics-mobile.png'),fullPage:true})}}
 await page.setViewportSize({width:1536,height:1120});await page.reload();
 await page.locator('#profile-cards .profile-card').first().waitFor();
 check(await count()===0,'Reload clears in-memory chart samples');
 await nav('diagnostics');
 check((await page.locator('#job-title').textContent())==='Storage & thermals','Reload restores the latest backend job with correct source');
 check(await page.locator('#demo-banner').isVisible(),'Restored fixture job keeps its demo label');
 if(!liveHost)check(http.every(item=>!item.path.includes('mode=live')&&item.source!=='live'),'Fixture-only browser run makes no live telemetry or diagnostic request');
 check(errors.length===0,'No browser JavaScript runtime errors');
 check(http.every(item=>item.status<400),'All exercised application HTTP requests succeed');
 fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:true,checks,errors,runtime:{browser:browser.version(),executable:browserPath(),playwright_module:process.env.PLAYWRIGHT_MODULE||'playwright-core',timezone:await page.evaluate(()=>Intl.DateTimeFormat().resolvedOptions().timeZone)},live_summary:liveSummary,http,scope:liveHost?'Actual loopback HTTP, authorized live baseline, and synthetic fixtures.':'Actual loopback HTTP and synthetic fixtures only; live host diagnosis not exercised.'},null,2));
 console.log(JSON.stringify({passed:true,checks},null,2));
}catch(error){fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:false,checks,errors,http,error:String(error)},null,2));await page.screenshot({path:path.join(output,'browser-failure.png'),fullPage:true}).catch(()=>{});throw error}
finally{await browser.close()}
