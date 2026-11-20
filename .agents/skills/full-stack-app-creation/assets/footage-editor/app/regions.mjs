// Oriented support ellipses are fitted in Python and use native source pixels.
// Positive dimensions spread content along the corresponding region axes.
export function influence(x,y,[cx,cy,ux,uy,rx,ry]) {
  const dx=x-cx, dy=y-cy;
  const across=dx*ux+dy*uy, along=dy*ux-dx*uy;
  const distance=(across/rx)**2+(along/ry)**2;
  return {across,along,distance};
}

export function deformation(x,y, regions, adjustments) {
  let dx=0,dy=0;
  for(const [key, shapes] of Object.entries(regions)) {
    const adjustment=adjustments[key];
    if(!adjustment)continue;
    const [width,height]=adjustment;
    for(const shape of shapes) {
      if(!shape)continue;
      const {across,along,distance}=influence(x,y,shape);
      if(distance>=1)continue;
      const [, ,ux,uy]=shape, falloff=(1-distance)**2;
      const a=across*width*falloff, b=along*height*falloff;
      dx+=a*ux-b*uy;
      dy+=a*uy+b*ux;
    }
  }
  return [x+dx,y+dy];
}

const facial=new Set(["left-eye","right-eye","left-brow","right-brow","nose","mouth","chin"]);
export function hitRegion(x,y,regions,{accept=()=>true,detail=false}={}) {
  let hit=null, best=Infinity;
  for(const [key, shapes] of Object.entries(regions).filter(([key])=>accept(key)))
    for(const [index,shape] of shapes.entries()) {
      if(!shape)continue;
      const {distance}=influence(x,y,shape);
      // A tight facial landmark wins against the broad head envelope.
      const score=distance-(facial.has(key)?.17:0)+(detail?.12*Math.log1p(shape[4]*shape[5]):0);
      if(distance<.83&&score<best) {best=score;hit={key,index};}
    }
  return hit;
}


const trunkParents={
  shoulders:"torso",chest:"torso","left-breast":"chest","right-breast":"chest",
  hips:"torso","left-hip":"hips","right-hip":"hips",buttocks:"hips",
  "left-buttock":"buttocks","right-buttock":"buttocks",
};
export function parentRegion(key, parents={}) {
  if(key&&Object.hasOwn(parents,key))return parents[key];
  if(facial.has(key))return "head";
  if(trunkParents[key])return trunkParents[key];
  if(!key)return "";
  const [side,part]=key.split("-");
  if(!["left","right"].includes(side))return "";
  if(part==="calf")return side+"-leg";
  if(part==="hand")return side+"-arm";
  if(["thumb","index","middle","ring","pinky"].includes(part))return side+"-hand";
  return "";
}

export function regionPath(key, parents) {
  const path=[];
  for(let part=key;part&&!path.includes(part);part=parentRegion(part,parents))path.unshift(part);
  return path;
}
