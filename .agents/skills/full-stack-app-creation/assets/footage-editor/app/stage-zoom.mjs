const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));

export function createStageZoom(canvas) {
  const viewport=canvas.closest("#stage-viewport");
  const content=canvas.closest("#stage-content");
  const control=document.getElementById("stage-zoom");
  const value=document.getElementById("stage-zoom-value");
  const reset=document.getElementById("stage-zoom-reset");
  const controls=document.getElementById("stage-zoom-controls");
  let scale=1,x=0,y=0,width=0,height=0,drag=null,suppressClick=false;

  function paint() {
    x=clamp(x,width*(1-scale),0);
    y=clamp(y,height*(1-scale),0);
    // Transform the canvas and its selection guide together while leaving the
    // rendered video raster available at its original size to the inspector.
    content.style.transform=scale===1?"":`translate(${x}px, ${y}px) scale(${scale})`;
    content.style.setProperty("--stage-scale",scale);
    viewport.classList.toggle("is-zoomed",scale>1);
    control.value=scale;
    value.value=scale+"×";
    reset.disabled=scale===1;
  }

  function zoomTo(target,anchorX=width/2,anchorY=height/2) {
    const next=clamp(Math.round(target*10)/10,Number(control.min),Number(control.max));
    const ratio=next/scale;
    x=anchorX-(anchorX-x)*ratio;
    y=anchorY-(anchorY-y)*ratio;
    scale=next;
    paint();
  }

  new ResizeObserver(()=>{
    const nextWidth=content.clientWidth,nextHeight=content.clientHeight;
    if(!nextWidth||!nextHeight)return;
    // Keep the same normalized point in view as the stage adapts to the layout.
    if(width&&height) {
      x*=nextWidth/width;
      y*=nextHeight/height;
    }
    width=nextWidth;
    height=nextHeight;
    paint();
  }).observe(content);

  control.addEventListener("input",()=>zoomTo(Number(control.value)));
  reset.addEventListener("click",()=>zoomTo(1));
  viewport.addEventListener("wheel",event=>{
    if((!event.ctrlKey&&!event.metaKey)||!event.deltaY)return;
    event.preventDefault();
    const rect=viewport.getBoundingClientRect();
    const unit=event.deltaMode===1?16:event.deltaMode===2?height:1;
    zoomTo(scale*Math.exp(-event.deltaY*unit*.0025),
      event.clientX-rect.left-content.offsetLeft,event.clientY-rect.top-content.offsetTop);
  },{passive:false});

  viewport.addEventListener("pointerdown",event=>{
    if(!event.isPrimary||event.button!==0)return;
    suppressClick=false;
    if(scale>1)drag={id:event.pointerId,left:event.clientX,top:event.clientY,x,y,started:false};
  });
  viewport.addEventListener("pointermove",event=>{
    if(drag?.id!==event.pointerId)return;
    const dx=event.clientX-drag.left,dy=event.clientY-drag.top;
    if(!drag.started&&Math.hypot(dx,dy)<5)return;
    if(!drag.started) {
      viewport.setPointerCapture(event.pointerId);
      viewport.classList.add("is-panning");
      drag.started=true;
    }
    x=drag.x+dx;
    y=drag.y+dy;
    paint();
  });
  function finishPan(event) {
    if(drag?.id!==event.pointerId)return;
    suppressClick=drag.started;
    drag=null;
    viewport.classList.remove("is-panning");
  }
  viewport.addEventListener("pointerup",finishPan);
  viewport.addEventListener("pointercancel",finishPan);
  viewport.addEventListener("lostpointercapture",finishPan);
  viewport.addEventListener("pointerleave",event=>{
    if(!drag?.started)finishPan(event);
  });
  viewport.addEventListener("click",event=>{
    // Complete drags on this layer so the inspector receives only taps/clicks.
    if(!suppressClick||event.detail===0)return;
    suppressClick=false;
    event.preventDefault();
    event.stopImmediatePropagation();
  },true);
  viewport.addEventListener("keydown",event=>{
    if(scale===1||!event.altKey)return;
    const directions={ArrowLeft:[1,0],ArrowRight:[-1,0],ArrowUp:[0,1],ArrowDown:[0,-1]};
    const direction=directions[event.code];
    if(!direction)return;
    event.preventDefault();
    event.stopPropagation();
    x+=direction[0]*width*.12;
    y+=direction[1]*height*.12;
    paint();
  });
  controls.hidden=false;
  return {snapshot:()=>({scale,x,y})};
}
