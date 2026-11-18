export function percent(value){return Number.isFinite(value)?value.toFixed(1).replace(/\.0$/,''):'—'}
export function bytes(value){if(!Number.isFinite(value))return '—';const unit=value>=1024**3?'GiB':'MiB';return `${(value/(unit==='GiB'?1024**3:1024**2)).toFixed(1)} ${unit}`}
export function uptime(value){if(!Number.isFinite(value))return '—';const days=Math.floor(value/86400),hours=Math.floor(value%86400/3600),minutes=Math.floor(value%3600/60);return days?`${days}d ${hours}h`:`${hours}h ${minutes}m`}
export const profileInfo={
 baseline:{icon:'◫',description:'Services, capacity, inodes, and package state.',count:5},
 startup:{icon:'◷',description:'Failed units and the shape of your startup.',count:4},
 storage:{icon:'▱',description:'Filesystem space, devices, and temperatures.',count:4},
 logs:{icon:'≋',description:'A bounded look at the last 15 minutes.',count:2},
 context:{icon:'⌁',description:'Installation state and local network context.',count:3}
};
export function findings(snapshot,job){
 const items=[];
 if(snapshot?.disk?.percent>=85)items.push({level:'review',title:'Root capacity deserves a look',text:`${percent(snapshot.disk.percent)}% in use on /. Review what is growing before planning cleanup.`});
 if(snapshot?.memory?.percent>=90)items.push({level:'review',title:'Available memory is low',text:'Over 90% is in use. Compare pressure and interval CPU before attributing slowness.'});
 if(snapshot?.cpu_percent>=90)items.push({level:'review',title:'High CPU in this interval',text:'A single sample is not a sustained trend. Check the activity chart and process intervals.'});
 if(snapshot?.reboot_required)items.push({level:'review',title:'Reboot marker is present',text:'The system reports a reboot requirement. No restart is initiated.'});
 const results=job?.results||[], review=results.filter(r=>r.assessment==='review'),limited=results.filter(r=>r.assessment==='limited');
 if(review.length)items.push({level:'review',title:`${review.length} check${review.length===1?'':'s'} to review`,text:review.map(r=>r.title).join(' · ')+'. Open the command evidence for context.'});
 if(limited.length)items.push({level:'limited',title:`${limited.length} coverage gap${limited.length===1?'':'s'}`,text:'Some checks were unavailable or incomplete. These are unknowns, not passing results.'});
 if(snapshot&&(snapshot.cpu_percent==null||!snapshot.memory||!snapshot.disk))items.push({level:'limited',title:'Some resource signals are pending',text:'Missing counters and a first CPU reading remain unknown. Wait for an interval or review coverage.'});
 if(snapshot&&!items.length)items.push({level:'observed',title:'Sampled resources below alert thresholds',text:'CPU <90%, memory <90%, root capacity <85%. This does not establish overall system health.'});
 if(!job)items.push({level:'limited',title:'Health checks have not run',text:'Start with a quick baseline to inspect services, capacity, and package state.'});
 else if(job.status==='cancelled')items.push({level:'limited',title:'Diagnostic was cancelled',text:'Only completed results are available. Unrun checks remain unverified.'});
 return items;
}
export function coverage(snapshot,job){
 const completed=job?.results||[];
 const group=ids=>{const all=ids.map(id=>completed.find(r=>r.id===id));return all.every(r=>r&&r.assessment==='observed')?'observed':all.some(r=>r?.assessment==='review')?'review':'limited'};
 return [
  ['CPU & memory',snapshot?.cpu_percent!=null&&snapshot?.memory?'observed':'limited','Interval CPU, available memory, swap occupancy, and host-visible pressure. Container limits are not normalized.'],
  ['Filesystem capacity',snapshot?.disk?'observed':'limited','Root mount capacity only. Targeted checks add inode and device output.'],
  ['Startup & services',group(['services','user-services','boot','boot-blame']),'System and user failed units, boot timing, and overlapping service durations.'],
  ['Recent errors',group(['kernel','journal']),'Visible journal entries from this boot and the last 15 minutes, capped at 40 per check.'],
  ['Packages & local network',group(['packages','links','routes']),'Installation state, local routes, and cumulative interface counters. No update refresh or remote probes.'],
  ['Drive health & graphics','limited','SMART/NVMe attributes, GPU health, and hardware self-tests are outside first-pass coverage.'],
  ['Thermal interpretation','limited','Optional sensors output is available as evidence. Vendor limits and thermal trends need further investigation.']
 ];
}
export function pathFor(history,key){
 // Preserve gaps instead of drawing a fabricated line through missing samples.
 const start=Date.parse(history[0]?.collected_at),end=Date.parse(history.at(-1)?.collected_at),timed=Number.isFinite(start)&&end>start;
 let path='',open=false;history.forEach((point,i)=>{const value=point[key];if(!Number.isFinite(value)){open=false;return}const fraction=timed?(Date.parse(point.collected_at)-start)/(end-start):i/Math.max(1,history.length-1);const x=37+fraction*651,y=184-Math.max(0,Math.min(100,value))*1.67;path+=`${open?'L':'M'}${x.toFixed(1)},${y.toFixed(1)} `;open=true});return path.trim();
}
export function report(snapshot,history,job){return {format:'fieldwork-report-v1',exported_at:new Date().toISOString(),source:snapshot?.source||job?.source,latest_snapshot:snapshot,session_samples:history,latest_diagnostic:job,coverage:coverage(snapshot,job),limits:['Read-only local observation; no repairs or remote probes.','Synthetic demo data is not evidence about this host.','Thresholds are triage heuristics; this is not hardware or security certification.','Latest job only; browser chart clears on reload.']}}
