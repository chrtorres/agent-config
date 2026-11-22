import {deformation,featureDisplacement} from "./regions.mjs";

const OVERLAP_STRENGTH=1.35;
const STRONG_EDIT_RELIEF=.42;
const risk=([width,height])=>{
  const normalized=Math.min(1,Math.max(0,(Math.max(Math.abs(width),Math.abs(height))-.43)/.32));
  return normalized*normalized*(3-2*normalized);
};

// Count overlapping features rather than individual ellipses. Segments of
// the same tracked limb keep their original warp, including at their joint.
export function compileCleanup(regions, adjustments, pins={}) {
  const groups=[];
  for(const [key,shapes] of Object.entries(regions)) {
    const adjustment=adjustments[key];
    if(!adjustment?.some(Boolean))continue;
    const fields=shapes.filter(Boolean);
    if(fields.length)groups.push({fields,adjustment,risk:risk(adjustment),pins:pins[key]??[]});
  }
  if(groups.length<2&&!groups.some(group=>group.risk>0||group.pins.length))return (x,y)=>deformation(x,y,regions,adjustments);

  return (x,y)=>{
    let dx=0,dy=0,mass=0,pairs=0,strain=0;
    for(const {fields,adjustment,risk,pins} of groups) {
      let mobility=1;
      // Ease the edited surface into observed joint/contact pixels. This
      // constrains the cleanup warp only, before any interactive motion.
      for(const [px,py,radius] of pins) {
        const t=Math.min(1,Math.hypot(x-px,y-py)/radius);
        mobility*=t*t*(3-2*t);
      }
      const [fx,fy,coverage]=featureDisplacement(x,y,fields,adjustment,mobility);
      dx+=fx;dy+=fy;
      pairs+=mass*coverage;
      mass+=coverage;
      strain+=risk*coverage**2;
    }
    // Pairs vanish at a support boundary. This makes the transition into the
    // overlap gradual and keeps the exact requested warp elsewhere.
    // Strong isolated controls also benefit from a soft local limit.
    const divisor=mass>0?1+(OVERLAP_STRENGTH*2*pairs+STRONG_EDIT_RELIEF*strain)/mass:1;
    return [x+dx/divisor,y+dy/divisor];
  };
}
