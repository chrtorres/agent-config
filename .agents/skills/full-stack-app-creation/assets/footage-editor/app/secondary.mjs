import {evaluated} from "./motion.mjs";

const bounded=(value,max)=>Math.max(-max,Math.min(max,value));
const copy=[0,0];

// Jury conditions for the characteristic polynomial z²-a1*z-a2. Reject
// unsupported fits rather than substituting a fabricated measured response.
export function validFit(model) {
  const ar=model?.ar,drive=model?.drive;
  if(!model?.supported||ar?.length!==2||drive?.length!==2||![...ar,...drive].every(Number.isFinite))return false;
  const [a,b]=ar;
  return 1-a-b>.0001&&1+a-b>.0001&&1+b>.0001;
}

function carrierIds(key) {
  if(["torso","chest","left-breast","right-breast"].includes(key))return [11,12,23,24];
  if(["hips","left-hip","right-hip","buttocks","left-buttock","right-buttock"].includes(key))return [23,24];
  if(key==="shoulders")return [11,12];
  if(key==="head"||/eye|brow|nose|mouth|chin/.test(key))return [0,7,8];
  const side=key.startsWith("right-")?1:0;
  if(key.endsWith("-arm"))return [13+side,15+side];
  if(/hand|finger|thumb|pinky/.test(key))return [15+side];
  if(key.endsWith("-calf"))return [25+side,27+side];
  if(key.endsWith("-leg"))return [23+side,25+side,27+side];
  return [11,12,23,24];
}

export class SecondaryMotion {
  constructor(study) {
    this.study=study;
    this.enabled=false;
    this.entries=Object.entries(study?.models??{}).filter(([,model])=>validFit(model)).map(([key,model])=>
      ({key,model,ids:carrierIds(key),at:[...copy],previous:[...copy],driver:[...copy],olderDriver:[...copy]}));
    this.clear();
  }
  clear() {
    for(const item of this.entries) {
      item.at=[0,0];item.previous=[0,0];item.driver=[0,0];item.olderDriver=[0,0];
    }
    this.result={};
    this.amplitude=0;
    this.accumulator=0;
  }
  enable(value) {this.enabled=value;this.clear();}
  tick(dt,frame,source,state,poseActive) {
    if(!this.enabled||!source||!poseActive||!this.entries.length) {this.clear();return;}
    this.accumulator+=dt;
    const samplePeriod=1/(this.study?.fps??30);
    if(this.accumulator+1e-8<samplePeriod)return;
    const pose=evaluated(source,state);
    while(this.accumulator+1e-8>=samplePeriod) {
      this.accumulator=Math.max(0,this.accumulator-samplePeriod);
      const result={};
      let maximum=0;
      for(const item of this.entries) {
        const {key,model,ids,at,previous,driver,olderDriver}=item;
        const value=ids.reduce((p,id)=>[p[0]+(pose[id][0]-source[id][0])/ids.length,
          p[1]+(pose[id][1]-source[id][1])/ids.length],[0,0]);
        const [ar1,ar2]=model.ar;
        const limit=Math.max(.8,Math.min(18,model.limit_px??(model.amplitude_p90??6.4)*1.25));
        const next=value.map((v,axis)=>bounded(ar1*at[axis]+ar2*previous[axis]+
          model.drive[axis]*bounded(v-2*driver[axis]+olderDriver[axis],55),limit));
        item.olderDriver=driver;item.driver=value;
        item.previous=at;item.at=next;
        const confidence=this.study.frames[frame]?.[key]?.[2]??0;
        if(confidence<.08)continue;
        const output=next.map(v=>v*Math.min(1,confidence/.55));
        if(Math.hypot(...output)>.008) {
          result[key]=output;maximum=Math.max(maximum,Math.hypot(...output));
        }
      }
      this.result=result;this.amplitude=maximum;
    }
  }
  inspect(frame) {
    return {enabled:this.enabled,active:this.amplitude>.008,frame,regions:Object.keys(this.result),
      amplitude:this.amplitude,eligibleRegions:this.entries.length};
  }
}

export function secondaryField(regions,response) {
  const entries=Object.entries(response).flatMap(([name,vector])=>(regions[name]??[]).filter(Boolean)
    .map(ellipse=>({ellipse,vector})));
  if(!entries.length)return ()=>copy;
  return (x,y)=>{
    let dx=0,dy=0,weights=0;
    for(const {ellipse:[cx,cy,ux,uy,rx,ry],vector:[vx,vy]} of entries) {
      const across=(x-cx)*ux+(y-cy)*uy,along=(y-cy)*ux-(x-cx)*uy;
      const inside=1-(across/rx)**2-(along/ry)**2;
      if(inside<=0)continue;
      const weight=inside**2;
      dx+=vx*weight;dy+=vy*weight;weights+=weight;
    }
    return [dx/Math.max(1,weights),dy/Math.max(1,weights)];
  };
}

// The image already contains the recorded residual. Use its direction to
// retain a small part of the tracked cleanup support's real motion, without
// adding the footage's displacement a second time.
export function followObservation(stabilized,raw,observation) {
  if(!raw||!observation||observation[2]<.28)return stabilized;
  return stabilized.map((shape,i)=>{
    const original=raw[i];
    if(!shape||!original)return shape;
    const dx=original[0]-shape[0],dy=original[1]-shape[1];
    const size=Math.hypot(dx,dy),motion=Math.hypot(observation[0],observation[1]);
    if(size<.02||motion<.04)return shape;
    const alignment=(dx*observation[0]+dy*observation[1])/(size*motion);
    const amount=.55*Math.max(0,alignment)*Math.min(1,observation[2]/.7,motion/size);
    return [shape[0]+dx*amount,shape[1]+dy*amount,...shape.slice(2)];
  });
}
