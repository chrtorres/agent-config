import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {resolve} from "node:path";

const [url, playwright, executablePath, comparison]=process.argv.slice(2);
const {chromium}=createRequire(import.meta.url)(resolve(playwright));
const browser=await chromium.launch({executablePath,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
let count=0;
const check=(condition,label)=>{assert.ok(condition,label);console.log("PASS "+label);count++;};
const address=(base,quality)=>new URL("/?quality="+quality,base).href;
const change=(page,id,value)=>page.locator("#"+id).evaluate((el,n)=>{el.value=n;el.dispatchEvent(new Event("input"));},value);
const ready=page=>page.waitForFunction(()=>window.movementReview?.inspect().render?.matteReady);
const state=page=>page.evaluate(()=>window.movementReview.inspect());
const seek=async(page,frame)=>{
  await change(page,"time",frame);
  await page.waitForFunction(frame=>{const s=window.movementReview.inspect();return s.position===frame&&s.render.matteReady;},frame);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
};
const raster=(page,corner=false)=>page.locator("#screen").evaluate(async(canvas,corner)=>{
  const gl=canvas.getContext("webgl");
  const [w,h]=corner?[24,24]:[canvas.width,canvas.height];
  const pixels=new Uint8Array(w*h*4);
  gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256",pixels))].join(",");
},corner);

try {
  for(const quality of ["native","4k"]) {
    const page=await browser.newPage({viewport:{width:1280,height:1024}});
    const errors=[];
    page.on("pageerror",e=>errors.push(e.message));
    try {
      const response=await page.goto(address(url,quality));
      check(response.ok()&&response.headers()["cache-control"]==="no-store",quality+" review is served without caching");
      await ready(page);
      for(const path of ["/timeline/timeline.json","/regions.json","/cleanup-tracks.json","/motion-study.json","/motion-splats.json","/skin/skin-000.png"]){
        const res=await page.request.head(new URL(path,url).href);
        check(res.ok()&&res.headers()["cache-control"]==="no-store",quality+" serves ephemeral "+path);
      }
      const input=await page.request.get(new URL("/source.mp4",url).href,{headers:{Range:"bytes=0-31"}});
      check(input.status()===206&&(await input.body()).length===32&&input.headers()["cache-control"]==="no-store",
        quality+" exposes the original via a no-store range response");
      check((await page.request.get(new URL("/input.mp4",url).href)).status()===404,quality+" excludes staging files");
      const regions=await (await page.request.get(new URL("/regions.json",url).href)).json();
      const chosen=regions.frames.findIndex((row,i)=>i>0&&row.torso?.[0]&&regions.frames[i+1]?.torso?.[0]);
      check(chosen>0&&Object.keys(regions.parts).length>37,quality+" rebuilds named anatomy from the supplied clip");
      await seek(page,chosen);
      const original=await raster(page), corner=await raster(page,true);
      const baseState=await state(page);
      const {width,height,outputWidth,outputHeight}=baseState.render;
      const longEdge=Math.max(width,height);
      const side=value=>quality==="native"?value:Math.max(2,2*Math.round(value*1920/longEdge));
      check(outputWidth===side(width)&&outputHeight===side(height),quality+" uses the expected render size");
      await change(page,"stage-zoom",2);
      check((await state(page)).stageZoom.scale===2&&await raster(page)===original,quality+" zoom preserves video pixels");
      await page.locator("#stage-zoom-reset").click();
      await page.locator("#feature-point-mode").click();
      const [x,y]=regions.frames[chosen].torso[0];
      const point=await page.locator("#screen").evaluate((canvas,[x,y])=>{
        const p=canvas.getBoundingClientRect(), s=window.movementReview.inspect().render;
        return [p.left+x/s.width*p.width,p.top+y/s.height*p.height];
      },[x,y]);
      await page.mouse.click(...point);
      await page.waitForFunction(()=>{
        const view=window.movementReview.inspect().inspection;
        return view?.selected?.key.startsWith("point-")&&view.available;
      });
      check((await state(page)).inspection.available,quality+" picks a visible custom area");
      await change(page,"feature-width",109.5);
      await page.waitForFunction(()=>window.movementReview.inspect().render.subjects.length>0);
      check(await raster(page)!==original&&await raster(page,true)===corner,quality+" reshapes local pixels and preserves the distant background");
      await page.locator("#feature-point-remove").click();
      await page.waitForFunction(()=>window.movementReview.inspect().render.subjects.length===0);
      check(await raster(page)===original,quality+" removal restores the entire raster");
      check(errors.length===0,quality+" operates without browser errors");
      if(comparison) {
        const sample=async view=>{
          const probes=[];
          const motionTab=view.getByRole("tab",{name:"Motion",exact:true});
          if(await motionTab.count())await motionTab.click();
          for(const fraction of [0,.4,1]) {
            const frame=Math.round((regions.frames.length-1)*fraction);
            await seek(view,frame);
            const neutral=await raster(view);
            await view.locator("#part").selectOption({label:"Right arm"});
            await change(view,"joint-y",-.35);
            await view.waitForFunction(()=>window.movementReview.inspect().render.liveMotion);
            probes.push([neutral,await raster(view)]);
            await view.locator("#reset").click();
            await view.waitForFunction(()=>!window.movementReview.inspect().render.liveMotion);
          }
          return probes;
        };
        // Keep only one UHD context alive at a time on software renderers.
        const rebuilt=await sample(page);
        await page.close();
        const expected=await browser.newPage({viewport:{width:1280,height:1024}});
        try {
          await expected.goto(address(comparison,quality));
          await ready(expected);
          const reference=await sample(expected);
          for(const [i,[neutral,posed]] of rebuilt.entries()) {
            check(neutral===reference[i][0],quality+" neutral pixels match the approved reference");
            check(posed===reference[i][1],quality+" posed pixels match the approved reference");
          }
        } finally { await expected.close(); }
      }
    } finally {await page.close();}
  }
} finally {await browser.close();}
console.log("Browser checks: "+count);
