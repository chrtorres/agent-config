// Color controls for hair and facial features. tools/colors.py mirrors the
// dye math and mask drawing so the export matches the preview.
export const COLOR_TARGETS=["hair","lips","eyes","brows"];
export const COLOR_LABELS={hair:"Hair",lips:"Lips",eyes:"Eyes",brows:"Eyebrows"};

export function hexColor(value) {
  const match=/^#([0-9a-f]{6})$/i.exec(value??"");
  if(!match)return null;
  const number=parseInt(match[1],16);
  return [(number>>16)/255,((number>>8)&255)/255,(number&255)/255];
}

// [r,g,b,strength] in 0..1, or zeros when the target is not dyed.
export function tint(entry) {
  const color=hexColor(entry?.[0]), strength=Number(entry?.[1]);
  if(!color||!Number.isFinite(strength)||strength<=0)return [0,0,0,0];
  return [...color,Math.min(100,strength)/100];
}

export function validColors(colors) {
  if(colors==null)return {};
  if(typeof colors!=="object")return null;
  const result={};
  for(const [key,entry] of Object.entries(colors)) {
    if(!COLOR_TARGETS.includes(key)||!Array.isArray(entry)||entry.length!==2||!hexColor(entry[0])||
       !Number.isFinite(entry[1])||entry[1]<0||entry[1]>100)return null;
    if(entry[1]>0)result[key]=[entry[0].toLowerCase(),entry[1]];
  }
  return result;
}

// Feature mask in source pixels: red lips (without the mouth opening), green
// irises inside the eye opening, blue brows. A small blur feathers the edges.
export function drawFeatureMask(context,areas,width,height) {
  context.save();
  context.setTransform(1,0,0,1,0,0);
  context.globalCompositeOperation="copy";
  context.fillStyle="#000";
  context.fillRect(0,0,width,height);
  if(!areas){context.restore();return false;}
  const path=points=>{
    const shape=new Path2D();
    points.forEach(([x,y],index)=>index?shape.lineTo(x,y):shape.moveTo(x,y));
    shape.closePath();
    return shape;
  };
  context.filter="blur(0.8px)";
  context.globalCompositeOperation="lighter";
  const lips=new OffscreenCanvas(width,height), lipContext=lips.getContext("2d");
  lipContext.fillStyle="#f00";
  lipContext.fill(path(areas.lips));
  lipContext.globalCompositeOperation="destination-out";
  lipContext.fill(path(areas.mouth));
  context.drawImage(lips,0,0);
  for(const [index,eye] of (areas.eyes??[]).entries()) {
    const iris=areas.irises?.[index];
    if(!iris)continue;
    context.save();
    context.clip(path(eye));
    context.fillStyle="#0f0";
    context.beginPath();
    context.arc(iris[0],iris[1],iris[2],0,2*Math.PI);
    context.fill();
    context.restore();
  }
  context.fillStyle="#00f";
  for(const brow of areas.brows??[])context.fill(path(brow));
  context.restore();
  return true;
}
