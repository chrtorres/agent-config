import {SecondaryMotion} from "./secondary.mjs";
import {createInspector} from "./inspect.mjs";
import { Motion,PARTS } from "./motion.mjs";
import { createRenderer } from "./render.mjs";
import {createStageZoom} from "./stage-zoom.mjs";
import {anchorPoint,validPoint} from "./point-regions.mjs";
import {ensureUhd} from "./uhd.mjs";
import {onStatus, progressBar} from "./status.mjs";
import {downloadVideo,saveMedia} from "./media-download.mjs";
import {COLOR_LABELS,COLOR_TARGETS,validColors} from "./colors.mjs";

const $=id=>document.getElementById(id);
const video=$("source"), canvas=$("screen"), slider=$("time"), menu=$("part");
const stageZoom=createStageZoom(canvas);
const useUhd=new URLSearchParams(location.search).get("quality")==="4k";
const knobs=["joint-x","joint-y","joint-r"].map($);
const motion=new Motion(), keys=new Set();
const tone=[0,0,0];
const toneInputs=["tone-light","tone-warm","tone-saturation"].map($);
for(const [index,input] of toneInputs.entries())input.oninput=()=>{
  tone[index]=Number(input.value)/100;
  $(input.id+"-value").value=input.value;
  changed=true;
};
$("tone-reset").onclick=()=>{
  for(const input of toneInputs) {input.value=0;input.oninput();}
};
// Hair and facial-feature dyes: {target:[hex color, strength 0..100]}.
const colors={};
const colorInputs={};
for(const key of COLOR_TARGETS) {
  const row=document.createElement("div");
  row.className="row color-row";row.dataset.target=key;
  const picker=Object.assign(document.createElement("input"),{type:"color",value:"#8a3b2a",id:"color-"+key});
  picker.setAttribute("aria-label",COLOR_LABELS[key]+" color");
  const strength=Object.assign(document.createElement("input"),{type:"range",min:0,max:100,step:1,value:0,id:"color-"+key+"-strength"});
  const output=Object.assign(document.createElement("output"),{id:"color-"+key+"-value",value:"0%"});
  const label=Object.assign(document.createElement("label"),{className:"slider feature-slider",textContent:COLOR_LABELS[key]+" "});
  label.append(picker,strength,output);
  row.append(label);
  $("color-rows").append(row);
  const update=()=>{
    output.value=strength.value+"%";
    if(Number(strength.value)>0)colors[key]=[picker.value,Number(strength.value)];
    else delete colors[key];
    changed=true;
  };
  picker.oninput=strength.oninput=update;
  colorInputs[key]={row,picker,strength,update};
}
$("color-reset").onclick=()=>{
  for(const {strength,update} of Object.values(colorInputs)) {strength.value=0;update();}
};
const colored=()=>Object.keys(colors).length>0;
let secondary=null,study=null,traceFrame=-1,splatPreview=null,splatLoading=false,splatsAvailable=false,splatFrame=-1,splatPoints=0;
let inspector=null, renderer=null, ready=false, changed=true, requested=null, pendingFrame=null, position=0;
let padIndex=null, pressed=[], stamp=null, elapsed=0;
let limit=0, fps=30, cuts=[], playbackStart=0, frameTimes=null;
const pointerDirections=new Map();
const points=Object.create(null), pointMode=$("feature-point-mode"), radiusInput=$("feature-radius");
let nextPoint=1;
function editRecipe() {
  const toPercent=values=>values.map(value=>Math.round(value*200)/2);
  const shapes=Object.fromEntries(Object.entries(inspector.adjustments).map(([key,values])=>[key,toPercent(values)]));
  const recipe={version:1,shapes,tone:toPercent(tone)};
  if(colored())recipe.colors=structuredClone(colors);
  const editedPoints=Object.fromEntries(Object.entries(points).filter(([key])=>Object.hasOwn(shapes,key)));
  if(Object.keys(editedPoints).length)recipe.points=editedPoints;
  if(inspector.cleanup())recipe.cleanup=true;
  if(!$("soft-physics").checked)recipe.physics=false;
  if(inspector.cleanup()&&secondary?.enabled)recipe.recordedDynamics=true;
  return recipe;
}
$("save-edits").onclick=()=>{
  saveMedia(new Blob([JSON.stringify(editRecipe(),null,2)+"\n"],{type:"application/json"}), "footage-edit.json");
};
$("download-edited").onclick=async()=>{
  const button = $("download-edited");
  const status = $("workspace-status");
  button.disabled = true;
  status.hidden = false;
  status.textContent = "Rendering shape and color edits…";
  const bar = progressBar(status, "Export progress");
  bar.show(null);
  const stop = onStatus(({export: job}) => { if (job.phase === "rendering") bar.show(job); });
  try {
    const recipe = editRecipe();
    if (Object.values(recipe.shapes).some(values => values.some(Boolean)) || recipe.tone.some(Boolean) || recipe.colors) {
      await downloadVideo("/export-edit", JSON.stringify(recipe), {"Content-Type":"application/json"});
    } else {
      const response = await fetch("/video.mp4");
      if (!response.ok) throw new Error("The prepared video is unavailable.");
      saveMedia(await response.blob(), "footage-edited.mp4");
    }
    status.textContent = "Edited video downloaded.";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    stop();
    bar.remove();
    button.disabled = false;
  }
};
$("download-frame").onclick=()=>{
  canvas.toBlob(frame => {
    if (frame) saveMedia(frame, "footage-frame.png");
  }, "image/png");
};
const STEP=1/120;
const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
const frameTime=index=>frameTimes?.[index] ?? index/fps;
function frameIndex(time) {
  const elapsed = time - playbackStart;
  if (!frameTimes) return clamp(Math.round(elapsed*fps),0,limit);
  let first = 0, end = frameTimes.length;
  while (first < end) {
    const middle = Math.floor((first+end)/2);
    if (frameTimes[middle] <= elapsed + .0000005) first = middle + 1;
    else end = middle;
  }
  return Math.max(0, first-1);
}
const sceneOf=index=>Math.max(0,cuts.findIndex(([a,b])=>index>=a&&index<b));
const currentShot=()=>sceneOf(position);

function setPointMode(active) {
  pointMode.setAttribute("aria-pressed",String(active));
  pointMode.textContent=active?"Cancel custom pick":"Pick custom area";
  if(active)$("feature-status").textContent="Click a visible area in the video or magnifier.";
  else inspector?.render();
}
function registerPoint(key,point) {
  points[key]=point;
  const label=renderer.augmentation.parts[point.anchor];
  inspector.registerPoint(key,"Custom area "+key.slice(6)+" · "+label);
}
function createPoint(x,y) {
  if(!renderer.isForeground(x,y))return false;
  const point=anchorPoint(...renderer.sourcePoint(x,y),renderer.augmentation.frames[position]);
  if(!point)return false;
  while(Object.hasOwn(points,"point-"+nextPoint))nextPoint++;
  const key="point-"+nextPoint++;
  video.pause();
  registerPoint(key,point);
  setPointMode(false);
  inspector.select(key);
  return true;
}
function syncPointControls() {
  const point=points[inspector?.current()];
  $("feature-radius-row").hidden=$("feature-point-remove").hidden=!point;
  if(!point)return;
  radiusInput.value=point.radius;
  $("feature-radius-value").value=point.radius+" px";
}
pointMode.onclick=()=>setPointMode(pointMode.getAttribute("aria-pressed")!=="true");
radiusInput.oninput=()=>{
  const point=points[inspector?.current()];
  if(!point)return;
  point.radius=Number(radiusInput.value);
  inspector.invalidateCleanup();
};
$("feature-point-remove").onclick=()=>{
  const key=inspector?.current();
  if(!Object.hasOwn(points,key))return;
  delete points[key];
  inspector.removePoint(key);
};
document.addEventListener("keydown",event=>{
  if(event.key==="Escape"&&pointMode.getAttribute("aria-pressed")==="true")setPointMode(false);
});

for(const [value,name] of PARTS.entries()) menu.add(new Option(name,String(value)));
const failed=text=>{$("error").textContent=text;$("error").hidden=false;$("loading").hidden=true;};
function display() {
  const time=frameTime(position);
  $("clock").textContent=String(Math.floor(time/60))+":"+Number(time%60).toFixed(2).padStart(5,"0");
  if(document.activeElement!==slider)slider.value=position;
  $("play").textContent=video.paused?"Play video":"Pause video";
  $("resolution").textContent=canvas.width+" × "+canvas.height;
  const shaped=Object.keys(inspector?.adjustments??{}).length>0, toned=tone.some(Boolean)||colored();
  $("save-edits").disabled=!shaped&&!toned;
  const rendered=renderer?.inspect();
  $("motion-state").textContent=motion.active()?(
    !rendered?.matteReady?"Loading pose layer":
    rendered.motionScale<.95?"Motion limited to available pixels":"Live pose"
  ):shaped?"Shape edits":colored()?"Colors adjusted":tone.some(Boolean)?"Skin tone adjusted":"Original frame";
  menu.value=motion.selected;
  for(let i=0;i<3;i++) {
    if(document.activeElement!==knobs[i])knobs[i].value=motion.offsets[motion.selected][i];
  }
}

function accept(index) {
  if(!renderer||video.seeking)return;
  pendingFrame=index;
  const affectsPixels=motion.active()||tone.some(Boolean)||colored()||Object.keys(inspector?.adjustments??{}).length>0;
  if(!renderer.frame(video,index,affectsPixels))return;
  pendingFrame=null;
  position=index;
  if(requested===index)requested=null;
  changed=true;
  ready=true;
  $("download-frame").disabled = false;
  $("loading").hidden=true;
  display();
}

function renderTrace(force=false) {
  if(!study||!$("motion-traces").open||!force&&traceFrame===position)return;
  traceFrame=position;
  const key=$("motion-region").value;
  const trace=$("motion-trace"), ctx=trace.getContext("2d");
  const mid=trace.height/2, step=trace.width/64;
  const samples=Array.from({length:65},(_,column)=>study.frames[position+column-32]?.[key]);
  const peak=Math.max(1,...samples.flatMap(row=>row?[Math.abs(row[0]),Math.abs(row[1])]:[]));
  ctx.clearRect(0,0,trace.width,trace.height);
  ctx.strokeStyle="#627d84";
  ctx.beginPath();ctx.moveTo(0,mid);ctx.lineTo(trace.width,mid);
  ctx.moveTo(trace.width/2,0);ctx.lineTo(trace.width/2,trace.height);ctx.stroke();
  for(const [axis,color] of ["#92ead4","#e9bb7e"].entries()) {
    let visible=false;
    ctx.strokeStyle=color;ctx.beginPath();
    samples.forEach((row,i)=>{
      if(!row) {visible=false;return;}
      const x=i*step,y=mid-row[axis]*.42*trace.height/peak;
      if(visible)ctx.lineTo(x,y);
      else ctx.moveTo(x,y);
      visible=true;
    });
    ctx.stroke();
  }
  const sample=samples[32], model=study.models[key];
  $("motion-trace-value").value=(sample?"X "+sample[0].toFixed(2)+" px · Y "+sample[1].toFixed(2)+" px":
    "No reliable sample at this frame")+(model?.supported?" · Live fit passed holdout":"");
}

function seek(index) {
  secondary?.clear();
  pendingFrame=null;
  const target=clamp(Math.round(index),0,limit);
  video.pause();
  requested=target;
  const period = target < limit ? frameTime(target+1)-frameTime(target) : 1/fps;
  video.currentTime=playbackStart+frameTime(target)+.23*period;
  if(target===position&&!video.seeking) {
    requested=null;
    changed=true;
  }
}
function step(direction) {seek((requested??position)+direction);}
function cue(direction) {
  const shot=clamp(currentShot()+direction,0,cuts.length-1);
  seek(cuts[shot][0]);
}
function playPause() {
  if(video.paused) {
    if(position>=limit)video.currentTime=playbackStart;
    video.play().catch(()=>failed("Use Play video to activate playback."));
  } else video.pause();
}
function reset() { motion.reset();secondary?.clear();changed=true;display(); }
function jump() { motion.jump();changed=true; }
function choose(which) {motion.choose(which);display();}

$("play").onclick=playPause;
$("previous-frame").onclick=()=>step(-1);
$("next-frame").onclick=()=>step(1);
$("playback-speed").onchange=event=>{video.playbackRate=Number(event.target.value);};
$("jump").onclick=jump;
for(const button of document.querySelectorAll("[data-direction]")) {
  const stop=event=>pointerDirections.delete(event.pointerId);
  button.onpointerdown=event=>{
    button.setPointerCapture(event.pointerId);
    pointerDirections.set(event.pointerId,button.dataset.direction);
  };
  button.onpointerup=button.onpointercancel=button.onlostpointercapture=stop;
  const activate=event=>{
    if(!["Space","Enter"].includes(event.code))return;
    event.preventDefault();
    if(event.type==="keydown")keys.add(button.dataset.direction);
    else keys.delete(button.dataset.direction);
  };
  button.onkeydown=button.onkeyup=activate;
  button.onblur=()=>keys.delete(button.dataset.direction);
}
$("reset").onclick=reset;
menu.onchange=()=>choose(Number(menu.value));
slider.oninput=()=>seek(Number(slider.value));
for(const button of document.querySelectorAll("[data-frame]")) button.onclick=()=>seek(Number(button.dataset.frame));
knobs.forEach((input,i)=>input.oninput=()=>{motion.position(i,Number(input.value));changed=true;});
video.addEventListener("seeked",()=>{accept(requested??frameIndex(video.currentTime));});
video.addEventListener("loadeddata",()=>accept(frameIndex(video.currentTime)));
for(const event of ["pause","play","ended"]) video.addEventListener(event,()=>{changed=true;display();});
video.addEventListener("error",()=>failed("The selected video could not play."));
function videoFrame(_,metadata) {
  const index=frameIndex(metadata.mediaTime);
  if(requested===null||requested===index)accept(index);
  video.requestVideoFrameCallback(videoFrame);
}
if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(videoFrame);
else video.addEventListener("timeupdate",()=>accept(frameIndex(video.currentTime)));

const keyboard={
  KeyW:1,KeyA:1,KeyS:1,KeyD:1,ArrowLeft:1,ArrowRight:1,ArrowUp:1,ArrowDown:1,
  Space:1,KeyQ:1,KeyE:1,KeyP:1,KeyR:1,
};
window.addEventListener("keydown",event=>{
  if($("stage-viewport").dataset.facePreview || event.target.closest("input,select,button,video,summary,.face-target-picker")||!keyboard[event.code])return;
  event.preventDefault();
  keys.add(event.code);
  if(event.repeat)return;
  if(event.code==="Space")jump();
  if(event.code==="KeyR")reset();
  if(event.code==="KeyP")playPause();
  if(event.code==="KeyQ")choose(motion.selected-1);
  if(event.code==="KeyE")choose(motion.selected+1);
});
window.addEventListener("keyup",event=>keys.delete(event.code));
window.addEventListener("blur",()=>{keys.clear();pointerDirections.clear();stamp=null;elapsed=0;});

function getPad() {
  try {
    const pads=Array.from(navigator.getGamepads?.()||[]).filter(p=>p?.connected&&p.mapping==="standard"&&p.axes.length>=4);
    const current=pads.find(p=>p.index===padIndex);
    const used=p=>p.axes.some(a=>Math.abs(a)>.18)||p.buttons.some(b=>b.pressed);
    return current&&used(current)?current:(pads.find(used)||current||pads[0]);
  } catch { return null; }
}
function input() {
  const held=code=>keys.has(code)||Array.from(pointerDirections.values()).includes(code);
  const key=(yes,no)=>Number(held(yes))-Number(held(no));
  const drive=[key("KeyD","KeyA"),key("KeyS","KeyW"),key("ArrowRight","ArrowLeft"),key("ArrowDown","ArrowUp"),0];
  const pad=getPad();
  if(!pad) {
    if(padIndex!==null) {
      padIndex=null;pressed=[];
      $("pad").textContent="Controller disconnected. Reconnect or use the keyboard.";
    }
    return drive;
  }
  const levels=pad.buttons.map(b=>b.pressed||b.value>.75);
  if(pad.index!==padIndex) {
    const wake=padIndex===null;
    padIndex=pad.index;
    pressed=wake?levels:[];
    $("pad").textContent="Xbox-style controller connected";
  }
  const edge=(n)=>levels[n]&&!pressed[n];
  if(edge(0))jump();
  if(edge(1))reset();
  if(edge(3))playPause();
  if(edge(4))choose(motion.selected-1);
  if(edge(5))choose(motion.selected+1);
  if(edge(12))cue(-1);
  if(edge(13))cue(1);
  if(edge(14))step(-1);
  if(edge(15))step(1);
  pressed=levels;
  for(let i=0;i<4;i++) {
    const axis=pad.axes[i];
    const value=Math.abs(axis)<.16?0:Math.sign(axis)*(Math.abs(axis)-.16)/.84;
    if(Math.abs(value)>Math.abs(drive[i]))drive[i]=value;
  }
  drive[4]=(pad.buttons[7]?.value||0)-(pad.buttons[6]?.value||0);
  return drive;
}

let poseKey="";
function animate(now) {
  requestAnimationFrame(animate);
  if(document.hidden) {stamp=null;elapsed=0;return;}
  const dt=stamp===null?0:clamp((now-stamp)/1000,0,.05);
  stamp=now;
  const drive=input();
  if(!ready)return;
  elapsed+=dt;
  const before=renderer.baseAt(position)[0];
  while(elapsed>=STEP) {
    motion.tick(STEP,drive,before,renderer.timeline.frames[position][0],renderer.timeline.height,
      renderer.timeline.travelY?.[currentShot()],renderer.timeline.rootLimit);
    elapsed-=STEP;
  }
  const state=motion.snapshot();
  const adjustments=inspector?.adjustments??{};
  const cleaned=inspector?.cleanup()??false;
  const physics=$("soft-physics").checked;
  const poseActive=motion.active();
  const active=poseActive||Object.keys(adjustments).length>0||tone.some(Boolean)||colored();
  secondary?.tick(dt,position,before,state,poseActive);
  const useRecorded=secondary?.enabled??false;
  const response=useRecorded?secondary.result:{};
  const observation=useRecorded?study.frames[position]:null;
  if(splatPreview&&$("show-splats").checked&&splatFrame!==position) {
    splatPoints=splatPreview.draw(position);
    splatFrame=position;
  }
  const key=active?JSON.stringify([state.root,state.lift,state.offsets,state.gait,state.gait>0?state.phase:0,adjustments,tone,cleaned,useRecorded,response,physics,colors]):"neutral";
  if(changed||key!==poseKey) {
    renderer.draw(state,poseActive,adjustments,tone,cleaned,response,observation,points,physics,colors);
    inspector?.render();
    syncPointControls();
    changed=false;
    poseKey=key;
    display();
  }
  if(secondary) {
    renderTrace();
    const view=secondary.inspect(position);
    const status=$("motion-study-status");
    const note=view.active?"Response "+view.amplitude.toFixed(2)+" source px · "+view.regions.length+" regions":
      view.eligibleRegions+" measured fits ready";
    if(status.value!==note)status.value=note;
  }
}

window.movementReview={
  seekSeconds:seconds=>seek(frameIndex(seconds)),
  inspect:()=>({ready,padIndex,position,shot:currentShot(),paused:video.paused,motion:motion.snapshot(),render:renderer?.inspect(),inspection:inspector?.snapshot(),tone:[...tone],
    stageZoom:stageZoom.snapshot(),points:structuredClone(points),
    secondary:secondary?.inspect(position)??{enabled:false,active:false,frame:position,regions:[],amplitude:0,eligibleRegions:0},
    splats:{available:splatsAvailable,visible:Boolean(splatPreview&&$("show-splats").checked),frame:splatFrame,points:splatPoints}
  }),
};

try {
  const quality=$("toggle-quality");
  quality.href=(useUhd?"/":"/?quality=4k")+location.hash;
  quality.textContent=useUhd?"Use native resolution":"Use 4K controls";
  renderer=await createRenderer(canvas,useUhd);
  $("tone-panel").hidden=!renderer.hasSkin;
  // Hair needs the segmentation masks; facial features need tracked mesh polygons.
  const facialColors=Boolean(renderer.augmentation?.colorAreas?.some(Boolean));
  for(const [key,{row}] of Object.entries(colorInputs))
    row.hidden=key==="hair"?!renderer.hasSkin:!facialColors;
  $("color-panel").hidden=!renderer.hasSkin&&!facialColors;
  study=await fetch("/motion-study.json").then(r=>r.ok?r.json():null);
  if(study&&study.frames.length===renderer.timeline.frames.length) {
    secondary=new SecondaryMotion(study);
    $("motion-study-panel").hidden=false;
    $("motion-traces").hidden=false;
    const observedRegions=new Set(study.frames.flatMap(row=>Object.keys(row)));
    for(const key of [...observedRegions].sort())
      $("motion-region").add(new Option(renderer.augmentation?.parts?.[key]??key,key));
    if(secondary.entries.length)$("motion-region").value=secondary.entries[0].key;
    $("motion-region").onchange=()=>$("motion-traces").open&&renderTrace(true);
    $("motion-traces").ontoggle=()=>renderTrace(true);
    $("recorded-motion").onchange=()=>{
      secondary.enable($("recorded-motion").checked);
      changed=true;
    };
  }
  fetch("/motion-splats.json",{method:"HEAD"}).then(r=>{
    splatsAvailable=r.ok;
    if(!splatsAvailable)return;
    $("motion-study-panel").hidden=false;
    $("splat-option").hidden=false;
  }).catch(()=>{});
  $("show-splats").onchange=async()=>{
    const control=$("show-splats"), preview=$("splat-preview");
    preview.hidden=!control.checked;
    if(!control.checked||splatPreview||splatLoading)return;
    splatLoading=true;
    try {
      const [module,data]=await Promise.all([import("./splats.mjs"),
        fetch("/motion-splats.json").then(r=>{if(!r.ok)throw new Error("Missing track");return r.json();})]);
      splatPreview=module.createSplatPreview(preview,data);
      splatFrame=-1;
    } catch {
      control.checked=false;
      preview.hidden=true;
      $("motion-study-status").value="Gaussian tracks could not be loaded.";
    } finally {splatLoading=false;}
  };
  inspector=createInspector(canvas,renderer,()=>video.pause(),()=>{
    changed=true;
    syncPointControls();
  },()=>video.paused&&!motion.active(),{
    pointEdit:createPoint,isPointMode:()=>pointMode.getAttribute("aria-pressed")==="true",
  });
  const shared=new URLSearchParams(location.hash.slice(1)).get("edit");
  if(shared) {
    try {
      const preset=JSON.parse(shared);
      if(preset?.version===1) {
        for(const [key,point] of Object.entries(preset.points??{}))
          if(/^point-[1-9]\d*$/.test(key)&&validPoint(point,renderer.augmentation?.parts??{}))registerPoint(key,point);
        inspector.restore?.(preset);
        const presetColors=validColors(preset.colors);
        for(const [key,[value,strength]] of Object.entries(presetColors??{})) {
          colorInputs[key].picker.value=value;colorInputs[key].strength.value=strength;colorInputs[key].update();
        }
        if(Array.isArray(preset.tone)&&preset.tone.length===3)
          toneInputs.forEach((input,index)=>{
            if(Number.isFinite(preset.tone[index])) {input.value=preset.tone[index];input.oninput();}
          });
      }
    } catch {
      // Invalid review links open the neutral state.
    }
  }
  if (useUhd) {
    $("loading").textContent = "Preparing and verifying 4K playback…";
    const bar = progressBar($("loading"), "4K build progress");
    bar.show(null);
    try {
      await ensureUhd(progress => bar.show(progress));
    } finally {
      bar.remove();
    }
  }
  video.src=useUhd?"/4k.mp4":"/video.mp4";
  ({fps,shots:cuts,playbackStart=0,frameTimes=null}=renderer.timeline);
  renderer.setPageReady(error=>{
    if(error) {$("motion-state").textContent="Pose layer unavailable";return;}
    if(video.paused&&!video.seeking)accept(pendingFrame??position);
  });
  limit=renderer.timeline.frames.length-1; slider.max=limit;
  $("download-edited").disabled = false;
  if(cuts.length>1)cuts.forEach(([start],i)=>{const button=document.createElement("button");button.textContent="Shot "+(i+1);button.onclick=()=>seek(start);document.querySelector(".shots").append(button);});
  accept(frameIndex(video.currentTime));
  requestAnimationFrame(animate);
} catch(e) {
  failed(e.message);
}
