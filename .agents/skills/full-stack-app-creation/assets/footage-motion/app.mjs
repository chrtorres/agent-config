import { Motion,PARTS } from "./motion.mjs";
import { createRenderer } from "./render.mjs";

const $=id=>document.getElementById(id);
const video=$("source"), canvas=$("screen"), slider=$("time"), menu=$("part");
const knobs=["joint-x","joint-y","joint-r"].map($);
const motion=new Motion(), keys=new Set();
let renderer=null, ready=false, changed=true, requested=null, position=0;
let padIndex=null, pressed=[], stamp=null, elapsed=0;
let limit=0, fps=30, cuts=[];
const STEP=1/120;
const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
const frameIndex=time=>clamp(Math.round(time*fps),0,limit);
const sceneOf=index=>Math.max(0,cuts.findIndex(([a,b])=>index>=a&&index<b));
const currentShot=()=>sceneOf(position);

for(const [value,name] of PARTS.entries()) menu.add(new Option(name,String(value)));
const failed=text=>{$("error").textContent=text;$("error").hidden=false;$("loading").hidden=true;};
function display() {
  const time=position/fps;
  $("clock").textContent=String(Math.floor(time/60))+":"+Number(time%60).toFixed(2).padStart(5,"0");
  if(document.activeElement!==slider)slider.value=position;
  $("play").textContent=video.paused?"Play video":"Pause video";
  $("resolution").textContent=canvas.width+" × "+canvas.height;
  menu.value=motion.selected;
  for(let i=0;i<3;i++) {
    if(document.activeElement!==knobs[i])knobs[i].value=motion.offsets[motion.selected][i];
  }
}

function accept(index) {
  if(!renderer?.frame(video,index))return;
  position=index;
  if(requested===index)requested=null;
  changed=true;
  ready=true;
  $("loading").hidden=true;
  display();
}

function seek(index) {
  const target=clamp(Math.round(index),0,limit);
  video.pause();
  requested=target;
  video.currentTime=(target+.23)/fps;
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
    if(position>=limit)video.currentTime=0;
    video.play().catch(()=>failed("Use Play video to activate playback."));
  } else video.pause();
}
function reset() { motion.reset();changed=true;display(); }
function jump() { motion.jump();changed=true; }
function choose(which) {motion.choose(which);display();}

$("play").onclick=playPause;
$("jump").onclick=jump;
$("reset").onclick=reset;
menu.onchange=()=>choose(Number(menu.value));
slider.oninput=()=>seek(Number(slider.value));
for(const button of document.querySelectorAll("[data-frame]")) button.onclick=()=>seek(Number(button.dataset.frame));
knobs.forEach((input,i)=>input.oninput=()=>{motion.position(i,Number(input.value));changed=true;});
video.addEventListener("seeked",()=>{accept(requested??frameIndex(video.currentTime));});
video.addEventListener("loadeddata",()=>accept(frameIndex(video.currentTime)));
for(const event of ["pause","play","ended"]) video.addEventListener(event,display);
video.addEventListener("error",()=>failed("The original video could not play."));
function videoFrame(_,metadata) {
  accept(frameIndex(metadata.mediaTime));
  video.requestVideoFrameCallback(videoFrame);
}
if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(videoFrame);
else video.addEventListener("timeupdate",()=>accept(frameIndex(video.currentTime)));

const keyboard={
  KeyW:1,KeyA:1,KeyS:1,KeyD:1,ArrowLeft:1,ArrowRight:1,ArrowUp:1,ArrowDown:1,
  Space:1,KeyQ:1,KeyE:1,KeyP:1,KeyR:1,
};
window.addEventListener("keydown",event=>{
  if(event.target.closest("input,select,button")||!keyboard[event.code])return;
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
window.addEventListener("blur",()=>{keys.clear();stamp=null;elapsed=0;});

function getPad() {
  try {
    const pads=Array.from(navigator.getGamepads?.()||[]).filter(p=>p?.connected&&p.mapping==="standard"&&p.axes.length>=4);
    const current=pads.find(p=>p.index===padIndex);
    const used=p=>p.axes.some(a=>Math.abs(a)>.18)||p.buttons.some(b=>b.pressed);
    return current&&used(current)?current:(pads.find(used)||current||pads[0]);
  } catch { return null; }
}
function input() {
  const key=(yes,no)=>Number(keys.has(yes))-Number(keys.has(no));
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
    motion.tick(STEP,drive,before,canvas.width,canvas.height,renderer.timeline.travelY?.[currentShot()]);
    elapsed-=STEP;
  }
  const state=motion.snapshot();
  const active=motion.active();
  const key=active?JSON.stringify([state.root,state.lift,state.offsets,state.gait,state.gait>0?state.phase:0]):"neutral";
  if(changed||key!==poseKey) {
    renderer.draw(state,active);
    changed=false;
    poseKey=key;
    display();
  }
}

window.movementReview={
  inspect:()=>({ready,padIndex,position,shot:currentShot(),paused:video.paused,motion:motion.snapshot(),render:renderer?.inspect()}),
};

try {
  renderer=await createRenderer(canvas);
  ({fps,shots:cuts}=renderer.timeline);
  limit=renderer.timeline.frames.length-1; slider.max=limit;
  cuts.forEach(([start],i)=>{const button=document.createElement("button");button.textContent="Shot "+(i+1);button.onclick=()=>seek(start);document.querySelector(".shots").append(button);});
  accept(frameIndex(video.currentTime));
  requestAnimationFrame(animate);
} catch(e) {
  failed(e.message);
}
