import {followObservation,secondaryField} from "./secondary.mjs";
import {edgeAxisWeight,fitTransport} from "./transport.mjs";
import {compileCleanup} from "./cleanup.mjs";
import {deformation} from "./regions.mjs";
import {pointShape} from "./point-regions.mjs";
import { LINKS,evaluated } from "./motion.mjs";

const VERTEX = "attribute vec2 p; attribute vec2 uv; varying vec2 q; varying vec2 xy; uniform vec2 size;"+
 "void main(){q=uv; xy=p;gl_Position=vec4(p.x/size.x*2.0-1.0,1.0-p.y/size.y*2.0,0,1);}";
const FRAGMENT = [
  "precision highp float; varying vec2 q; varying vec2 xy; uniform vec2 size;",
  "uniform vec2 tile; uniform sampler2D frame; uniform sampler2D matte; uniform sampler2D skin; uniform vec3 tone; uniform float raster;",
  "uniform int kind; uniform vec4 protect; uniform float verticalTravel;",
  "bool protectedPixel(vec2 p){return p.x>=protect.x&&p.y>=protect.y&&p.x<protect.z&&p.y<protect.w;}",
  "vec4 grade(vec4 v,vec2 atlas){",
  " if(tone==vec3(0.0))return v;",
  " float weight=texture2D(skin,atlas).r; if(weight<.004)return v;",
  " float y=dot(v.rgb,vec3(.2126,.7152,.0722));",
  " float midtone=4.0*y*(1.0-y);",
  " vec3 rgb=v.rgb+(v.rgb-y)*tone.z*.42+midtone*(tone.x*.16+tone.y*vec3(.085,.012,-.085));",
  " return vec4(mix(v.rgb,clamp(rgb,0.0,1.0),weight),v.a); }",
  "vec2 tileUV(vec2 sourceUV){",
  " return (tile+clamp(sourceUV*size/PIXEL_SCALE,vec2(.5),vec2(TILE_RIGHT,TILE_BOTTOM)))/vec2(ATLAS_WIDTH,ATLAS_HEIGHT); }",
  "float opacityAt(vec2 uv){vec2 a=texture2D(matte,tileUV(uv)).rg;return max(a.r,a.g);}",
  "vec4 visibleRow(vec2 dest, vec2 warped){",
  " vec2 row=vec2(warped.x,dest.y);",
  " float known=1.-smoothstep(.008,.16,opacityAt(row));",
  " vec4 direct=texture2D(frame,row);",
  " if(known>.999)return direct;",
  " vec4 sum=vec4(0.); float weight=0.;",
  " for(int i=1;i<=7;i++){",
  "   float stepPx=7.*float(i)*float(i);",
  "   float gain=1./(1.+float(i)*float(i));",
  "   for(int side=-1;side<=1;side+=2){",
  "     float x=clamp(row.x+float(side)*stepPx/size.x,0.,1.);",
  "     vec2 sampleAt=vec2(x,dest.y);",
  "     float accepted=(1.-smoothstep(.008,.13,opacityAt(sampleAt)))*gain;",
  "     sum+=texture2D(frame,sampleAt)*accepted;weight+=accepted;",
  "   }",
  " }",
  " vec4 estimate=mix(texture2D(frame,warped),sum/max(.00001,weight),smoothstep(.00001,.018,weight));",
  " return mix(estimate,direct,known);",
  "}",
  "void main(){ vec4 v=texture2D(frame,q);",
  " if(kind==0){gl_FragColor=v;return;}",
  " vec2 atlas=tileUV(q);",
  " v=grade(v,atlas); if(kind==4){gl_FragColor=v;return;}",
  " vec2 target=(floor(xy*raster)+.5)/(size*raster);",
  " vec2 dest=tileUV(target);",
  " if(protectedPixel(xy)||length((q-target)*size)<.045){gl_FragColor=grade(texture2D(frame,target),dest);return;}",
  " if(kind==6){",
  "   vec2 newMask=texture2D(matte,atlas).rg;",
  "   vec2 stepUV=vec2(PIXEL_SCALE)/size;",
  "   vec2 oldMask=texture2D(matte,dest).rg;",
  "   oldMask=max(oldMask,.78*texture2D(matte,tileUV(target+vec2(stepUV.x,0.))).rg);",
  "   oldMask=max(oldMask,.78*texture2D(matte,tileUV(target-vec2(stepUV.x,0.))).rg);",
  "   oldMask=max(oldMask,.78*texture2D(matte,tileUV(target+vec2(0.,stepUV.y))).rg);",
  "   oldMask=max(oldMask,.78*texture2D(matte,tileUV(target-vec2(0.,stepUV.y))).rg);",
  "   float before=smoothstep(.018,.68,max(oldMask.r,oldMask.g));",
  "   float after=smoothstep(.018,.68,max(newMask.r,newMask.g));",
  "   vec4 original=grade(texture2D(frame,target),dest);",
  "   if(before==0.0&&after==0.0){gl_FragColor=original;return;}",
  "   vec2 onRow=vec2(q.x,target.y);",
  "   float sameRow=(1.-smoothstep(.012,.17,opacityAt(onRow)))*(1.-after)*.55;",
  "   float near=1.-smoothstep(4.,28.,abs(q.y-target.y)*size.y);",
  "   vec4 transported=mix(v,texture2D(frame,onRow),sameRow*near);",
  "   vec4 composite=mix(original,transported,max(before,after));",
  // Large vertical movement can carry the sky into the water or the water into
  // the deck. Repair the exposed silhouette from the recorded destination row.
  "   float level=smoothstep(24.,60.,verticalTravel);",
  "   if(level>0.0&&before>0.0&&after<.999){",
  "     float repair=smoothstep(.018,.34,max(oldMask.r,oldMask.g));",
  "     vec4 background=mix(original,visibleRow(target,q),repair);",
  "     composite=mix(composite,mix(background,v,after),level);",
  "   }",
  "   gl_FragColor=composite;return;",
  " }",
  " float before=smoothstep(.015,.14,texture2D(matte,dest).r);",
  " float after=texture2D(matte,atlas).r;",
  " gl_FragColor=mix(grade(texture2D(frame,target),dest),v,max(before,after)); }",
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
      shader.replaceAll(token,value.toFixed(1)),FRAGMENT);
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

function mesh(w,h,details,points=null) {
  const xs=Object.values(points??{}).map(p=>p[0]),ys=Object.values(points??{}).map(p=>p[1]);
  for(const [x,y,ux,uy,rx,ry] of details) {
    const ex=Math.hypot(ux*rx,uy*ry), ey=Math.hypot(uy*rx,ux*ry);
    xs.push(x-ex,x+ex);ys.push(y-ey,y+ey);
  }
  const left=points?Math.max(0,Math.min(...xs)-145):0,right=points?Math.min(w,Math.max(...xs)+145):w;
  const top=points?Math.max(0,Math.min(...ys)-172):0,bottom=points?Math.min(h,Math.max(...ys)+125):h;
  // Thin finger and face regions need more geometry than a body-scale
  // grid. Sample their support on both axes and cap the 16-bit index budget.
  const grid=(min,max,dimension)=>{
    const cells=Math.max(1,Math.ceil((max-min)/19));
    const result=Array.from({length:cells+1},(_,index)=>min+(max-min)*index/cells);
    for(const [x,y,ux,uy,rx,ry] of details) {
      const center=dimension===0?x:y;
      const radius=dimension===0?Math.hypot(ux*rx,uy*ry):Math.hypot(uy*rx,ux*ry);
      const stride=Math.max(1.4,Math.min(7,Math.min(rx,ry)/4));
      if(radius>105)continue;
      if(rx===0&&center>min&&center<max&&result.length<220&&!result.some(value=>value===center))result.push(center);
      if(rx===0)continue;
      for(let value=Math.max(min+1,center-radius-stride);value<Math.min(max,center+radius+stride);value+=stride) {
        if(result.length>=220)break;
        if(!result.some(coordinate=>Math.abs(coordinate-value)<.68))result.push(value);
      }
    }
    return result.sort((a,b)=>a-b);
  };
  const xGrid=grid(left,right,0), yGrid=grid(top,bottom,1);
  const cols=xGrid.length, rows=yGrid.length;
  const bytes=new Float32Array(cols*rows*4), index=[], vertices=[];
  const positions=[];
  for(let r=0;r<rows;r++)for(let c=0;c<cols;c++) {
    const x=xGrid[c],y=yGrid[r],idx=r*cols+c;
    positions.push([x,y]);
    bytes.set([x,y,x/w,y/h],idx*4);
    if(c<cols-1&&r<rows-1)index.push(idx,idx+1,idx+cols,idx+1,idx+cols+1,idx+cols);
  }
  return {positions,bytes,index:new Uint16Array(index),xGrid,yGrid};
}

function boneWeights(points) {
  const segments=LINKS.map(([a,b])=>{
    const p=points[a],q=points[b],dx=q[0]-p[0],dy=q[1]-p[1];
    return {x:p[0],y:p[1],dx,dy,den:Math.max(dx*dx+dy*dy,.1),confidence:Math.min(p[2],q[2])};
  });
  return (x,y)=>{
    const nearest=segments.map((s,i)=>{
      const t=Math.min(1,Math.max(0,((x-s.x)*s.dx+(y-s.y)*s.dy)/s.den));
      return [i,(x-s.x-t*s.dx)**2+(y-s.y-t*s.dy)**2+(1-s.confidence)*480];
    }).sort((a,b)=>a[1]-b[1]).slice(0,4);
    const weights=nearest.map(([i,d])=>[i,Math.exp(-(d-nearest[0][1])/840)]);
    const total=weights.reduce((sum,[,w])=>sum+w,0);
    return weights.map(([i,w])=>[i,w/total]);
  };
}

function matteDistance(matte,left,top,width,height,channel) {
  // Chamfer distance on the low-resolution source matte limits how far the
  // recorded scenery follows the performer. Units are matte pixels here.
  const out=new Float32Array(width*height);
  for(let i=0;i<out.length;i++) {
    const x=i%width,y=Math.floor(i/width);
    out[i]=matte.data[((top+y)*matte.width+left+x)*4+channel]>58?0:1e4;
  }
  for(let direction of [1,-1]) {
    for(let i=direction===1?0:out.length-1;i>=0&&i<out.length;i+=direction) {
      const x=i%width,y=Math.floor(i/width),prevY=y-direction;
      if(x-direction>=0&&x-direction<width)out[i]=Math.min(out[i],out[i-direction]+1);
      if(prevY<0||prevY>=height)continue;
      const row=prevY*width;
      out[i]=Math.min(out[i],out[row+x]+1);
      if(x>0)out[i]=Math.min(out[i],out[row+x-1]+Math.SQRT2);
      if(x<width-1)out[i]=Math.min(out[i],out[row+x+1]+Math.SQRT2);
    }
  }
  return out;
}

const clamp=(value,low,high)=>Math.min(high,Math.max(low,value));
const smooth=value=>value*value*(3-2*value);

function surfacePoint(moved,grid,x,y) {
  // Read the same triangle the GPU uses for this original-frame coordinate.
  const cell=(axis,value)=>{
    let hi=axis.length-1,lo=0;
    while(hi-lo>1) {
      const mid=(lo+hi)>>1;
      if(axis[mid]<=value)lo=mid;
      else hi=mid;
    }
    return [lo,clamp((value-axis[lo])/(axis[hi]-axis[lo]),0,1)];
  };
  const [column,u]=cell(grid.xGrid,x),[row,v]=cell(grid.yGrid,y);
  const cols=grid.xGrid.length, i=row*cols+column;
  const [a,b,c,d]=[moved[i],moved[i+1],moved[i+cols],moved[i+cols+1]];
  return [0,1].map(j=>u+v<=1?a[j]*(1-u-v)+b[j]*u+c[j]*v:
    b[j]*(1-v)+c[j]*(1-u)+d[j]*(u+v-1));
}

function sourceAtTriangle(x,y,grid,points) {
  const {index,positions}=grid;
  // The clicked pixel and the video shader share the same barycentric UVs.
  for(let i=0;i<index.length;i+=3) {
    const ia=index[i],ib=index[i+1],ic=index[i+2];
    const [ax,ay]=points[ia],[bx,by]=points[ib],[cx,cy]=points[ic];
    if(x<Math.min(ax,bx,cx)||x>Math.max(ax,bx,cx)||y<Math.min(ay,by,cy)||y>Math.max(ay,by,cy))continue;
    const ux=bx-ax,uy=by-ay,vx=cx-ax,vy=cy-ay;
    const det=ux*vy-uy*vx;
    if(det<=0)continue;
    const dx=x-ax,dy=y-ay;
    const u=(dx*vy-dy*vx)/det,v=(ux*dy-uy*dx)/det;
    if(u< -1e-8||v< -1e-8||u+v>1+1e-8)continue;
    const a=positions[ia],b=positions[ib],c=positions[ic];
    return [a[0]+u*(b[0]-a[0])+v*(c[0]-a[0]),a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])];
  }
  return [x,y];
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

export async function createRenderer(canvas, useUhd=false) {
  const timeline=await fetch("/timeline/timeline.json").then(response=>{
    if(!response.ok)throw new Error("Motion timeline unavailable.");
    return response.json();
  });
  const rasterScale=useUhd?3840/timeline.height:1;
  const augmentation=await fetch("/regions.json").then(response=>response.ok?response.json():null)
    .catch(()=>null);
  if(augmentation&&augmentation.frames.length!==timeline.frames.length)
    throw new Error("Shape regions do not match the footage timeline.");
  const cleanupTracks=augmentation ? await fetch("/cleanup-tracks.json").then(response=>response.ok?response.json():null) : null;
  if(cleanupTracks&&(cleanupTracks.version!==1||cleanupTracks.frames.length!==timeline.frames.length))
    throw new Error("Cleanup tracks do not match the footage timeline.");
  const hasSkin=augmentation ? await fetch("/skin/skin-000.png",{method:"HEAD"}).then(r=>r.ok).catch(()=>false) : false;
  const gl=canvas.getContext("webgl",{alpha:false,antialias:false,preserveDrawingBuffer:true});
  if(!gl)throw new Error("Movement control needs WebGL.");
  const pipeline=program(gl,timeline);
  const position=gl.getAttribLocation(pipeline,"p"),uv=gl.getAttribLocation(pipeline,"uv");
  const uniform=Object.fromEntries(["size","tile","kind","protect","frame","matte","skin","tone","raster","verticalTravel"]
    .map(k=>[k,gl.getUniformLocation(pipeline,k)]));
  gl.uniform1i(uniform.frame,0);gl.uniform1i(uniform.matte,1);gl.uniform1f(uniform.raster,rasterScale);gl.uniform1i(uniform.skin,2);
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
  const atlases=new Map();
  let requestRender;
  const setPageReady=callback=>{requestRender=callback;};
  const slots=timeline.grid**2;
  let wantedPage=0, activePage=-1;
  function loadPage(page) {
    if(page<0||page>=timeline.pages.length||atlases.has(page))return;
    const entry={textures:null};
    atlases.set(page,entry);
    const urls=["/timeline/"+timeline.pages[page][0]];
    if(hasSkin)urls.push("/skin/skin-"+String(page).padStart(3,"0")+".png");
    Promise.all(urls.map(fetchTexture)).then(bitmaps=>{
      {
        const matte=new OffscreenCanvas(bitmaps[0].width,bitmaps[0].height);
        const context=matte.getContext("2d",{willReadFrequently:true});
        context.drawImage(bitmaps[0],0,0);
        entry.matte=context.getImageData(0,0,matte.width,matte.height);
      }
      gl.activeTexture(gl.TEXTURE0);
      entry.textures=bitmaps.map(bitmap=>{
        const result=texture(bitmap,gl.LINEAR);
        bitmap.close();
        return result;
      });
      gl.bindTexture(gl.TEXTURE_2D,source);
      prune();
      if(page===wantedPage)requestRender?.();
    }).catch(error=>requestRender?.(error));
  }
  function prune() {
    for(const [page,entry] of atlases) {
      if(entry.textures&&page!==activePage&&(page<wantedPage-1||page>wantedPage+2)) {
        entry.textures.forEach(texture=>gl.deleteTexture(texture));
        atlases.delete(page);
      }
    }
  }
  function selectPage(page) {
    wantedPage=page;
    loadPage(page);
    loadPage(page+1);
    loadPage(page+2);
    return atlases.get(page).textures;
  }
  const quad=gl.createBuffer(),surface=gl.createBuffer(),triangles=gl.createBuffer();
  const bind=buffer=>{
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,16,0);
    gl.enableVertexAttribArray(uv);gl.vertexAttribPointer(uv,2,gl.FLOAT,false,16,8);
  };
  const [tw,th]=timeline.tile, grid=timeline.grid, height=timeline.height;
  let current=-1,layers=[],width=0,seenFrame=-1,renders=0,subjects=[],requestedSubjects=[],displayRegions={};
  let shapeMesh=null,motionMesh=null,motionScale=1,cleanupEffect=0,attachedCleanup=false;
  let heldForMatte=false, liveMotion=false;
  let pickSurface=null,protectedRect=null;
  function baseAt(i) {
    return timeline.frames[i][1].map(row=>Object.fromEntries(row.map(([x,y,c],n)=>[
      timeline.landmarks[n],[x/4,y/4,c/100]
    ])));
  }
  function frame(video,index,requireMatte=false) {
    if(video.readyState<2||video.videoHeight!==Math.round(height*rasterScale))return false;
    const [w]=timeline.frames[index];
    if(video.videoWidth!==Math.round(w*rasterScale))return false;
    const tile=index%slots,page=Math.floor(index/slots);
    const textures=selectPage(page);
    heldForMatte=Boolean(requireMatte&&!textures&&seenFrame>=0);
    if(heldForMatte)return false;
    if(w!==width) {
      // Pose geometry stays in source pixels at both raster sizes. Only the
      // viewport and decoded texture change when reviewing the UHD export.
      width=w;canvas.width=video.videoWidth;canvas.height=video.videoHeight;
      gl.viewport(0,0,canvas.width,canvas.height);
      gl.uniform2f(uniform.size,width,height);
      gl.bindBuffer(gl.ARRAY_BUFFER,quad);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,0,0,width,0,1,0,0,height,0,1,width,height,1,1]),gl.STATIC_DRAW);
    }
    if(current!==index) {
      current=index;
      layers=baseAt(index).map(points=>({points}));
      shapeMesh=null;motionMesh=null;
    }
    activePage=textures?page:-1;
    prune();
    gl.uniform2f(uniform.tile,(tile%grid)*tw,Math.floor(tile/grid)*th);
    const shot=timeline.shots.findIndex(([a,b])=>index>=a&&index<b);
    protectedRect=timeline.protected[shot];
    gl.uniform4f(uniform.protect,...protectedRect);

    if(textures)for(let i=0;i<textures.length;i++) {
      gl.activeTexture(gl.TEXTURE1+i);gl.bindTexture(gl.TEXTURE_2D,textures[i]);
    }
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,source);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,video);
    seenFrame=current;
    return true;
  }
  const inRect=(x,y,[left,top,right,bottom])=>x>=left&&x<right&&y>=top&&y<bottom;
  function sourcePoint(x,y) {
    if(!pickSurface||pickSurface.frame!==current||inRect(x,y,protectedRect)||
       (pickSurface.bounds&&!inRect(x,y,pickSurface.bounds)))return [x,y];
    return sourceAtTriangle(x,y,pickSurface.grid,pickSurface.points);
  }
  function isForeground(x,y) {
    return sourceVisible(...sourcePoint(x,y));
  }
  function sourceVisible(x,y) {
    const page=atlases.get(activePage)?.matte;
    if(!page||x<0||y<0||x>=width||y>=height)return false;
    const slot=current%slots;
    const ax=(slot%grid)*tw+Math.min(tw-1,Math.max(0,Math.floor(x/timeline.pixelScale)));
    const ay=Math.floor(slot/grid)*th+Math.min(th-1,Math.max(0,Math.floor(y/timeline.pixelScale)));
    return page.data[(ay*page.width+ax)*4]>65;
  }

  function repaint(grid,points,kind) {
    for(let i=0;i<points.length;i++) {
      grid.bytes[i*4]=points[i][0];
      grid.bytes[i*4+1]=points[i][1];
    }
    gl.uniform1i(uniform.kind,kind);
    bind(surface);gl.bufferData(gl.ARRAY_BUFFER,grid.bytes,gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,triangles);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,grid.index,gl.DYNAMIC_DRAW);
    gl.drawElements(gl.TRIANGLES,grid.index.length,gl.UNSIGNED_SHORT,0);
  }

  function moveRegions(regions,project) {
    return Object.fromEntries(Object.entries(regions).map(([key,shapes])=>[key,shapes.map(shape=>{
      if(!shape)return null;
      const [x,y,ux,uy,rx,ry]=shape;
      const [cx,cy]=project(x,y);
      const [ax,ay]=project(x+ux*rx*.2,y+uy*rx*.2);
      const [bx,by]=project(x-uy*ry*.2,y+ux*ry*.2);
      const across=Math.max(.5,Math.hypot(ax-cx,ay-cy));
      return [cx,cy,(ax-cx)/across,(ay-cy)/across,across*5,Math.max(2.5,Math.hypot(bx-cx,by-cy)*5)];
    })]));
  }

  function drawMotion(state,base,details,signature,warp,response) {
    if(!motionMesh||motionMesh.signature!==signature) {
      const grid=mesh(width,height,details);
      const image=atlases.get(activePage).matte, slot=current%slots;
      const originX=(slot%timeline.grid)*tw,originY=Math.floor(slot/timeline.grid)*th;
      const shot=timeline.shots.findIndex(([a,b])=>current>=a&&current<b);
      const [left,top,right,bottom,slope=0]=timeline.reflection[shot];
      const grids=layers.map((layer,channel)=>{
        const weights=boneWeights(layer.points);
        const distance=matteDistance(image,originX,originY,tw,th,channel);
        return grid.positions.map(([x,y])=>{
          const col=clamp(Math.floor(x/timeline.pixelScale),0,tw-1);
          const row=clamp(Math.floor(y/timeline.pixelScale),0,th-1);
          const value=channel&&
            (x<left-24||x>right+24||y<top-24||y>bottom+slope*x+24)?Infinity:distance[row*tw+col]*timeline.pixelScale;
          return {distance:value,weights:value<=330?weights(x,y):[]};
        });
      });
      motionMesh={grid,grids,signature};
    }

    const {grid,grids}=motionMesh;
    requestedSubjects=layers.map((layer,index)=>evaluated(layer.points,state,index===1));
    const poseMaps=layers.map((layer,index)=>LINKS.map(([a,b])=>
      mapping(layer.points[a],layer.points[b],requestedSubjects[index][a],requestedSubjects[index][b])));
    const magnitude=Math.hypot(state.root[0],state.root[1]-state.lift);
    const radius=Math.min(320,Math.max(132,magnitude*2.55));
    const marginX=Math.min(width*.32,Math.max(82,Math.abs(state.root[0])*1.9));
    const marginY=Math.min(height*.3,Math.max(88,Math.abs(state.root[1]-state.lift)*1.9));
    const secondary=secondaryField(base,response);
    const targets=grid.positions.map(([x,y],i)=>{
      let dx=0,dy=0,total=0;
      for(let layer=0;layer<layers.length;layer++) {
        const {distance,weights}=grids[layer][i];
        if(distance>=radius)continue;
        const coverage=1-smooth(distance/radius);
        const [sx,sy]=layer===0?warp(x,y):[x,y];
        let mx=0,my=0;
        for(const [link,weight] of weights) {
          const [r,s,px,py]=poseMaps[layer][link];
          mx+=(sx*r-sy*s+px)*weight;my+=(sx*s+sy*r+py)*weight;
        }
        const [residualX,residualY]=layer===0?secondary(x,y):[0,0];
        dx+=(mx-x+residualX)*coverage;dy+=(my-y+residualY)*coverage;total+=coverage;
      }
      return [x+dx/Math.max(1,total)*edgeAxisWeight(x,width,marginX),
        y+dy/Math.max(1,total)*edgeAxisWeight(y,height,marginY)];
    });
    const fitted=fitTransport(grid.positions,targets,grid.index,width,height);
    motionScale=fitted.scale;
    const project=(x,y)=>surfacePoint(fitted.points,grid,x,y);
    subjects=layers.map(layer=>Object.fromEntries(Object.entries(layer.points)
      .map(([key,[x,y]])=>[key,project(x,y)])));
    displayRegions=moveRegions(base,project);
    gl.uniform1f(uniform.verticalTravel,Math.abs(state.root[1]-state.lift));
    pickSurface={frame:current,grid,points:fitted.points};
    repaint(grid,fitted.points,6);
  }

  function draw(state,poseActive,adjustments={},tone=[0,0,0],cleaned=false,response={},observation=null,points={}) {
    if(current<0)return;
    const named=augmentation?.frames[current]??{};
    const observed={...named};
    for(const [key,point] of Object.entries(points)) {
      const shape=pointShape(point,named);
      if(shape&&sourceVisible(shape[0],shape[1]))observed[key]=[shape];
    }
    const stabilized=cleaned&&cleanupTracks?.frames[current];
    const base=stabilized?Object.fromEntries(Object.entries(observed).map(([key,shapes])=>
      [key,adjustments[key]&&stabilized[key]?
        followObservation(stabilized[key],shapes,observation?.[key]):shapes])):observed;
    const entries=Object.entries(base).filter(([key])=>adjustments[key]);
    const active=(poseActive||entries.length>0)&&activePage>=0;
    const graded=hasSkin&&activePage>=0&&tone.some(Boolean);
    liveMotion=Boolean(active&&poseActive);
    gl.uniform3f(uniform.tone,...(graded?tone:[0,0,0]));
    gl.disable(gl.BLEND);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
    gl.uniform1i(uniform.kind,graded?4:0);
    bind(quad);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
    subjects=[];requestedSubjects=[];motionScale=1;cleanupEffect=0;attachedCleanup=false;
    pickSurface=null;
    displayRegions=base;
    renders++;
    if(!active)return;

    const shaped=Object.fromEntries(entries);
    const rawShapes=Object.fromEntries(entries.map(([key])=>[key,observed[key]]));
    attachedCleanup=Boolean(stabilized&&entries.some(([key,shapes])=>JSON.stringify(shapes)!==JSON.stringify(observed[key])));
    const signature=(cleaned?"clean:":"")+(observation?"flow:":"")+
      entries.map(([key])=>points[key]?key+"@"+points[key].radius:key).join(",");
    const details=entries.flatMap(([,items])=>items).filter(Boolean)
      .sort((a,b)=>Math.min(a[4],a[5])-Math.min(b[4],b[5]));
    const raw=(x,y)=>entries.length?deformation(x,y,rawShapes,adjustments):[x,y];
    const pins=cleaned?cleanupTracks?.pins?.[current]:null;
    const refinement=pins?details.concat(entries.flatMap(([key])=>
      (pins[key]??[]).map(([x,y])=>[x,y,1,0,0,0]))):details;
    const clean=cleaned&&entries.length?compileCleanup(shaped,adjustments,pins??{}):null;
    const warp=clean?(x,y)=>{
      const [sx,sy]=raw(x,y), result=clean(x,y);
      cleanupEffect=Math.max(cleanupEffect,Math.hypot(result[0]-sx,result[1]-sy));
      return result;
    }:raw;
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    if(poseActive) {
      drawMotion(state,base,refinement,signature,warp,response);
      return;
    }

    // Shape-only edits keep the old source/transported matte blend, without
    // changing unrelated background in the surrounding scene.
    const extents=details.map(([x,y,ux,uy,rx,ry])=>{
      const a=Math.hypot(ux*rx,uy*ry)+22,b=Math.hypot(uy*rx,ux*ry)+22;
      return [x-a,y-b,x+a,y+b];
    });
    const left=Math.max(0,Math.floor(Math.min(...extents.map(r=>r[0]))));
    const top=Math.max(0,Math.floor(Math.min(...extents.map(r=>r[1]))));
    const right=Math.min(width,Math.ceil(Math.max(...extents.map(r=>r[2]))));
    const bottom=Math.min(height,Math.ceil(Math.max(...extents.map(r=>r[3]))));
    if(right<=left||bottom<=top)return;
    if(!shapeMesh||shapeMesh.signature!==signature)
      shapeMesh={signature,grid:mesh(width,height,refinement,layers[0].points)};
    const {grid}=shapeMesh;
    const desired=grid.positions.map(([x,y])=>warp(x,y));
    const {points:fitted}=fitTransport(grid.positions,desired,grid.index,width,height);
    const bounds=[left,top,right,bottom];
    displayRegions=moveRegions(base,(x,y)=>inRect(x,y,bounds)&&!inRect(x,y,protectedRect)?
      surfacePoint(fitted,grid,x,y):[x,y]);
    subjects=[evaluated(layers[0].points,state)];
    pickSurface={frame:current,grid,points:fitted,bounds};
    gl.enable(gl.SCISSOR_TEST);
    gl.scissor(left*rasterScale,(height-bottom)*rasterScale,(right-left)*rasterScale,(bottom-top)*rasterScale);
    repaint(grid,fitted,5);
    gl.disable(gl.SCISSOR_TEST);
  }
  return {timeline,augmentation,hasSkin,frame,draw,baseAt,setPageReady,isForeground,sourcePoint,regions:()=>displayRegions,
    inspect:()=>({frame:seenFrame,renders,width,height,subjects,requestedSubjects,motionScale,cleanupEffect,attachedCleanup,heldForMatte,liveMotion,
      outputWidth:canvas.width,outputHeight:canvas.height,matteReady:activePage>=0,plateReady:activePage>=0})};
}
