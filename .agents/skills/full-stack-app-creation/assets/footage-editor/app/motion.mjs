// The movement state is independent of the media clock. Positions and angles
// are expressed in the camera plane, where the original footage is observable.
export const PARTS = ["Left arm","Right arm","Left leg","Right leg","Torso","Head"];
export const LINKS = [[23,24],[11,12],[11,23],[12,24],[11,7],[12,8],[7,8],[0,7],[0,8],
  [11,13],[13,15],[12,14],[14,16],[23,25],[25,27],[27,31],[27,29],[24,26],[26,28],[28,32],[28,30]];
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]];
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1]];
const scale=(p,s)=>[p[0]*s,p[1]*s];
const mag=p=>Math.hypot(...p);
const mean=(a,b)=>scale(add(a,b),.5);
const turn=(v,r)=>[v[0]*Math.cos(r)-v[1]*Math.sin(r),v[0]*Math.sin(r)+v[1]*Math.cos(r)];
const empty=()=>PARTS.map(()=>[0,0,0]);

export class Motion {
  constructor() {
    this.selected=0;
    this.reset();
  }
  reset() {
    this.root=[0,0];this.velocity=[0,0];this.offsets=empty();
    this.phase=0;this.gait=0;this.lift=0;this.vertical=0;this.hopping=false;
  }
  choose(value) { this.selected=(value+PARTS.length)%PARTS.length; }
  jump() {
    if(!this.hopping) {this.hopping=true;this.vertical=267;}
  }
  active() {
    return this.root.some(x=>Math.abs(x)>.0001)||this.gait>.001||this.lift>.01||
      this.offsets.some(row=>row.some(x=>Math.abs(x)>.0001));
  }
  position(index,value) { this.offsets[this.selected][index]=clamp(value,-1,1); }
  tick(dt, drive, reference, width, height, travelY=[height*.25,height*.88], rootLimit=[width,height]) {
    const [lx,ly,rx,ry,rotation]=drive;
    const hip=reference?mean(reference[23],reference[24]):[width/2,height*.6];
    const delta=1-Math.exp(-16*dt);
    this.velocity=this.velocity.map((v,i)=> {
      const next=v+(([lx*230,ly*142][i])-v)*delta;
      return Math.abs(next)<.55?0:next;
    });
    const room=travelY;
    for(let axis=0;axis<2;axis++) {
      // An actor partly out of the source frame can move inward immediately.
      const low=Math.min(0,(axis===0?48:room[0])-hip[axis]);
      const high=Math.max(0,(axis===0?width-44:room[1])-hip[axis]);
      this.root[axis]=clamp(this.root[axis]+this.velocity[axis]*dt,Math.max(low,-rootLimit[axis]),Math.min(high,rootLimit[axis]));
    }
    const speed=clamp(mag(this.velocity)/230,0,1);
    this.phase=(this.phase+dt*(1+speed*5.9))%(Math.PI*2);
    this.gait+=((speed>.005?speed:0)-this.gait)*(1-Math.exp(-12*dt));
    if(this.gait<.0009) this.gait=0;
    if(this.hopping) {
      this.lift+=this.vertical*dt; this.vertical-=790*dt;
      if(this.lift<=0&&this.vertical<0) {this.hopping=false;this.lift=0;this.vertical=0;}
    }
    const axes=[rx,ry,rotation];
    for(let i=0;i<3;i++) {
      if(axes[i]) this.position(i,this.offsets[this.selected][i]+dt*axes[i]*1.65);
    }
  }
  snapshot() {
    return {root:[...this.root],offsets:this.offsets.map(x=>[...x]),selected:this.selected,
      phase:this.phase,gait:this.gait,lift:this.lift};
  }
}

// Clamp the target to the two-bone chain's reach before solving the bend.
function chain(a,b,c,newA,target) {
  const upper=mag(sub(b,a)), lower=mag(sub(c,b));
  const original=sub(c,a);
  const cross=original[0]*(b[1]-a[1])-original[1]*(b[0]-a[0]);
  const aim=sub(target,newA);
  const length=mag(aim);
  if(upper<5||lower<5||length<.05) return [add(newA,sub(b,a)),add(newA,original)];
  const reach=clamp(length,Math.abs(upper-lower)+.08,upper+lower-.04);
  const direction=scale(aim,1/length), side=Math.sign(cross)||1;
  const along=(upper*upper-lower*lower+reach*reach)/(2*reach);
  const perpendicular=Math.sqrt(Math.max(0,upper*upper-along*along));
  const joint=add(newA,add(scale(direction,along),scale([-direction[1]*side,direction[0]*side],perpendicular)));
  return [joint,add(newA,scale(direction,reach))];
}

export function evaluated(j, state, reflected=false) {
  const hip=mean(j[23],j[24]), shoulder=mean(j[11],j[12]);
  const unit=clamp(mag(sub(hip,shoulder)),68,280);
  const direction=reflected?-.65:1, amount=reflected?.64:1;
  const root=[state.root[0]*direction,(state.root[1]-state.lift)*amount];
  const [tx,ty,tr]=state.offsets[4];
  const [hx,hy,hr]=state.offsets[5];
  const torso=[tx*unit*.32*(reflected?-1:1),ty*unit*.35];
  const lean=tr*.48*(reflected?-1:1);
  const moved={};
  for(const i of [11,12,13,14,15,16,0,7,8]) {
    moved[i]=add(hip,add(turn(sub(j[i],hip),lean),add(root,torso)));
  }
  const head=moved[0];
  for(const i of [0,7,8]) {
    const angle=hr*.45*(reflected?-1:1);
    moved[i]=add(head,add(turn(sub(j[i],j[0]),angle),[hx*unit*.27*(reflected?-1:1),hy*unit*.24]));
  }
  for(let side=0;side<2;side++) {
    const sign=side===0?1:-1;
    const [ax,ay,ar]=state.offsets[side];
    const shoulderId=11+side,elbow=13+side,wrist=15+side;
    const swing=Math.sin(state.phase)*state.gait*sign;
    const armPull=[(ax*.51-swing*.15)*unit*(reflected?-1:1),ay*unit*.62+Math.abs(swing)*unit*.055];
    const aim=add(moved[wrist],armPull);
    moved[wrist]=add(moved[shoulderId],turn(sub(aim,moved[shoulderId]),ar*.62*(reflected?-1:1)));
    if(Math.abs(ax)+Math.abs(ay)+Math.abs(ar)+Math.abs(swing)>.0001)
      [moved[elbow],moved[wrist]]=chain(j[shoulderId],j[elbow],j[wrist],moved[shoulderId],moved[wrist]);
    const [lx,ly,lr]=state.offsets[side+2];
    const h=23+side,k=25+side,a=27+side,toe=31+side,heel=29+side;
    const set=add(root,[unit*(lx*.64+swing*.27)*(reflected?-1:1),unit*(ly*.54-Math.max(0,swing)*.19)]);
    moved[h]=add(j[h],root);
    moved[a]=add(j[a],set);
    moved[k]=add(j[k],root);
    if(Math.abs(lx)+Math.abs(ly)+Math.abs(swing)>.0001)
      [moved[k],moved[a]]=chain(j[h],j[k],j[a],moved[h],moved[a]);
    const angle=lr*.87*(reflected?-1:1);
    for(const t of [toe,heel]) moved[t]=add(moved[a],turn(sub(j[t],j[a]),angle));
  }
  return moved;
}
