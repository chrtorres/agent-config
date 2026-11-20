import assert from "node:assert/strict";
import {fitTransport} from "../app/transport.mjs";

const width=240, height=340, row=13, rows=18;
const points=[], indices=[];
for(let y=0;y<rows;y++)for(let x=0;x<row;x++) {
  const i=y*row+x;
  points.push([width*x/(row-1),height*y/(rows-1)]);
  if(x+1<row&&y+1<rows)indices.push(i,i+1,i+row,i+1,i+row+1,i+row);
}
const area=([ax,ay],[bx,by],[cx,cy])=>(bx-ax)*(cy-ay)-(by-ay)*(cx-ax);
const identity=fitTransport(points,points,indices,width,height);
assert.deepEqual(identity.points,points);
assert.equal(identity.scale,1);

let seed=8723;
function sample() {
  seed=(Math.imul(seed,1664525)+1013904223)>>>0;
  return seed/2**32;
}
let minimum=1;
for(let run=0;run<100;run++) {
  const targets=points.map(([x,y],i)=>[x+(sample()-.5)*620,(i+run)%17===0?NaN:y+(sample()-.5)*780]);
  const output=fitTransport(points,targets,indices,width,height);
  assert.ok(output.scale>=0&&output.scale<=1);
  const stored=output.points.map(pair=>pair.map(Math.fround));
  stored.forEach(([x,y],i)=>{
    const [u,v]=points[i];
    assert.ok(x>=0&&x<=width&&y>=0&&y<=height);
    if(u===0||u===width)assert.equal(x,u);
    if(v===0||v===height)assert.equal(y,v);
  });
  for(let i=0;i<indices.length;i+=3) {
    const triangle=indices.slice(i,i+3);
    const ratio=area(...triangle.map(j=>stored[j]))/area(...triangle.map(j=>points[j]));
    assert.ok(ratio>=.15);
    minimum=Math.min(minimum,ratio);
  }
}
console.log(JSON.stringify({identity:true,adversarial_meshes:100,triangles_per_mesh:indices.length/3,
  minimum_float32_area_ratio:minimum}));
