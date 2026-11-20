// Source-pose depth orders the foreground observations. Projection is from
// the captured camera, using measured screen coordinates and recorded color.
const STRIDE=44;
const CORNERS=[[-3,-3],[3,-3],[-3,3],[-3,3],[3,-3],[3,3]];

function reader(data) {
  if(data?.version!==1||data.format!=="source-gaussians-4d"||data.recordBytes!==STRIDE||
     !Array.isArray(data.frames)||!data.frames.length||
     ![data.width,data.height,data.fps,data.temporalSigmaFrames].every(v=>Number.isFinite(v)&&v>0))
    throw new Error("Invalid Gaussian preview data.");
  const cache=new Map();
  function fetchRow(index) {
    if(cache.has(index))return cache.get(index);
    const raw=atob(data.frames[index]);
    if(raw.length%STRIDE!==0)throw new Error("Invalid Gaussian sample row.");
    const buffer=Uint8Array.from(raw,char=>char.charCodeAt(0));
    const view=new DataView(buffer.buffer);
    const row=new Map();
    for(let start=0;start<buffer.length;start+=STRIDE) {
      const id=view.getUint32(start,true);
      const values=Array.from({length:9},(_,i)=>view.getFloat32(start+4+i*4,true));
      if(!values.every(Number.isFinite)||values[6]<=0||values[7]<=0)
        throw new Error("Invalid Gaussian sample geometry.");
      row.set(id,{id,values,rgba:buffer.slice(start+40,start+44)});
    }
    cache.set(index,row);
    if(cache.size>9)cache.delete(cache.keys().next().value);
    return row;
  }
  return requested=>{
    const time=Math.max(0,Math.min(data.frames.length-1,Number(requested)||0));
    const center=Math.round(time);
    const visible=fetchRow(center), around=[];
    for(let i=Math.max(0,center-2);i<=Math.min(center+2,data.frames.length-1);i++) {
      const offset=time-i;
      around.push([offset,Math.exp(-.5*(offset/data.temporalSigmaFrames)**2),fetchRow(i)]);
    }
    const evaluated=[];
    for(const [id,reference] of visible) {
      let total=0,x=0,y=0,z=0;
      for(const [dt,weight,row] of around) {
        const sample=row.get(id);
        if(!sample)continue;
        const [cx,cy,cz,vx,vy,vz]=sample.values;
        // A linear trajectory couples spatial covariance to time. Taking a
        // conditional slice translates the local spatial Gaussian by v*dt.
        x+=(cx+vx*dt)*weight;
        y+=(cy+vy*dt)*weight;
        z+=(cz+vz*dt)*weight;
        total+=weight;
      }
      const [, , , , , ,sx,sy,angle]=reference.values;
      evaluated.push({id,x:x/total,y:y/total,z:z/total,sx,sy,angle,rgba:reference.rgba});
    }
    return evaluated.sort((a,b)=>b.z-a.z||a.id-b.id);
  };
}

export function evaluateSplatFrame(data,frame) {
  return reader(data)(frame);
}

function pipeline(gl) {
  const program=gl.createProgram();
  const shaders=[
    [gl.VERTEX_SHADER,`
      attribute vec2 position;
      attribute vec2 ellipse;
      attribute vec4 color;
      uniform vec2 viewport;
      varying vec2 local;
      varying vec4 shade;
      void main() {
        gl_Position=vec4(position.x*2.0/viewport.x-1.0,1.0-position.y*2.0/viewport.y,0.0,1.0);
        local=ellipse;
        shade=color;
      }`],
    [gl.FRAGMENT_SHADER,`
      precision mediump float;
      varying vec2 local;
      varying vec4 shade;
      void main() {
        float a=shade.a*exp(-.5*dot(local,local));
        if(a<.01)discard;
        gl_FragColor=vec4(shade.rgb,a);
      }`],
  ];
  for(const [type,source] of shaders) {
    const shader=gl.createShader(type);
    gl.shaderSource(shader,source);
    gl.compileShader(shader);
    if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));
    gl.attachShader(program,shader);
  }
  gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
  return program;
}

export function createSplatPreview(canvas,data) {
  const evaluate=reader(data);
  const gl=canvas.getContext("webgl",{alpha:false,antialias:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error("WebGL rendering is unavailable.");
  const program=pipeline(gl), vertices=gl.createBuffer();
  const viewport=gl.getUniformLocation(program,"viewport");
  gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER,vertices);
  for(const [name,size,offset] of [["position",2,0],["ellipse",2,8],["color",4,16]]) {
    const location=gl.getAttribLocation(program,name);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location,size,gl.FLOAT,false,32,offset);
  }
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  gl.clearColor(.045,.063,.087,1);
  let scratch=new Float32Array(0);
  function draw(frame) {
    const points=evaluate(frame);
    const components=points.length*48;
    if(scratch.length<components)scratch=new Float32Array(components);
    const width=canvas.width,height=canvas.height;
    const scale=Math.min(width/data.width,height/data.height);
    const dx=(width-data.width*scale)/2,dy=(height-data.height*scale)/2;
    let cursor=0;
    for(const {x,y,sx,sy,angle,rgba} of points) {
      const c=Math.cos(angle), s=Math.sin(angle);
      const px=dx+x*scale, py=dy+y*scale;
      for(const [u,v] of CORNERS) {
        scratch[cursor++]=px+scale*(u*sx*c-v*sy*s);
        scratch[cursor++]=py+scale*(u*sx*s+v*sy*c);
        scratch[cursor++]=u;
        scratch[cursor++]=v;
        for(const channel of rgba)scratch[cursor++]=channel/255;
      }
    }
    gl.viewport(0,0,width,height);
    gl.uniform2f(viewport,width,height);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.bufferData(gl.ARRAY_BUFFER,scratch.subarray(0,components),gl.DYNAMIC_DRAW);
    gl.drawArrays(gl.TRIANGLES,0,points.length*6);
    return points.length;
  }
  return {draw};
}
