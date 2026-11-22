// Soft-tissue dynamics for edited parts. The footage already contains the
// original tissue's motion, so only the volume a shape edit adds is simulated:
// that extra mass hangs from the tracked part on a damped spring, lags when the
// body accelerates, and overshoots when it stops. The simulation runs once per
// shot over the whole track, so playback, seeking, and the exported video show
// the same motion. tools/soft_body.py mirrors this file.

// [natural frequency in Hz, damping ratio, softness]. Rigid parts are absent.
const SOFT=[2.6,.2,1], FLESH=[3.2,.28,.7], LIMB=[4.5,.35,.4];
export const MATERIALS={
  chest:SOFT,"left-breast":SOFT,"right-breast":SOFT,
  buttocks:SOFT,"left-buttock":SOFT,"right-buttock":SOFT,
  hips:FLESH,"left-hip":FLESH,"right-hip":FLESH,torso:FLESH,
  "left-calf":[4,.3,.55],"right-calf":[4,.3,.55],
  "left-arm":LIMB,"right-arm":LIMB,"left-leg":LIMB,"right-leg":LIMB,
  shoulders:[5,.4,.3],
};
const LIMIT=.15, SMOOTH=[1,4,6,4,1];

// Share of the part's projected area that the edit added.
export function addedShare([width,height]) {
  const grow=(1+width)*(1+height)-1;
  return grow>0?grow/(1+grow):0;
}

function smoothedCenters(run,shapes) {
  return run.map((frame,position)=>{
    let x=0,y=0,total=0;
    for(let tap=-2;tap<=2;tap++) {
      const shape=shapes[run[position+tap]];
      if(position+tap<0||position+tap>=run.length||!shape)continue;
      const weight=SMOOTH[tap+2];
      x+=shape[0]*weight;y+=shape[1]*weight;total+=weight;
    }
    return [x/total,y/total];
  });
}

// frames[i][key] is the list of segment ellipses for frame i. Returns, per
// frame, a list of [ox,oy] offsets per segment (null where untracked), or
// null when the part is rigid or the edit adds no volume.
export function softBodyTrack(frames,key,adjustment,{times,fps,shots}) {
  const material=MATERIALS[key], share=addedShare(adjustment);
  if(!material||share<=0)return null;
  const [frequency,damping,softness]=material;
  const omega=2*Math.PI*frequency, gain=share*softness;
  const time=index=>times?.[index]??index/fps;
  const segments=Math.max(0,...frames.map(frame=>frame[key]?.length??0));
  const result=frames.map(()=>Array(segments).fill(null));
  for(const [start,end] of shots??[[0,frames.length]]) {
    for(let segment=0;segment<segments;segment++) {
      const shapes=frames.map(frame=>frame[key]?.[segment]??null);
      let index=start;
      while(index<end) {
        if(!shapes[index]){index++;continue;}
        const run=[];
        while(index<end&&shapes[index])run.push(index++);
        const centers=smoothedCenters(run,shapes);
        let [x,y]=centers[0], vx=0, vy=0;
        result[run[0]][segment]=[0,0];
        for(let step=1;step<run.length;step++) {
          const dt=Math.max(1e-4,time(run[step])-time(run[step-1]));
          const [ax,ay]=centers[step-1], [bx,by]=centers[step];
          const cvx=(bx-ax)/dt, cvy=(by-ay)/dt;
          if(step===1){vx=cvx;vy=cvy;}
          const substeps=Math.max(1,Math.ceil(dt*omega/.2)), h=dt/substeps;
          for(let sub=1;sub<=substeps;sub++) {
            const cx=ax+cvx*h*sub, cy=ay+cvy*h*sub;
            // Semi-implicit Euler: the mass is pulled toward the moving anchor
            // and damped relative to the anchor's velocity.
            vx+=(-omega*omega*(x-cx)-2*damping*omega*(vx-cvx))*h;
            vy+=(-omega*omega*(y-cy)-2*damping*omega*(vy-cvy))*h;
            x+=vx*h;y+=vy*h;
          }
          const shape=shapes[run[step]];
          const limit=LIMIT*Math.min(shape[4],shape[5]);
          let ox=x-bx, oy=y-by;
          const size=Math.hypot(ox,oy);
          if(size>limit) {
            // A bounded tether keeps a violent tracking jump from flinging
            // the tissue off the body. Velocity is clipped with it.
            const keep=limit/size;
            ox*=keep;oy*=keep;x=bx+ox;y=by+oy;vx=cvx+(vx-cvx)*keep;vy=cvy+(vy-cvy)*keep;
          }
          result[run[step]][segment]=[ox*gain,oy*gain];
        }
      }
    }
  }
  return result;
}

export function withOffsets(shapes,offsets) {
  if(!offsets)return shapes;
  return shapes.map((shape,index)=>shape&&offsets[index]?[...shape.slice(0,6),...offsets[index]]:shape);
}
