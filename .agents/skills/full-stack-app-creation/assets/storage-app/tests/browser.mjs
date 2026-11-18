import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
import {bytes,percent} from '../web/core.mjs';

const [origin,output]=process.argv.slice(2);
if(!origin||!output)throw Error('Usage: node tests/browser.mjs <origin> <evidence-directory>');
fs.mkdirSync(output,{recursive:true});
function executable(){
  if(process.env.BROWSER_EXECUTABLE)return process.env.BROWSER_EXECUTABLE;
  for(const name of ['google-chrome','chromium','chromium-browser'])for(const folder of (process.env.PATH||'').split(path.delimiter)){
    const candidate=path.join(folder,name);try{fs.accessSync(candidate,fs.constants.X_OK);return candidate}catch{}
  }
  throw Error('Existing Chrome/Chromium required; set BROWSER_EXECUTABLE.');
}
const browser=await chromium.launch({executablePath:executable(),headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:1120},reducedMotion:'reduce',timezoneId:'America/New_York',acceptDownloads:true});
const page=await context.newPage();
const results={started_at:new Date().toISOString(),browser_version:browser.version(),executable:executable(),checks:[],scenarios:{},http:[],accessibility:[],errors:[],screenshots:[]};
let lastSnapshot, requests=0;
page.on('pageerror',error=>results.errors.push(error.message));
page.on('request',request=>{if(new URL(request.url()).pathname==='/api/snapshot')requests++});
page.on('response',async response=>{const url=new URL(response.url());if(url.pathname.startsWith('/api/'))results.http.push({method:response.request().method(),path:url.pathname+url.search,status:response.status()});if(url.pathname==='/api/snapshot'&&response.ok())try{lastSnapshot=await response.json()}catch{}});
function check(value,message){assert.ok(value,message);results.checks.push(message)}
async function scenario(id,fn){await fn();results.scenarios[id]=true;console.log(`${id}: PASS`)}
const nav=async view=>{await page.locator(`[data-view="${view}"]`).click();await page.locator(`#${view==='overview'?'summary':view}-section`).waitFor({state:'visible'})};
const settle=async()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
async function screenshot(name){await page.locator('#toast').waitFor({state:'hidden'});const modal=await page.locator('#drive-dialog').isVisible();if(!modal)await page.evaluate(()=>window.scrollTo(0,0));await settle();await page.screenshot({path:path.join(output,name),fullPage:!modal});results.screenshots.push(name)}
async function accessibility(label){
  const analysis=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  const violations=analysis.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,failure:n.failureSummary}))}));
  results.accessibility.push({label,violations,passes:analysis.passes.length,incomplete:analysis.incomplete.length});
  check(!violations.length,`${label}: no automated WCAG A/AA violations`);
}
async function refresh(){await page.locator('#refresh').click();await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);await settle()}
async function mockSnapshot(snapshot){await page.route('**/api/snapshot?source=demo',route=>route.fulfill({json:snapshot}));await refresh()}
try{
  await scenario('A01',async()=>{
    const response=await page.goto(origin);check(response.status()===200,'Live dashboard serves over HTTP');
    await page.locator('#dashboard').waitFor({state:'visible'});
    check(lastSnapshot.source==='live'&&lastSnapshot.drives.length>0,'Live HTTP inventory contains physical devices');
    check(await page.locator('#drive-cards .drive-card').count()===lastSnapshot.drives.length,'Rendered drive count matches live collector');
    results.live_summary={source:lastSnapshot.source,totals:lastSnapshot.totals,drive_count:lastSnapshot.drives.length,volume_count:lastSnapshot.volumes.length,health_coverage:lastSnapshot.coverage};
  });
  await scenario('A08',async()=>{
    const t=lastSnapshot.totals;
    check((await page.locator('#summary-section .metric strong').allTextContents()).slice(0,3).join('|')===[bytes(t.physical),bytes(t.used),bytes(t.available)].join('|'),'Overview capacity cards equal live API byte values');
    check(await page.locator('#used-percentage').textContent()===percent(t.percent),'Donut center uses actual usable-space denominator');
    check(t.total===t.used+t.available+t.reserved,'Mounted allocation balances used, available and reserved');
    await screenshot('live-overview-desktop.png');
  });
  await scenario('A04',async()=>{
    await nav('health');
    check(await page.locator('#health-cards .health-card').count()===lastSnapshot.drives.length,'Live health view includes every physical drive');
    const cards=await page.locator('#health-cards').textContent();
    for(const drive of lastSnapshot.drives)check(cards.includes(drive.health.reason),`${drive.name}: rendered health reason matches actual collector response`);
    const commands=lastSnapshot.evidence.filter(item=>item.argv?.[0]?.endsWith('/smartctl'));
    results.live_smart={attempted:commands.length,coverage:lastSnapshot.coverage.hardware_health,health:lastSnapshot.drives.map(d=>({path:d.path,...d.health}))};
    check(commands.length===lastSnapshot.drives.length||lastSnapshot.evidence.some(item=>item.tool==='smartctl'&&item.status==='missing'),'SMART attempts or missing-tool evidence account for all live drives');
    await screenshot('live-health-desktop.png');await nav('overview');
  });
  await scenario('A12',async()=>{
    await page.locator('#auto-update').click();
    check(await page.locator('#auto-update').getAttribute('aria-pressed')==='false','Pause toggles update state');
    const before=requests;
    // Deliberate absence check over an entire ten-second polling period.
    await page.waitForTimeout(10800);
    check(requests===before,'Paused dashboard sends no scheduled snapshot requests');
    const updated=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/history');
    await page.locator('#auto-update').click();await updated;await settle();
    check(requests>before,'Resume collects another live sample');
    check(lastSnapshot.drives.some(d=>d.io!==null),'Repeated live sampling returns actual interval I/O');
    await page.locator('#auto-update').click();
    const manual=requests;await refresh();check(requests===manual+1,'Manual refresh issues a single snapshot request');
    const calls=requests;
    await page.route('**/api/snapshot?source=live',async route=>{await new Promise(resolve=>setTimeout(resolve,500));await route.continue()});
    const promise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/history');
    await page.locator('#refresh').click();
    check(await page.locator('#refresh').isDisabled(),'In-flight refresh disables repeat requests');
    await promise;await page.unroute('**/api/snapshot?source=live');
    await page.waitForFunction(()=>!document.querySelector('#refresh').disabled);
    check(requests===calls+1,'Delayed refresh has no overlapping duplicate request');
  });
  await scenario('A13',async()=>{
    const liveHistory=await (await page.request.get(origin+'/api/history?source=live')).json();
    await page.locator('#units').selectOption('decimal');await page.reload();await page.locator('#dashboard').waitFor({state:'visible'});
    check(await page.locator('#units').inputValue()==='decimal','Unit preference survives reload');
    check(await page.locator('#auto-update').getAttribute('aria-pressed')==='false','Pause preference survives reload');
    await page.locator('#source').selectOption('demo');await page.locator('#demo-notice').waitFor({state:'visible'});await page.locator('#dashboard').waitFor({state:'visible'});
    check((await page.locator('#host-name').textContent())==='atlas-demo','Demo source is visibly separate');
    await page.reload();await page.locator('#dashboard').waitFor({state:'visible'});
    check(await page.locator('#source').inputValue()==='demo','Source preference survives reload');
    const after=await (await page.request.get(origin+'/api/history?source=live')).json();
    check(after.samples.length===liveHistory.samples.length,'Demo viewing does not write live history');
    await page.locator('#units').selectOption('binary');
  });
  await scenario('A09',async()=>{
    for(const view of ['drives','volumes','activity','health','overview']){
      await nav(view);check(await page.locator(`[data-view="${view}"]`).getAttribute('aria-current')==='page',`${view} navigation exposes selected view`);
    }
    await nav('activity');check(await page.locator('#activity-chart svg').count()===1,'Activity view plots returned demo history');
    await page.locator('#history-range').selectOption('180');check((await page.locator('#activity-metrics').textContent()).includes('60'),'History window uses available recorded samples');
    await screenshot('demo-activity-desktop.png');await nav('overview');
    await nav('health');await page.locator('.brand').click();
    check(await page.locator('[data-view="overview"]').getAttribute('aria-current')==='page','Atlas brand returns to the overview');
  });
  await scenario('A10',async()=>{
    const opener=page.locator('[data-drive="/dev/nvme0n1"]');await opener.focus();await page.keyboard.press('Enter');
    await page.locator('#drive-dialog').waitFor({state:'visible'});
    check((await page.locator('#dialog-content').textContent()).includes('nvme0n1p2'),'Drive dialog shows actual child partitions');
    check((await page.locator('#dialog-content').textContent()).includes('SMART passed'),'Drive dialog exposes health source');
    await screenshot('drive-details-desktop.png');
    for(let i=0;i<7;i++)await page.keyboard.press('Tab');
    check(await page.evaluate(()=>document.querySelector('#drive-dialog').contains(document.activeElement)),'Dialog traps keyboard focus');
    await page.keyboard.press('Escape');check(!await page.locator('#drive-dialog').isVisible(),'Escape closes native dialog');
    check(await opener.evaluate(node=>node===document.activeElement),'Dialog restores focus to selected drive');
  });
  await scenario('A11',async()=>{
    await nav('volumes');await page.locator('#volume-search').fill('ARCHIVE');
    check(await page.locator('#volume-rows tr').count()===1&&(await page.locator('#volume-rows').textContent()).includes('Archive'),'Search finds volume labels case insensitively');
    await page.locator('#volume-search').fill('/mnt/archive');check(await page.locator('#volume-rows tr').count()===1,'Search accepts a mount path');
    await page.locator('#volume-search').fill('missing-volume');check((await page.locator('#volume-rows').textContent()).includes('No volumes match'),'Search displays a meaningful empty state');
    await page.locator('#volume-search').fill('');await page.locator('#volume-filter').selectOption('attention');
    check(await page.locator('#volume-rows tr').count()===1,'Attention filter returns only warning or critical volumes');
    await page.locator('#volume-filter').selectOption('normal');check(await page.locator('#volume-rows tr').count()===2,'Normal filter excludes warnings');
    await page.locator('#volume-filter').selectOption('all');await page.locator('#volume-sort').selectOption('available');
    check((await page.locator('#volume-rows tr').first().textContent()).includes('System'),'Available-space sort orders actual numeric capacity');
    await page.locator('#volume-sort').selectOption('usage');check((await page.locator('#volume-rows tr').first().textContent()).includes('Archive'),'Usage sort returns highest pressure first');
    check((await page.locator('#unmounted-list').textContent()).includes('Travel'),'Volumes view lists unmounted partition labels');
  });
  await scenario('A14',async()=>{
    const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;
    const target=path.join(output,'downloaded-demo-report.json');await download.saveAs(target);
    const report=JSON.parse(fs.readFileSync(target,'utf8'));
    check(report.snapshot.source==='demo','Downloaded artifact identifies the chosen source');
    check(report.snapshot.totals.used===lastSnapshot.totals.used&&report.history.length===60,'Downloaded bytes match deterministic returned data and history');
    check(await download.failure()===null,'Report download completes successfully');
  });
  await scenario('A17',async()=>{
    const prior=await page.locator('#volume-rows').textContent();
    await page.route('**/api/snapshot?source=demo',route=>route.abort('failed'));await refresh();
    check((await page.locator('#error-text').textContent()).includes('last successful sample'),'Network failure labels retained data as stale');
    check(await page.locator('#volume-rows').textContent()===prior,'Network failure retains the last successful view');
    await screenshot('stale-data-desktop.png');await page.unroute('**/api/snapshot?source=demo');
    const recovered=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/history');await page.locator('#retry').click();await recovered;
    await page.locator('#error-notice').waitFor({state:'hidden'});check(true,'Retry clears stale state after a successful real HTTP response');
  });
  await scenario('A16',async()=>{
    const fixture=await (await page.request.get(origin+'/api/snapshot?source=demo')).json();
    const empty=structuredClone(fixture);empty.drives=[];empty.partitions=[];empty.volumes=[];empty.findings=[];empty.totals={physical:0,total:0,used:0,available:0,reserved:0,drive_count:0,volume_count:0,unmounted_count:0,attention_count:0,percent:null};empty.coverage={usage:'complete',hardware_health:0};
    await mockSnapshot(empty);await nav('overview');check((await page.locator('#capacity-chart').textContent()).includes('No accessible mounted'),'Empty mounted inventory has an explicit empty state');
    check((await page.locator('#drive-cards').textContent()).includes('No physical drives'),'Empty physical inventory remains visible');
    await screenshot('empty-inventory-desktop.png');await page.unroute('**/api/snapshot?source=demo');
    const partial=structuredClone(fixture);partial.issues=['Fixture: permission denied reading one mount'];partial.coverage.usage='partial';partial.volumes[0].label='<img src=x onerror=alert(1)>';
    await mockSnapshot(partial);check(await page.locator('#partial-notice').isVisible(),'Partial collection exposes its coverage reason');
    check(await page.locator('#volume-rows img').count()===0&&(await page.locator('#volume-rows').textContent()).includes('<img'),'Untrusted labels are rendered as text');
    await page.unroute('**/api/snapshot?source=demo');
    await mockSnapshot({source:'demo',drives:[]});check((await page.locator('#error-text').textContent()).includes('unexpected data contract'),'Malformed API contracts produce a readable error');
    await page.unroute('**/api/snapshot?source=demo');await refresh();await page.locator('#error-notice').waitFor({state:'hidden'});
    const fresh=await context.newPage();fresh.on('pageerror',error=>results.errors.push(error.message));
    await fresh.route('**/api/snapshot?*',route=>route.fulfill({status:503,json:{error:'Fixture: collector unavailable'}}));
    await fresh.goto(origin);await fresh.locator('#error-notice').waitFor({state:'visible'});
    check(await fresh.locator('#export').isDisabled()&&!await fresh.locator('#dashboard').isVisible(),'Initial collector failure shows no invented data or enabled export');await fresh.close();
  });
  await scenario('A18',async()=>{
    for(const width of [1440,1024,768,390,360]){
      await page.setViewportSize({width,height:900});
      for(const view of ['overview','drives','volumes','activity','health']){
        await nav(view);check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${view} has no page overflow at ${width}px`);
      }
    }
    await page.setViewportSize({width:390,height:844});await nav('overview');await screenshot('demo-overview-mobile.png');
    await nav('volumes');await screenshot('demo-volumes-mobile.png');
    const capacity=page.locator('#volume-rows tr').first().locator('[data-label="Available"]');
    const bounds=await capacity.boundingBox();check(bounds.x>=0&&bounds.x+bounds.width<=390,'Mobile cards expose available capacity without horizontal scrolling');
  });
  await scenario('A19',async()=>{
    for(const width of [1440,390]){
      await page.setViewportSize({width,height:1000});
      for(const view of ['overview','drives','volumes','activity','health']){await nav(view);await accessibility(`${view}-${width}`)}
    }
    await nav('drives');await page.locator('[data-drive="/dev/sdb"]').click();await accessibility('unmounted-drive-dialog-mobile');await page.locator('#dialog-done').click();
    const navButton=page.locator('[data-view="health"]');await navButton.focus();await page.keyboard.press('Enter');
    check(await navButton.getAttribute('aria-current')==='page','Navigation works using only the keyboard');
    check(await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),'Browser QA respects reduced-motion preference');
    check(results.errors.length===0,'No uncaught browser errors across the entire journey');
  });
  await page.setViewportSize({width:1440,height:1120});await nav('overview');await screenshot('demo-overview-desktop.png');
  await page.locator('#source').selectOption('live');await page.locator('#dashboard').waitFor({state:'visible'});await screenshot('live-overview-final.png');
  results.passed=true;
}catch(error){results.passed=false;results.failure=error.stack;console.error(error);try{await screenshot('failure.png')}catch{}}
finally{results.finished_at=new Date().toISOString();fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify(results,null,2));await browser.close()}
if(!results.passed)process.exitCode=1;
