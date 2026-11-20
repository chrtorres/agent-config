import {parentRegion,regionPath} from "./regions.mjs";
import {pickRegion} from "./picking.mjs";

export function createInspector(stage, renderer, pause, changed, canMark=()=>true,
  {pointEdit, isPointMode=()=>false}={}) {
  const $=id=>document.getElementById(id);
  const panel=$("inspection"), menu=$("feature"), notice=$("feature-status");
  const magnifier=$("magnifier"), context=magnifier.getContext("2d");
  const marker=$("feature-marker"), markerLabel=$("feature-marker-label");
  const zoom=$("feature-zoom"), values=[$("feature-width"),$("feature-height")];
  const adjustments={};
  let selected=null,crop=null,cleaned=false;
  const parts=renderer.augmentation?.parts;
  if(!parts)return {adjustments,cleanup:()=>false,render(){},snapshot:()=>null,
    current:()=>null,select(){},registerPoint(){},removePoint(){},invalidateCleanup(){}};
  const available=Object.assign(Object.create(null),parts);
  const parents=renderer.augmentation.parents;
  const pathTo=key=>regionPath(key,parents);
  const parentOf=key=>parentRegion(key,parents);
  panel.hidden=false;
  stage.classList.add("can-inspect");
  for(const [key,label] of Object.entries(available))menu.add(new Option(label,key));
  const set=(key,index=0)=>{
    selected=available[key]?{key,index}:null;
    menu.value=selected?.key??"";
    const path=pathTo(selected?.key).filter(part=>available[part]);
    $("feature-path").textContent=path.map(part=>available[part]).join(" › ");
    const parent=path.at(-2);
    $("feature-parent").hidden=!parent;
    $("feature-parent").textContent=parent?"Zoom out to "+available[parent]:"";
    $("feature-parent").onclick=parent?()=>{zoom.value=1;set(parent);}:null;
    syncControls();
    render();
    changed();
  };
  function registerPoint(key,label) {
    if(Object.hasOwn(available,key))return;
    available[key]=label;
    menu.add(new Option(label,key));
  }
  function removePoint(key) {
    if(Object.hasOwn(parts,key)||!Object.hasOwn(available,key))return;
    delete available[key];
    delete adjustments[key];
    Array.from(menu.options).find(option=>option.value===key)?.remove();
    if(selected?.key===key)set(null);
    shapeChanged();
  }
  function syncControls() {
    const value=adjustments[selected?.key]??[0,0];
    for(const [index,input] of values.entries()) {
      input.value=value[index]*100;
      input.disabled=!selected;
      $(input.id+"-value").value=Math.round(value[index]*200)/2+"%";
    }
    $("feature-reset").disabled=!selected;
    const hasShapes=Object.keys(adjustments).length>0;
    $("feature-reset-all").disabled=!hasShapes;
    $("clean-image").disabled=!hasShapes||cleaned;
    $("undo-cleanup").hidden=!cleaned;
    if(!cleaned)$("cleanup-status").value="";
    zoom.disabled=!selected;
  }
  menu.onchange=()=>set(menu.value);
  zoom.oninput=render;
  for(const [index,input] of values.entries()) input.oninput=()=>{
    if(!selected)return;
    const dimensions=[...(adjustments[selected.key]??[0,0])];
    dimensions[index]=Number(input.value)/100;
    if(dimensions.some(Boolean))adjustments[selected.key]=dimensions;
    else delete adjustments[selected.key];
    shapeChanged();
  };
  function shapeChanged() {
    cleaned=false;
    syncControls();
    changed();
  }
  $("feature-reset").onclick=()=>{
    if(selected&&Object.hasOwn(adjustments,selected.key)) {
      delete adjustments[selected.key];
      shapeChanged();
    }
  };
  $("feature-reset-all").onclick=()=>{
    for(const key of Object.keys(adjustments))delete adjustments[key];
    shapeChanged();
  };
  $("clean-image").onclick=()=>{
    cleaned=true;
    syncControls();
    changed();
  };
  $("undo-cleanup").onclick=()=>{
    cleaned=false;
    syncControls();
    changed();
  };
  function stagePoint(event) {
    const bounds=stage.getBoundingClientRect();
    const {width,height}=renderer.inspect();
    if(!width||!height||!bounds.width||!bounds.height)return null;
    const scale=width/bounds.width;
    const x=(event.clientX-bounds.left)*scale;
    const y=(event.clientY-bounds.top)*height/bounds.height;
    return x>=0&&x<width&&y>=0&&y<height?{x,y,scale}:null;
  }
  function lensPoint(event) {
    if(!crop||!selected)return null;
    const bounds=magnifier.getBoundingClientRect();
    if(!bounds.width||!bounds.height)return null;
    const scale=crop.width/bounds.width;
    const x=crop.left+(event.clientX-bounds.left)*scale;
    const y=crop.top+(event.clientY-bounds.top)*crop.height/bounds.height;
    return {x,y,scale};
  }
  function pick(point,inLens) {
    if(!point||!renderer.isForeground(point.x,point.y))return null;
    if(!inLens)return pickRegion(point,renderer.regions());
    const details=key=>pathTo(key).slice(0,-1).includes(selected.key);
    const siblings=key=>key!==selected.key&&parentOf(key)===parentOf(selected.key);
    return pickRegion(point,renderer.regions(),details)||
      (parentOf(selected.key)&&pickRegion(point,renderer.regions(),siblings));
  }
  function wirePicker(canvas,toPoint,inLens=false) {
    canvas.addEventListener("pointermove",event=>{
      const point=toPoint(event);
      const over=isPointMode()?point&&renderer.isForeground(point.x,point.y):pick(point,inLens);
      canvas.classList.toggle("feature-hit",Boolean(over));
    });
    canvas.addEventListener("pointerleave",()=>canvas.classList.remove("feature-hit"));
    canvas.addEventListener("click",event=>{
      const point=toPoint(event);
      if(isPointMode()) {
        if(!point||!pointEdit?.(point.x,point.y))notice.textContent="Choose a visible area on the performer.";
        return;
      }
      const hit=pick(point,inLens);
      if(hit) {
        pause();
        set(hit.key,hit.index);
      } else if(!inLens) {
        notice.textContent=point&&renderer.isForeground(point.x,point.y)?
          "Use Pick custom area for this point.":"No tracked feature at that point.";
      }
    });
  }
  wirePicker(stage,stagePoint);
  wirePicker(magnifier,lensPoint,true);
  magnifier.addEventListener("wheel",event=>{
    if(!selected||magnifier.hidden)return;
    event.preventDefault();
    zoom.value=Math.max(1,Math.min(6,Number(zoom.value)+(event.deltaY<0?.25:-.25)));
    render();
  },{passive:false});
  new ResizeObserver(render).observe(stage);
  function visibleShape() {
    const shape=renderer.regions()[selected?.key]?.[selected.index];
    const bounds=renderer.inspect();
    return shape&&shape[0]>=0&&shape[0]<bounds.width&&shape[1]>=0&&shape[1]<bounds.height?shape:null;
  }
  function render() {
    if(cleaned) {
      const visible=Object.keys(adjustments).some(key=>renderer.regions()[key]?.some(Boolean));
      const {cleanupEffect,attachedCleanup}=renderer.inspect();
      $("cleanup-status").value=cleanupEffect>.045?
        (attachedCleanup?"Cleanup applied with joint tracking":"Cleanup applied to visible edits"):
        visible?"No strong or overlapping edit to smooth in this frame":"Adjusted features are outside the tracked view";
    }
    const shape=visibleShape();
    marker.hidden=!shape||!canMark();
    magnifier.hidden=!shape;
    $("feature-zoom-value").value=Number(zoom.value).toFixed(1)+"×";
    if(!shape) {
      crop=null;
      notice.textContent=selected?"Feature outside the tracked view at this frame.":"Click a feature in the video or select it below.";
      return;
    }
    notice.textContent=available[selected.key]+" tracked";
    const [x,y,ux,uy,rx,ry]=shape;
    const {width,height}=renderer.inspect();
    const sx=stage.clientWidth/width, sy=stage.clientHeight/height;
    marker.style.left=x*sx+"px";
    marker.style.top=y*sy+"px";
    marker.style.width=`max(calc(10px / var(--stage-scale, 1)), ${rx*1.5*sx}px)`;
    marker.style.height=`max(calc(10px / var(--stage-scale, 1)), ${ry*1.5*sy}px)`;
    marker.style.transform="translate(-50%,-50%) rotate("+Math.atan2(uy,ux)+"rad)";
    markerLabel.textContent=available[selected.key];
    markerLabel.style.rotate=-Math.atan2(uy,ux)+"rad";
    // Read the rendered stage so the magnifier shows the current edit and pose.
    const raster=stage.width/width, aspect=magnifier.width/magnifier.height;
    const scale=Number(zoom.value);
    let centerX=x, centerY=y, extent=Math.max(25,rx*2.8,ry*2.8*aspect);
    if(scale===1) {
      // The overview includes other visible segments and descendants so a
      // straight arm can be followed to a hand even when its wrist is distant.
      const related=Object.entries(renderer.regions()).filter(([key])=>pathTo(key).includes(selected.key))
        .flatMap(([,items])=>items)
        .filter(part=>part&&part[0]>=0&&part[0]<width&&part[1]>=0&&part[1]<height);
      if(related.length>1) {
        const xs=related.map(([x,,ux,uy,rx,ry])=>[x,Math.hypot(ux*rx,uy*ry)]);
        const ys=related.map(([,y,ux,uy,rx,ry])=>[y,Math.hypot(uy*rx,ux*ry)]);
        const bounds=rows=>[
          Math.min(...rows.map(([center,radius])=>center-.64*radius)),
          Math.max(...rows.map(([center,radius])=>center+.64*radius))
        ];
        const [l,r]=bounds(xs), [t,b]=bounds(ys);
        centerX=(l+r)/2;centerY=(t+b)/2;
        extent=Math.max(extent,(r-l)*1.15,(b-t)*1.15*aspect);
      }
    }
    const boxWidth=Math.min(width,height*aspect,extent)/scale;
    const boxHeight=boxWidth/aspect;
    const left=Math.max(0,Math.min(width-boxWidth,centerX-boxWidth/2));
    const top=Math.max(0,Math.min(height-boxHeight,centerY-boxHeight/2));
    crop={left,top,width:boxWidth,height:boxHeight};
    context.drawImage(stage,left*raster,top*raster,boxWidth*raster,boxHeight*raster,
      0,0,magnifier.width,magnifier.height);
  }
  syncControls();
  function restore(preset) {
    for(const [key,values] of Object.entries(preset.shapes??{})) {
      if(available[key]&&Array.isArray(values)&&values.length===2&&values.some(Boolean)&&
         values.every(v=>Number.isFinite(v)&&v>=-70&&v<=110))
        adjustments[key]=values.map(v=>v/100);
    }
    cleaned=preset.cleanup===true&&Object.keys(adjustments).length>0;
    zoom.value=Number.isFinite(preset.zoom)?Math.max(1,Math.min(6,preset.zoom)):1;
    if(available[preset.feature])set(preset.feature);
    syncControls();
    changed();
  }
  return {adjustments,cleanup:()=>cleaned,render,restore,select:set,current:()=>selected?.key??null,
    registerPoint,removePoint,invalidateCleanup:shapeChanged,snapshot:()=>({selected,cleanup:cleaned,zoom:Number(zoom.value),
      available:Boolean(visibleShape()),crop:crop&&{...crop},adjustments:structuredClone(adjustments)})};
}
