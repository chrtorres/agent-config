export function pickRegion({x,y,scale=1},regions,accept=()=>true) {
  let closest=null, best=Infinity;
  // Allow one CSS pixel of aiming tolerance on a narrow region. The tolerance
  // shrinks in source pixels as the video or magnifier is zoomed in.
  const tolerance=Math.min(2,Math.max(0,scale));
  for(const [key,shapes] of Object.entries(regions)) {
    if(!accept(key))continue;
    for(const [index,shape] of shapes.entries()) {
      if(!shape)continue;
      const [cx,cy,ux,uy,rx,ry]=shape;
      const dx=x-cx,dy=y-cy;
      const across=(dx*ux+dy*uy)/(rx+tolerance),along=(dy*ux-dx*uy)/(ry+tolerance);
      const distance=across**2+along**2;
      if(distance>.83)continue;
      // Prefer a tightly framed feature in an overlap near its center. A
      // distant small ellipse does not displace a deliberate broad-region hit.
      const specificity=.34/(1+Math.sqrt(rx*ry)/25);
      const score=distance-specificity*(1-distance);
      if(score<best) {
        best=score;
        closest={key,index};
      }
    }
  }
  return closest;
}
