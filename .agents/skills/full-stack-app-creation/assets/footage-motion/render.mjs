import { LINKS,evaluated } from "./motion.mjs";

const VERTEX = "attribute vec2 p; attribute vec2 uv; varying vec2 q; varying vec2 xy; uniform vec2 size;"+
 "void main(){q=uv; xy=p;gl_Position=vec4(p.x/size.x*2.0-1.0,1.0-p.y/size.y*2.0,0,1);}";
const FRAGMENT = [
  "precision highp float; varying vec2 q; varying vec2 xy; uniform vec2 size;",
  "uniform vec2 tile; uniform sampler2D frame; uniform sampler2D matte; uniform sampler2D fill;",
  "uniform int kind; uniform vec4 protect; uniform vec4 reflection; uniform float mirrorSlope; ",
  "bool protectedPixel(vec2 p){return p.x>=protect.x&&p.y>=protect.y&&p.x<protect.z&&p.y<protect.w;}",
  "void main(){ vec4 v=texture2D(frame,q);",
  " if(kind==0){gl_FragColor=v;return;}",
  " vec2 atlas=(tile+clamp(q*size/PIXEL_SCALE,vec2(.5),vec2(TILE_RIGHT,TILE_BOTTOM)))/vec2(ATLAS_WIDTH,ATLAS_HEIGHT);",
  " vec2 m=texture2D(matte,atlas).rg;",
  " if(kind==1){float a=protectedPixel(xy)?0.0:smoothstep(.015,.14,max(m.x,m.y));gl_FragColor=vec4(mix(v.rgb,texture2D(fill,atlas).rgb,a),1.);return;}",
  " if(protectedPixel(xy)||(kind==3&&(xy.x<reflection.x||xy.y<reflection.y||xy.x>reflection.z||xy.y>reflection.w+mirrorSlope*xy.x))) discard;",
  " float a=kind==2?m.x:m.y; if(a<.004)discard;gl_FragColor=vec4(v.rgb,a); }",
].join("\n");

function program(gl,timeline) {
  const [w,h]=timeline.tile;
  const {grid,pixelScale}=timeline;
  if(![w,h,grid,pixelScale].every(v=>Number.isInteger(v)&&v>0&&v<=8192))
    throw new Error("Invalid atlas geometry.");
  // Compile stable atlas constants so shader arithmetic agrees with a build
  // using the same dimensions as literals, including on pixel comparisons.
  const fragment=Object.entries({PIXEL_SCALE:pixelScale,TILE_RIGHT:w-.5,TILE_BOTTOM:h-.5,
    ATLAS_WIDTH:w*grid,ATLAS_HEIGHT:h*grid}).reduce((shader,[token,value])=>
      shader.replace(token,value.toFixed(1)),FRAGMENT);
  const p=gl.createProgram();
  for(const [type,src] of [[gl.VERTEX_SHADER,VERTEX],[gl.FRAGMENT_SHADER,fragment]]) {
    const s=gl.createShader(type);
    gl.shaderSource(s,src);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    gl.attachShader(p,s);
  }
  gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  gl.useProgram(p);
  return p;
}

const fetchTexture=async path=>{
  const res=await fetch(path);
  if(!res.ok)throw new Error("Missing timeline image.");
  return createImageBitmap(await res.blob(),{colorSpaceConversion:"none",premultiplyAlpha:"none"});
};

function mesh(points,w,h) {
  const xs=Object.values(points).map(p=>p[0]),ys=Object.values(points).map(p=>p[1]);
  const left=Math.max(0,Math.min(...xs)-90),right=Math.min(w,Math.max(...xs)+90);
  const top=Math.max(0,Math.min(...ys)-95),bottom=Math.min(h,Math.max(...ys)+95);
  const cols=Math.ceil((right-left)/19)+1, rows=Math.ceil((bottom-top)/19)+1;
  const bytes=new Float32Array(cols*rows*4), index=[], vertices=[];
  const segments=LINKS.map(([a,b])=>{
    const p=points[a],q=points[b],dx=q[0]-p[0],dy=q[1]-p[1];
    return {x:p[0],y:p[1],dx,dy,den:Math.max(dx*dx+dy*dy,.1), confidence:Math.min(p[2],q[2])};
  });
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++) {
    const x=left+(right-left)*c/(cols-1),y=top+(bottom-top)*r/(rows-1);
    const scored=segments.map((s,i)=>{
      const t=Math.min(1,Math.max(0,((x-s.x)*s.dx+(y-s.y)*s.dy)/s.den));
      const d=(x-s.x-t*s.dx)**2+(y-s.y-t*s.dy)**2;
      return {i,t,d:d+(1-s.confidence)*480};
    }).sort((a,b)=>a.d-b.d).slice(0,4);
    const near=scored[0].d;
    const values=scored.map(s=>Math.exp(-(s.d-near)/840));
    const total=values.reduce((a,b)=>a+b,0);
    const weights=scored.map(({i,t},k)=>[i,t,values[k]/total]);
    const idx=r*cols+c;
    vertices.push({x,y,weights});
    bytes.set([x,y,x/w,y/h],idx*4);
    if(c<cols-1&&r<rows-1)index.push(idx,idx+1,idx+cols,idx+1,idx+cols+1,idx+cols);
  }
  return {vertices,bytes,index:new Uint16Array(index)};
}

// Piecewise-affine skinning follows each observed bone. A mild scale bound
// keeps distorted detections from growing a limb when it moves behind an edge.
function mapping(a,b,c,d) {
  const ux=b[0]-a[0],uy=b[1]-a[1],vx=d[0]-c[0],vy=d[1]-c[1];
  const n=ux*ux+uy*uy;
  if(n<9)return [1,0,c[0]-a[0],c[1]-a[1]];
  let r=(ux*vx+uy*vy)/n,s=(ux*vy-uy*vx)/n;
  const gain=Math.hypot(r,s);
  const factor=gain>.0001?Math.min(1.42,Math.max(.68,gain))/gain:1;
  r*=factor;s*=factor;
  return [r,s,c[0]-r*a[0]+s*a[1],c[1]-s*a[0]-r*a[1]];
}

export async function createRenderer(canvas) {
  const timeline=await fetch("/timeline/timeline.json").then(response=>{
    if(!response.ok)throw new Error("Motion timeline unavailable.");
    return response.json();
  });
  const gl=canvas.getContext("webgl",{alpha:false,antialias:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error("Movement control needs WebGL.");
  const pipeline=program(gl,timeline);
  const position=gl.getAttribLocation(pipeline,"p"),uv=gl.getAttribLocation(pipeline,"uv");
  const uniform=Object.fromEntries(["size","tile","kind","protect","reflection","mirrorSlope","frame","matte","fill"]
    .map(k=>[k,gl.getUniformLocation(pipeline,k)]));
  gl.uniform1i(uniform.frame,0);gl.uniform1i(uniform.matte,1);gl.uniform1i(uniform.fill,2);
  gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.NONE);
  const texture=(bitmap,filter)=>{
    const t=gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D,t);
    for(const setting of [gl.TEXTURE_MAG_FILTER,gl.TEXTURE_MIN_FILTER])gl.texParameteri(gl.TEXTURE_2D,setting,filter);
    for(const setting of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,setting,gl.CLAMP_TO_EDGE);
    if(bitmap)gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,bitmap);
    return t;
  };
  const source=texture(null,gl.NEAREST);
  const atlases=await Promise.all(timeline.pages.map(pair=>Promise.all(pair.map(async name=>{
    const bitmap=await fetchTexture("/timeline/"+name);
    const result=texture(bitmap,gl.LINEAR);
    bitmap.close();
    return result;
  }))));
  const quad=gl.createBuffer(),surface=gl.createBuffer(),triangles=gl.createBuffer();
  const bind=buffer=>{
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,16,0);
    gl.enableVertexAttribArray(uv);gl.vertexAttribPointer(uv,2,gl.FLOAT,false,16,8);
  };
  const [tw,th]=timeline.tile, grid=timeline.grid, height=timeline.height;
  let current=-1,layers=[],width=0,seenFrame=-1,renders=0,subjects=[];
  function baseAt(i) {
    return timeline.frames[i][1].map(row=>Object.fromEntries(row.map(([x,y,c],n)=>[
      timeline.landmarks[n],[x/4,y/4,c/100]
    ])));
  }
  function frame(video,index) {
    if(video.readyState<2||video.videoHeight!==height)return false;
    const [w]=timeline.frames[index];
    if(video.videoWidth!==w)return false;
    if(w!==width) {
      width=w;canvas.width=width;canvas.height=height;gl.viewport(0,0,width,height);
      gl.uniform2f(uniform.size,width,height);
      gl.bindBuffer(gl.ARRAY_BUFFER,quad);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,0,0,width,0,1,0,0,height,0,1,width,height,1,1]),gl.STATIC_DRAW);
    }
    current=index;
    layers=baseAt(index).map(points=>({points,mesh:null}));
    const tile=index%(grid*grid),page=Math.floor(index/(grid*grid));
    gl.uniform2f(uniform.tile,(tile%grid)*tw,Math.floor(tile/grid)*th);
    const shot=timeline.shots.findIndex(([a,b])=>index>=a&&index<b);
    gl.uniform4f(uniform.protect,...timeline.protected[shot]);
    gl.uniform4f(uniform.reflection,...timeline.reflection[shot].slice(0,4));
    gl.uniform1f(uniform.mirrorSlope,timeline.reflection[shot][4]??0);
    for(let i=0;i<2;i++) {
      gl.activeTexture(gl.TEXTURE1+i);gl.bindTexture(gl.TEXTURE_2D,atlases[page][i]);
    }
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,source);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,video);
    seenFrame=current;
    return true;
  }
  function draw(state,active) {
    if(current<0)return;
    gl.disable(gl.BLEND);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
    gl.uniform1i(uniform.kind,active?1:0);
    bind(quad);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
    subjects=[];
    renders++;
    if(!active)return;
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    for(let index=layers.length-1;index>=0;index--) {
      const layer=layers[index],before=layer.points,after=evaluated(before,state,index===1);
      subjects[index]=after;
      const m=layer.mesh??(layer.mesh=mesh(before,width,height));
      const map=LINKS.map(([a,b])=>mapping(before[a],before[b],after[a],after[b]));
      for(let i=0;i<m.vertices.length;i++) {
        const {x,y,weights}=m.vertices[i];
        let dx=0,dy=0;
        for(const [link,,weight] of weights) {
          const [r,s,px,py]=map[link];
          dx+=(x*r-y*s+px)*weight;dy+=(x*s+y*r+py)*weight;
        }
        m.bytes[i*4]=dx;m.bytes[i*4+1]=dy;
      }
      gl.uniform1i(uniform.kind,index+2);
      bind(surface);gl.bufferData(gl.ARRAY_BUFFER,m.bytes,gl.DYNAMIC_DRAW);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,triangles);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,m.index,gl.DYNAMIC_DRAW);
      gl.drawElements(gl.TRIANGLES,m.index.length,gl.UNSIGNED_SHORT,0);
    }
  }
  return {timeline,frame,draw,baseAt,inspect:()=>({frame:seenFrame,renders,width,height,subjects})};
}
