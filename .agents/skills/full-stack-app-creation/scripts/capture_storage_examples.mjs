// Generate synthetic-only examples through an isolated app's actual HTTP/UI.
import fs from 'node:fs';
import path from 'node:path';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const [origin,output]=process.argv.slice(2);
if(!origin||!output)throw Error('Usage: capture_storage_examples.mjs <isolated-local-origin> <fresh-output-directory>');
let executable=process.env.BROWSER_EXECUTABLE;
if(!executable)for(const folder of (process.env.PATH||'').split(path.delimiter))for(const name of ['google-chrome','chromium','chromium-browser']){const candidate=path.join(folder,name);try{fs.accessSync(candidate,fs.constants.X_OK);executable ||= candidate}catch{}}
if(!executable)throw Error('Existing Chrome/Chromium required');
fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch({executablePath:executable,headless:true,args:['--no-sandbox']});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1080},timezoneId:'UTC',reducedMotion:'reduce'});
 await context.addInitScript(()=>localStorage.setItem('atlas.preferences',JSON.stringify({source:'demo',units:'binary',view:'overview',auto:false})));
 const page=await context.newPage();
 await page.route('**/api/snapshot?source=demo',async route=>{const response=await route.fetch();const data=await response.json();if(data.source!=='demo'||data.host!=='atlas-demo')throw Error('Refusing non-synthetic sample');data.captured_at='2000-01-01T12:00:00+00:00';fs.writeFileSync(path.join(output,'synthetic-snapshot.json'),JSON.stringify(data,null,2));await route.fulfill({json:data})});
 await page.goto(origin);await page.locator('#dashboard').waitFor({state:'visible'});
 await page.screenshot({path:path.join(output,'overview-desktop.png'),fullPage:true});
 await page.locator('[data-view="volumes"]').click();await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'volumes-mobile.png'),fullPage:true});
 fs.writeFileSync(path.join(output,'README.md'),'# Synthetic storage examples\n\nHistorical illustrative captures generated from the demo source of the bundled app. Fictional devices and labels; timestamp normalized. These images and JSON are examples, not live health or current acceptance evidence. Regenerate with scripts/capture_storage_examples.mjs against an isolated task copy.\n');
}finally{await browser.close()}
