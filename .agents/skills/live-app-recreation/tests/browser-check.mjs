import path from 'node:path';
import {constants} from 'node:fs';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright-core');
function findBrowser(){
 if(process.env.BROWSER_EXECUTABLE)return process.env.BROWSER_EXECUTABLE;
 for(const name of ['google-chrome','chromium','chromium-browser','chrome'])for(const dir of (process.env.PATH||'').split(path.delimiter)){
  const candidate=path.join(dir,name);try{fs.accessSync(candidate,constants.X_OK);return candidate}catch{}
 }
 return undefined;
}
const [origin,output]=process.argv.slice(2);
if(!origin||!output)throw Error('Usage: node browser-check.mjs <preview-url> <evidence-directory>');
fs.mkdirSync(output,{recursive:true});
import assert from 'node:assert/strict';
import fs from 'node:fs';
const browser=await chromium.launch({executablePath:findBrowser(),headless:true,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:1080},reducedMotion:'reduce'});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const checks=[];
async function done(){await page.waitForFunction(()=>!document.querySelector('#input').disabled,{timeout:20000})}
async function prompt(text){await page.locator('#input').fill(text);await page.locator('#composer').evaluate(f=>f.requestSubmit())}
try {
const response=await page.goto(new URL('?noautoplay',origin).href);assert.equal(response.status(),200);checks.push('page serves successfully');
await page.getByRole('button',{name:'Create a note',exact:false}).first().click();await page.locator('#modal:not([hidden])').waitFor();await page.locator('#deny').click();await done();
assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('live-app-recreation-v1')).files['Notes/hello.md']),undefined);checks.push('denied write does not create file');
await prompt('Create a note');await page.locator('#modal:not([hidden])').waitFor();await page.locator('#allow').click();await done();
assert.match(await page.evaluate(()=>JSON.parse(localStorage.getItem('live-app-recreation-v1')).files['Notes/hello.md']),/Made with your agent/);checks.push('approved write persists file');
await prompt('Edit my note');await page.locator('#modal:not([hidden])').waitFor();await page.locator('#allow').click();await done();
assert.match(await page.evaluate(()=>JSON.parse(localStorage.getItem('live-app-recreation-v1')).files['Notes/hello.md']),/Edited together/);checks.push('approved edit persists content');
await page.locator('[data-tab=files]').click();await page.getByRole('button',{name:/Notes\/hello.md/}).click();assert.match(await page.locator('#file-content').textContent(),/Edited together/);checks.push('Files view opens actual edited content');
await page.locator('[data-tab=settings]').click();await page.locator('#confirm').uncheck();await page.locator('[data-tab=chat]').click();
await prompt('test workspace escape');await done();assert.match(await page.locator('.tool.failed').last().textContent(),/outside/);checks.push('traversal blocked in browser');
await page.reload();assert.match(await page.evaluate(()=>JSON.parse(localStorage.getItem('live-app-recreation-v1')).files['Notes/hello.md']),/Edited together/);assert.equal(await page.locator('#confirm').isChecked(),false);checks.push('files, messages and settings survive reload');
await page.locator('#new-chat').click();await prompt('Read my welcome file');await page.locator('#send').click();await done();checks.push('stop response releases composer');
await page.locator('#history').click();assert.equal(await page.locator('.conversation-row').count(),2);await page.locator('#close-history').click();checks.push('conversation history retains both chats');
await page.locator('#reset').click();assert.equal(Object.keys(await page.evaluate(()=>JSON.parse(localStorage.getItem('live-app-recreation-v1')).files)).length,2);checks.push('reset restores clean workspace');
await page.locator('[data-tab=settings]').click();await page.locator('#confirm').check();await page.locator('[data-tab=chat]').click();
await page.locator('#tour').click();
for(let i=0;i<2;i++){await page.locator('#modal:not([hidden])').waitFor({timeout:25000});await page.locator('#allow').click()}
await page.waitForFunction(()=>document.querySelector('#tour').textContent.includes('Play'),{timeout:25000});assert.match(await page.locator('#file-content').textContent(),/Edited together/);checks.push('full walkthrough completes with two user approvals');
await page.locator('[data-tab=chat]').click();await page.waitForFunction(()=>document.querySelector('[data-tab=chat]').classList.contains('selected'));await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await page.screenshot({path:path.join(output,'browser-preview.png'),fullPage:true});
await page.setViewportSize({width:360,height:800});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth,{timeout:5000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:path.join(output,'browser-mobile.png'),fullPage:true});checks.push('synthetic mobile layout has no horizontal overflow');
assert.deepEqual(errors,[]);checks.push('no browser JavaScript errors');
fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:true,checks,errors,scope:'Chrome browser tests of recreation only'},null,2));console.log(JSON.stringify({passed:true,checks},null,2));
}catch(error){
fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({passed:false,checks,errors,error:String(error)},null,2));
await page.screenshot({path:path.join(output,'browser-failure.png'),fullPage:true}).catch(()=>{});
throw error;
}finally{await browser.close()}
