import assert from "node:assert/strict";
import {SecondaryMotion,followObservation,secondaryField,validFit} from "../app/secondary.mjs";

const model={ar:[1.28,-.62],drive:[.3,.26],supported:true};
assert.ok(validFit(model));
assert.ok(!validFit({...model,ar:[1.8,-.2]}));
assert.ok(!validFit({...model,supported:false}));
const shape=[35,55,1,0,20,30], raw=[38,55,1,0,20,30];
assert.ok(followObservation([shape],[raw],[3,0,.9])[0][0]>35);
assert.deepEqual(followObservation([shape],[raw],[-3,0,.9]),[shape]);
assert.deepEqual(followObservation([shape],[raw],[3,0,.1]),[shape]);
const field=secondaryField({chest:[shape]},{chest:[2,3]});
assert.deepEqual(field(35,55),[2,3]);
assert.deepEqual(field(80,80),[0,0]);

const source=Object.fromEntries(Array.from({length:33},(_,i)=>[i,[80+i*2,45+i*4,1]]));
const state={root:[0,0],lift:0,offsets:Array.from({length:6},()=>[0,0,0]),gait:0,phase:0};
const study={fps:30,frames:[{chest:[2,0,1]}],models:{chest:model,unsafe:{...model,ar:[2,0]}}};
const motion=new SecondaryMotion(study);
assert.equal(motion.inspect(0).eligibleRegions,1);
motion.enable(true);
motion.tick(1/30,0,source,state,true);
assert.equal(motion.amplitude,0);
state.root=[14,0];
motion.tick(1/30,0,source,state,true);
assert.ok(motion.amplitude>1);
const peaks=[];
for(let i=0;i<50;i++) {motion.tick(1/30,0,source,state,true);peaks.push(motion.result.chest?.[0]??0);}
assert.ok(peaks.some(v=>v<-.02));
assert.equal(motion.amplitude,0);
motion.enable(false);
assert.deepEqual(motion.inspect(0),{enabled:false,active:false,frame:0,regions:[],amplitude:0,eligibleRegions:1});
console.log("PASS stable fit admission, localized field, observed direction, driven rebound, settling and exact disable");
