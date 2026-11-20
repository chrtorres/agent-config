const clamp=(n,lo,hi)=>Math.min(hi,Math.max(lo,n));
export const pointRadius=[4,100];

export function validPoint(point,parts) {
  return point&&Object.hasOwn(parts,point.anchor)&&Number.isInteger(point.segment)&&point.segment>=0&&
    Number.isFinite(point.across)&&Number.isFinite(point.along)&&Number.isFinite(point.area)&&point.area>0&&
    Number.isFinite(point.radius)&&point.radius>=pointRadius[0]&&point.radius<=pointRadius[1];
}

export function anchorPoint(x,y,areas) {
  let best=Infinity, point=null;
  for(const [anchor,shapes] of Object.entries(areas)) {
    for(const [segment,shape] of shapes.entries()) {
      if(!shape)continue;
      const [cx,cy,ux,uy,rx,ry]=shape;
      const dx=x-cx,dy=y-cy;
      const across=(dx*ux+dy*uy)/rx, along=(dy*ux-dx*uy)/ry;
      // Favor a nearby tracked detail over a much larger overlapping region.
      const score=Math.hypot(dx,dy)+.3*Math.min(rx,ry)+18*Math.max(0,Math.hypot(across,along)-1);
      if(score>=best)continue;
      best=score;
      point={anchor,segment,across,along,area:rx*ry,radius:clamp(Math.round(.65*Math.min(rx,ry)),6,24)};
    }
  }
  return point;
}

export function pointShape(point,areas) {
  const shape=areas[point.anchor]?.[point.segment];
  if(!shape)return null;
  const [cx,cy,ux,uy,rx,ry]=shape;
  const a=point.across*rx,b=point.along*ry;
  const radius=point.radius*clamp(Math.sqrt(rx*ry/point.area),.45,2);
  return [cx+a*ux-b*uy,cy+a*uy+b*ux,ux,uy,radius,radius];
}
