// Regenerate illustrative assets only. Never substitute these for raw QA evidence.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
const [origin,output]=process.argv.slice(2);
if(!origin||!output)throw Error('Usage: PLAYWRIGHT_MODULE=<module> node scripts/capture_examples.mjs <isolated-local-origin> <new-output-directory>');
const target=new URL(origin);
if(target.protocol!=='http:'||!['127.0.0.1','localhost'].includes(target.hostname)||target.username||target.password)throw Error('Only a dedicated loopback preview is supported');
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright-core');
function browserPath(){if(process.env.BROWSER_EXECUTABLE)return process.env.BROWSER_EXECUTABLE;for(const name of ['google-chrome','chromium','chromium-browser'])for(const folder of (process.env.PATH||'').split(path.delimiter)){const file=path.join(folder,name);try{fs.accessSync(file,fs.constants.X_OK);return file}catch{}}throw Error('Existing browser required')}
if(fs.existsSync(output))throw Error('Output already exists');
fs.mkdirSync(output,{recursive:true});
const base=Date.parse('2020-01-01T12:00:00Z'); // Deliberately synthetic example clock.
function normalize(value){
 if(Array.isArray(value))return value.map(normalize);
 if(!value||typeof value!=='object')return value;
 const result={};for(const [key,part]of Object.entries(value)){
  if(['started_at','finished_at','exported_at','collected_at'].includes(key)&&part!==null)result[key]=new Date(base+(key==='collected_at'?(value.sequence||0)*3000:key==='finished_at'?2000:0)).toISOString();
  else if(key==='id'&&Array.isArray(value.planned))result[key]='synthetic-example-job';
  else result[key]=normalize(part);
 }return result;
}
const browser=await chromium.launch({executablePath:browserPath(),headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1536,height:1120},reducedMotion:'reduce',timezoneId:'UTC',acceptDownloads:true});
const errors=[],http=[];
page.on('pageerror',e=>errors.push(e.message));
try{
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url());
  const body=request.method()==='POST'?request.postDataJSON():null;
  if(url.searchParams.get('mode')==='live'||body?.mode==='live')throw Error('Example capture must not inspect a live host');
  const response=await route.fetch();
  const data=await response.json();
  if(data?.source&&data.source!=='demo')throw Error('Use an isolated server without a live job');
  http.push({method:request.method(),route:url.pathname+url.search,status:response.status()});
  await route.fulfill({response,json:normalize(data)});
 });
 assert.equal((await page.goto(origin)).status(),200);
 await page.locator('#profile-cards .profile-card').first().waitFor();
 await page.locator('#source').selectOption('demo');
 await page.waitForFunction(()=>document.querySelector('#host-name').textContent==='demo-workstation');
 await page.locator('#profile-cards [data-profile=baseline]').click();
 await page.waitForFunction(()=>document.querySelector('#job-source').textContent.includes('COMPLETED'));
 await page.locator('.check-result summary').first().click();
 await page.locator('#toast').evaluate(node=>node.classList.remove('visible'));
 await page.screenshot({path:path.join(output,'diagnostics-desktop.png'),fullPage:true});
 const downloading=page.waitForEvent('download');await page.locator('#export').click();const download=await downloading;
 const raw=path.join(output,'temporary-demo-download.json');await download.saveAs(raw);
 const report=normalize(JSON.parse(fs.readFileSync(raw,'utf8')));fs.unlinkSync(raw);
 assert.equal(report.source,'demo');
 fs.writeFileSync(path.join(output,'demo-report.json'),JSON.stringify(report,null,2)+'\n');
 await page.locator('[data-view=overview]').click();
 await page.waitForFunction(()=>Number(document.querySelector('#chart-range').textContent.match(/(\d+) SAMPLES/)[1])>=4,null,{timeout:20000});
 await page.locator('#monitor').click();await page.locator('#toast').evaluate(node=>node.classList.remove('visible'));
 await page.screenshot({path:path.join(output,'overview-desktop.png'),fullPage:true});
 await page.setViewportSize({width:360,height:900});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:path.join(output,'overview-mobile.png'),fullPage:true});
 await page.locator('[data-view=diagnostics]').click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:path.join(output,'diagnostics-mobile.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(output,'http-example.json'),JSON.stringify({kind:'curated synthetic HTTP route example',timestamps:'Normalized to a fictional UTC clock; no production host data',http},null,2)+'\n');
 console.log('Synthetic examples captured; timestamp/job-ID normalization applied. This is illustrative material, not current host evidence.');
}finally{await browser.close()}
