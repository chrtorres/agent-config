import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {resolve} from "node:path";
import {writeFile} from "node:fs/promises";

const [url,modulePath,executablePath,report]=process.argv.slice(2);
const {chromium}=createRequire(import.meta.url)(resolve(modulePath));
const browser=await chromium.launch({executablePath,args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
const checks=[];
const check=(condition,label)=>{
  assert.ok(condition,label);
  checks.push(label);
  console.log("PASS "+label);
};
const near=(a,b,tolerance=.5)=>Math.abs(a-b)<=tolerance;
try {
  for(const quality of ["native","4k"]) {
    const page=await browser.newPage({viewport:{width:1280,height:960}});
    const errors=[];
    page.on("pageerror",error=>errors.push(error.message));
    const inspect=()=>page.evaluate(()=>window.movementReview.inspect());
    const measurements=()=>page.evaluate(()=>{
      const stage=document.getElementById("stage-viewport"),canvas=document.getElementById("screen");
      const rect=element=>element.getBoundingClientRect().toJSON();
      return {stage:rect(stage),canvas:rect(canvas),raster:[canvas.width,canvas.height],
        markerTracksVideo:document.getElementById("feature-marker").parentElement===canvas.parentElement};
    });
    const center=rect=>[rect.x+rect.width/2,rect.y+rect.height/2];
    const slider=page.getByRole("slider",{name:"Video zoom"}),fit=page.getByRole("button",{name:"Fit video"});
    const address=new URL(url);address.searchParams.set("quality",quality);
    try {
      await page.goto(address.href);
      await page.waitForFunction(()=>window.movementReview?.inspect().render?.matteReady);
      check(await slider.isVisible()&&await fit.isDisabled(),quality+" has accessible main zoom controls and starts fitted");
      const before=await inspect(), initial=await measurements();
      check(before.stageZoom.scale===1&&near(initial.canvas.width,initial.stage.width)&&near(initial.canvas.height,initial.stage.height),
        quality+" fits the full video in its viewport");
      check(initial.markerTracksVideo,quality+" selection guide shares the video transform");
      const wheel=async(ctrlKey,dx,dy)=>page.locator("#stage-viewport").evaluate((stage,{ctrlKey,dx,dy})=>{
        const rect=stage.getBoundingClientRect();
        const event=new WheelEvent("wheel",{ctrlKey,deltaY:-320,cancelable:true,clientX:rect.x+dx,clientY:rect.y+dy});
        stage.dispatchEvent(event);
        return event.defaultPrevented;
      },{ctrlKey,dx,dy});
      const dx=initial.stage.width*.38,dy=initial.stage.height*.57;
      check(!await wheel(false,dx,dy)&&(await inspect()).stageZoom.scale===1,quality+" plain wheel still supports page scrolling");
      check(await wheel(true,dx,dy),quality+" modifier wheel is handled by video zoom");
      const zoomed=await inspect(), after=await measurements();
      check(zoomed.stageZoom.scale>2&&near(after.stage.width,initial.stage.width)&&near(after.stage.height,initial.stage.height),
        quality+" enlarges the video inside the unchanged viewport");
      check(initial.raster.every((dimension,i)=>dimension===after.raster[i])&&zoomed.motion.root.every((axis,i)=>axis===before.motion.root[i]),
        quality+" zoom leaves the render size and performer movement untouched");
      check(near((after.stage.x+dx-after.canvas.x)/after.canvas.width,dx/initial.canvas.width,.002)&&
        near((after.stage.y+dy-after.canvas.y)/after.canvas.height,dy/initial.canvas.height,.002),
        quality+" wheel zoom preserves the pointer's exact video position");

      const [x,y]=center(after.stage);
      await page.locator("#screen").evaluate(canvas=>{
        window.stageZoomClickCount=0;
        canvas.addEventListener("click",()=>window.stageZoomClickCount++);
      });
      await page.mouse.move(x,y);
      await page.mouse.down();
      await page.mouse.move(x+35,y-30,{steps:4});
      await page.mouse.up();
      let state=await inspect();
      check(near(state.stageZoom.x-zoomed.stageZoom.x,35)&&near(state.stageZoom.y-zoomed.stageZoom.y,-30),
        quality+" pointer drag pans in screen pixels");
      check(await page.evaluate(()=>window.stageZoomClickCount)===0,quality+" drag does not dispatch a feature click");
      await page.mouse.click(x,y);
      check(await page.evaluate(()=>window.stageZoomClickCount)===1,quality+" ordinary click remains available while zoomed");
      const beforeKeys=state.stageZoom;
      await page.locator("#screen").focus();
      await page.keyboard.press("Alt+ArrowRight");
      state=await inspect();
      check(state.stageZoom.x<beforeKeys.x&&JSON.stringify(state.motion.offsets)===JSON.stringify(before.motion.offsets),
        quality+" keyboard panning leaves performer articulation untouched");
      await page.locator("#time").evaluate(input=>{input.value=90;input.dispatchEvent(new Event("input"));});
      await page.waitForFunction(()=>{const state=window.movementReview.inspect();return state.position===90&&state.render.matteReady;});
      check((await inspect()).stageZoom.scale===state.stageZoom.scale,quality+" scrub retains the same zoom");

      if(quality==="native") {
        await page.setViewportSize({width:390,height:844});
        await page.waitForFunction(()=>{
          const bound=document.getElementById("stage-viewport").getBoundingClientRect();
          return bound.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth;
        });
        const mobile=await measurements();
        check(mobile.stage.width<=390&&mobile.canvas.width>mobile.stage.width,quality+" mobile layout clips the enlarged video without horizontal overflow");
      }
      await slider.evaluate(input=>{input.value=input.max;input.dispatchEvent(new Event("input"));});
      const maxState=await inspect();
      const labelScale=await page.locator("#feature-marker-label").evaluate(el=>Number(getComputedStyle(el).scale));
      check(maxState.stageZoom.scale===8&&near(labelScale,.125,.001),
        quality+" reaches 8× while the selection label keeps its screen size");
      await fit.click();
      const restored=await inspect(), fitted=await measurements();
      check(restored.stageZoom.scale===1&&restored.stageZoom.x===0&&restored.stageZoom.y===0&&
        near(fitted.stage.width,fitted.canvas.width)&&near(fitted.stage.height,fitted.canvas.height),quality+" Fit video resets zoom and pan");
      check(errors.length===0,quality+" reports no browser errors");
    } finally { await page.close(); }
  }
} finally { await browser.close(); }
if(report)await writeFile(report,JSON.stringify({count:checks.length,checks},null,2)+"\n");
