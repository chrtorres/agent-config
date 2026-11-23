import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {pathToFileURL} from "node:url";

const [url, playwright, executablePath, fixtures] = process.argv.slice(2);
const {chromium} = await import(pathToFileURL(join(playwright, "index.mjs")));
const browser = await chromium.launch({executablePath, args:["--no-sandbox"]});
const passed = [];
function check(value, name) {
  assert.ok(value, name);
  passed.push(name);
}
try {
  const page = await browser.newPage({viewport:{width:1120,height:820}});
  const response = await page.goto(url);
  check(response.ok(), "Editor served over HTTP");
  const toggle = page.locator("#face-swap > summary");
  await toggle.click();
  check(await page.getByRole("button",{name:"Run Face Swap"}).isVisible(), "Face Swap opens inside the editor");
  check(new URL(page.url()).pathname === "/", "Toggle does not navigate");
  const route = path => new URL(path, url).href;
  for (const path of ["/style.css","/workspace.mjs","/face-swap.mjs","/viewer-size.mjs"]) {
    check((await page.request.get(route(path))).ok(), `${path} served`);
  }
  const getStatus = async () => (await page.request.get(route("/face-swap/status"))).json();
  check((await getStatus()).phase === "idle","Starts idle");
  check((await page.request.get(route("/face-swap/result.mp4"))).status() === 404,"Unverified export unavailable");
  const rejected = await page.request.post(route("/face-swap/cancel"),{headers:{Origin:"https://example.com"}});
  check(rejected.status() === 403,"Cross-origin action rejected");
  const drop = (input, files) => input.evaluate((element, data) => {
    const transfer = new DataTransfer();
    for (const file of data) transfer.items.add(new File([new Uint8Array(file.bytes)], file.name, {type:file.type}));
    const zone = element.closest("[data-media-drop]");
    zone.dispatchEvent(new DragEvent("dragover", {dataTransfer:transfer,bubbles:true,cancelable:true}));
    const highlighted = zone.classList.contains("is-dragging");
    zone.dispatchEvent(new DragEvent("drop", {dataTransfer:transfer,bubbles:true,cancelable:true}));
    return highlighted;
  }, files);
  const target = page.getByLabel("Video or image file");
  const donor = page.getByLabel("Source image or video");
  await drop(target,[{name:"test.txt",type:"text/plain",bytes:[1,2]}]);
  check(await page.getByText("Choose a video or image file.").isVisible(),"Unsupported drop is rejected");
  check(await drop(target,[{name:"target.mp4",type:"video/mp4",bytes:[...await readFile(join(fixtures,"target.mp4"))]}]),
    "Target drop zone gives hover feedback");
  check(await page.getByText("target.mp4",{exact:true}).isVisible(),"Dropped target filename is shown");
  const stage = await page.getByRole("region",{name:"Quick review",exact:true}).boundingBox();
  const tools = await page.locator(".landing-controls").boundingBox();
  check(stage && tools && stage.x < tools.x,"Desktop puts the preview beside the tools");
  await page.setViewportSize({width:390,height:820});
  check(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),"Mobile layout fits the viewport");
  await page.setViewportSize({width:1120,height:820});
  check(await drop(donor,[{name:"source.mp4",type:"video/mp4",bytes:[...await readFile(join(fixtures,"source.mp4"))]}]),
    "Face Swap accepts a dropped source video");
  check(await page.getByRole("button",{name:"Run Face Swap"}).isDisabled(),"Video source requires a selected frame");
  const source = page.getByLabel("Source video",{exact:true});
  await page.waitForFunction(() => document.querySelector("#face-source-video").readyState >= 2);
  await source.evaluate(async media => {
    await new Promise(resolve => {
      media.addEventListener("seeked",resolve,{once:true});
      media.currentTime=.25;
    });
  });
  await page.getByRole("button",{name:"Use current frame"}).click();
  await page.getByText("Frame selected at 0.25 s").waitFor();
  check(await page.getByRole("button",{name:"Run Face Swap"}).isDisabled(),"Swap requires an explicit destination face");
  await page.waitForFunction(() => document.querySelector("#face-target-video").readyState >= 2);
  const targetVideo = page.getByLabel("Target video frame");
  const originalWidth = (await targetVideo.boundingBox()).width;
  await page.getByLabel("Target zoom").fill("3");
  check(Math.abs((await targetVideo.boundingBox()).width - originalWidth*3)<2,"Target zoom magnifies the selection view");
  await page.getByRole("group",{name:"Target face picker"}).press("Enter");
  await page.getByText(/Target face selected at/).waitFor();
  const green = page.getByRole("img",{name:"Green preview of the selected face mask"});
  check(await green.isVisible(),"Green mask confirms the destination");
  check(Math.abs((await green.boundingBox()).width-(await targetVideo.boundingBox()).width)<2,
    "Green mask stays registered while zoomed");
  await page.getByRole("button",{name:"Reset zoom",exact:true}).click();
  check(Math.abs((await targetVideo.boundingBox()).width-originalWidth)<2,"Reset zoom restores the full frame");
  check(await page.getByRole("img",{name:"Selected source face frame"}).isVisible(),"Source video still selected");
  check(Boolean(await page.getByLabel("Video or image file").inputValue()),"Existing editor video selected");
  await page.getByRole("button",{name:"Run Face Swap"}).click();
  await page.getByText(/Face Swap is running/).waitFor();
  check(await page.getByRole("button",{name:"Play preview",exact:true}).isEnabled(),"Quick Review can be used while the swap runs");
  check(await page.getByRole("button",{name:"Cancel",exact:true}).isVisible(),"Running job cancellable");
  await page.getByRole("heading",{name:"Verified result"}).waitFor({timeout:120000});
  const {phase,report} = await getStatus();
  check(phase === "ready","Result published");
  check(report.frames === 12,"All 12 frames retained");
  check(report.swapped > 0,"Face pixels modified");
  check(report.unchanged > 0 && report.swapped + report.unchanged === 12,"Missing-face frames retained");
  check(report.tracking?.detected + report.tracking?.flow_carried > 0,"Action tracking used");
  check(report.video === "verified","Decoded frame hashes and timing verified");
  check(report.audio === "verified","Audio verified");
  check(report.outside_mask === "byte exact","Outside-mask bytes verified");
  const result = await page.request.get(route("/face-swap/result.mp4"),{headers:{Range:"bytes=0-31"}});
  check(result.status() === 206 && (await result.body()).length === 32,"Output supports byte ranges");
  check(result.headers()["cache-control"] === "no-store","Export not cached");
  const preview = await page.request.get(route("/face-swap/preview.mp4"),{headers:{Range:"bytes=0-31"}});
  check(preview.status() === 206 && preview.headers()["content-range"] !== result.headers()["content-range"],
    "Separate playback rendition uses byte ranges");
  await page.locator("#face-display").click();
  const video = page.getByLabel("Face swap preview");
  check(await video.evaluate(media=>Boolean(media.closest(".quick-frame"))),"Swap uses the existing Quick Review viewport");
  await page.waitForFunction(() => document.querySelector("#face-video").readyState >= 2);
  check(await video.evaluate(media=>media.videoWidth===480 && media.videoHeight===520),"Chrome decodes playback rendition");
  await video.evaluate(media=>media.play());
  await page.waitForFunction(() => document.querySelector("#face-video").currentTime > .1);
  check(await video.evaluate(media=>media.currentTime > .1),"Verified video plays in Chrome");
  await video.evaluate(async media=>{
    media.pause();
    await new Promise(resolve=>{
      media.addEventListener("seeked",resolve,{once:true});
      media.currentTime=.25;
    });
  });
  check(await page.locator("#face-monitor").isVisible(),"Sidebar also shows the swapped frame");
  const rgb = await video.evaluate(media => {
    const canvas = document.createElement("canvas");
    canvas.width = media.videoWidth;
    canvas.height = media.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(media,0,0);
    return Array.from(ctx.getImageData(15,15,1,1).data).slice(0,3);
  });
  check(rgb.every((value,index)=>Math.abs(value-[116,104,124][index]) <= 4),
    `Protected background colors display correctly in Chrome (${rgb.join(",")})`);
  if (process.env.FOOTAGE_SYNTHETIC_SCREENSHOT) {
    await page.screenshot({path:process.env.FOOTAGE_SYNTHETIC_SCREENSHOT});
  }
  await page.locator("#face-stage-display").click();
  check(await page.locator("#face-monitor").isHidden(),"Show original clears the sidebar mirror");
  check(Math.abs(await page.locator("#quick-video").evaluate(media=>media.currentTime)-.25)<.02,"Comparison keeps the playhead");
  check(await page.locator("#quick-video").isVisible(),"Original returns in the same editor viewport");
  await page.getByRole("button",{name:"Clear result"}).click();
  await page.getByRole("heading",{name:"Verified result"}).waitFor({state:"hidden"});
  check((await getStatus()).phase === "idle","Clear resets job");
  check((await page.request.get(route("/face-swap/result.mp4"))).status() === 404,"Clear revokes download");
  console.log(JSON.stringify({checks:passed,count:passed.length,report},null,2));
} finally {
  await browser.close();
}
