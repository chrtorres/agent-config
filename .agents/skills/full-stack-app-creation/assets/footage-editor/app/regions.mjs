// Oriented support ellipses are fitted in Python and use native source pixels.
// Positive dimensions spread content along the corresponding region axes.
export function influence(x,y,[cx,cy,ux,uy,rx,ry]) {
  const dx=x-cx, dy=y-cy;
  const across=dx*ux+dy*uy, along=dy*ux-dx*uy;
  const distance=(across/rx)**2+(along/ry)**2;
  return {across,along,distance};
}

// A shape edit scales the whole part uniformly about its tracked center, the
// way a genuinely larger or smaller part would look. The earlier kernel faded
// the scale continuously from the center, which magnified the middle and
// squeezed the rim like a lens. Here the part's interior keeps one scale and
// only the band beyond RING_START absorbs the change. The ring widens
// with the expansion so the surrounding area never folds (Jacobian stays above
// MIN_JACOBIAN). tools/cleanup.py mirrors these constants and formulas.
export const RING_START=.9;
const MIN_JACOBIAN=.3;
// In the ring the displacement magnitude falls from grow*RING_START to zero
// along a smoothstep whose steepest slope is 1.5/span, so the radial Jacobian
// is at least 1-1.5*grow*RING_START/span.
export function reach([width,height]) {
  const grow=Math.max(0,width,height);
  return RING_START+Math.max(.5,1.5*grow*RING_START/(1-MIN_JACOBIAN));
}

export function ringWeight(radius,outer) {
  if(radius<=RING_START)return 1;
  if(radius>=outer)return 0;
  const t=(radius-RING_START)/(outer-RING_START);
  return RING_START*(1-t*t*(3-2*t))/radius;
}

// Segments of one feature form one body part, so their weights are a
// partition rather than a sum: overlapping limb segments do not double the
// requested scale at the joint. Optional shape[6..7] is a soft-tissue offset
// in source pixels that moves the whole part with the same weight.
export function featureDisplacement(x,y,shapes,[width,height],mobility=1) {
  const outer=reach([width,height]);
  let dx=0,dy=0,total=0,complement=1;
  for(const shape of shapes) {
    if(!shape)continue;
    const [, ,ux,uy,rx,ry,ox=0,oy=0]=shape;
    const {across,along,distance}=influence(x,y,shape);
    const weight=ringWeight(Math.sqrt(distance),outer);
    if(weight<=0)continue;
    const a=across*width, b=along*height;
    dx+=weight*(a*ux-b*uy+ox);
    dy+=weight*(a*uy+b*ux+oy);
    total+=weight;complement*=1-weight;
  }
  const scale=mobility/Math.max(1,total);
  return [dx*scale,dy*scale,1-complement];
}

export function supportExtent(shape,adjustment) {
  const [x,y,ux,uy,rx,ry]=shape, outer=reach(adjustment);
  return [x,y,ux,uy,rx*outer,ry*outer];
}

export function deformation(x,y, regions, adjustments) {
  let dx=0,dy=0;
  for(const [key, shapes] of Object.entries(regions)) {
    const adjustment=adjustments[key];
    if(!adjustment)continue;
    const [fx,fy]=featureDisplacement(x,y,shapes,adjustment);
    dx+=fx;dy+=fy;
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
