import {escapeHTML as e,bytes,percent,filterVolumes} from './core.mjs';
const $=id=>document.getElementById(id);
const paths={grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',drive:'M4 3h16v18H4z M8 7h8 M8 11h8 M16 17h.01',layers:'m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',activity:'M2 12h4l3-8 6 16 3-8h4',shield:'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z m-4 9 3 3 5-6',lock:'M6 11h12v10H6z M8 11V7a4 4 0 0 1 8 0v4',terminal:'M3 4h18v16H3z m4 4 4 4-4 4 m6 0h4',download:'M12 3v12 m-5-5 5 5 5-5 M4 16v5h16v-5',refresh:'M20 8a8 8 0 1 0 0 8 M20 3v5h-5',search:'M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0 m-2 4 6 6',arrow:'M5 12h14 m-5-5 5 5-5 5',pie:'M10 3a9 9 0 1 0 11 11H10z M14 2v8h8a9 9 0 0 0-8-8',alert:'m12 3 10 18H2z M12 9v5 m0 3h.01'};
const icon=name=>`<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="${paths[name]||paths.drive}"/></svg>`;
document.querySelectorAll('[data-icon]').forEach(node=>node.innerHTML=icon(node.dataset.icon));
const defaults={source:'live',units:'binary',view:'overview',auto:true};
let preferences={};
try{preferences=JSON.parse(localStorage.getItem('atlas.preferences')||'{}')}catch{}
const state={...defaults,...preferences,snapshot:null,history:[],busy:false,request:0,controller:null,query:'',filter:'all',sort:'usage',range:60,dialogDrive:null};
if(!['live','demo'].includes(state.source))state.source='live';
if(!['binary','decimal'].includes(state.units))state.units='binary';
if(location.hash==='#health')state.view='health';
if(!['overview','drives','volumes','activity','health'].includes(state.view))state.view='overview';
state.auto=state.auto!==false;
const fmt=v=>bytes(v,state.units);
const healthLabels={healthy:'SMART passed',failing:'SMART failing',warning:'SMART findings',unknown:'Health unknown',unavailable:'Health unavailable'};
function save(){try{localStorage.setItem('atlas.preferences',JSON.stringify({source:state.source,units:state.units,view:state.view,auto:state.auto}))}catch{}}
const titles={overview:['A little clarity.<br>A lot of space.','Know what’s used, what’s available, and what needs your attention.','Overview'],drives:['Every drive. In view.','Compare physical devices and explore the partitions inside.','Physical drives'],volumes:['Room for what’s next.','Find available capacity and see which mounted volumes need attention.','Volumes'],activity:['Follow the flow.','Live read and write activity, backed by your recorded samples.','Activity'],health:['Stay one step ahead.','Capacity findings and hardware health, with clear coverage limits.','Health & insights']};
function setView(view){
  state.view=view;save();
  document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===view);b.toggleAttribute('aria-current',b.dataset.view===view);if(b.dataset.view===view)b.setAttribute('aria-current','page')});
  $('page-title').innerHTML=titles[view][0];$('page-subtitle').textContent=titles[view][1];$('breadcrumb-view').textContent=titles[view][2];
  const visible={overview:['summary-section','overview-grid','drives-section','volumes-section'],drives:['drives-section'],volumes:['volumes-section','unmounted-section'],activity:['activity-section'],health:['health-section']}[view];
  for(const id of ['summary-section','overview-grid','drives-section','volumes-section','unmounted-section','activity-section','health-section'])$(id).hidden=!visible.includes(id);
}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
document.querySelector('.brand').addEventListener('click',event=>{event.preventDefault();setView('overview');window.scrollTo({top:0})});
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>{setView(b.dataset.go);$('page-title').scrollIntoView({block:'start'})}));
function metric(label,value,note,symbol,extra=''){return `<article class="metric ${extra}"><div class="metric-top"><span>${label}</span>${icon(symbol)}</div><strong>${e(value)}</strong><p>${e(note)}</p></article>`}
function renderSummary(){
  const t=state.snapshot.totals;
  $('summary-section').innerHTML=metric('Physical capacity',fmt(t.physical),`${t.drive_count} physical drives detected`,'drive')+metric('Space used',fmt(t.used),'Across accessible mounted filesystems','pie')+metric('Available to you',fmt(t.available),'Excludes filesystem reserves','layers')+metric('Needs attention',String(t.attention_count),t.attention_count?'Capacity or device health findings':'No capacity or known health findings','alert','attention');
  const used=t.total?100*t.used/t.total:0,available=t.total?100*(t.used+t.available)/t.total:0;
  $('capacity-chart').innerHTML=t.total?`<div class="capacity-content"><div class="donut" style="--used:${used}%;--available:${available}%" role="img" aria-label="Mounted allocation: ${e(fmt(t.used))} used, ${e(fmt(t.available))} available, ${e(fmt(t.reserved))} reserved"><div class="donut-center"><strong id="used-percentage">${e(percent(t.percent))}</strong><span>usable space used</span></div></div><div class="capacity-legend"><div class="legend-row"><span><i class="legend-dot"></i>Used</span><strong id="used-bytes">${e(fmt(t.used))}</strong></div><div class="legend-row"><span><i class="legend-dot available"></i>Available</span><strong>${e(fmt(t.available))}</strong></div><div class="legend-row"><span><i class="legend-dot reserved"></i>Reserved</span><strong>${e(fmt(t.reserved))}</strong></div></div></div>`:'<p class="empty-state">No accessible mounted filesystem capacity. Physical devices may still be present.</p>';
}
function renderInsights(){
  const s=state.snapshot;
  let html=s.findings.slice(0,2).map(f=>`<article class="insight-item"><span class="insight-kicker">${f.kind==='capacity'?'CAPACITY CHECK':'HARDWARE CHECK'} · ${e(f.level.toUpperCase())}</span><h3>${e(f.title)}</h3><p>${e(f.detail)}</p></article>`).join('');
  if(!html)html='<article class="insight-item normal"><span class="insight-kicker">CAPACITY LOOKS COMFORTABLE</span><h3>A little breathing room.</h3><p>No mounted volumes are above the 80% warning threshold.</p></article>';
  if(s.findings.length<2){const missing=s.drives.length-s.coverage.hardware_health;html+=`<article class="insight-item normal"><span class="insight-kicker">${missing?'KNOW YOUR COVERAGE':'PARTITION VISIBILITY'}</span><h3>${missing?`${missing} drive${missing===1?'':'s'} without a health reading`:`${s.totals.unmounted_count} unmounted partitions`}</h3><p>${missing?'SMART access is unavailable for some devices. Open Health & insights for the reason.':'Unmounted capacity may contain data. Atlas never counts it as free space.'}</p></article>`}
  $('insight-cards').innerHTML=html;
}
function partitionTrack(drive){
  if(!drive.partitions.length)return '<span class="partition-segment" style="width:100%"></span>';
  return drive.partitions.map(p=>`<span class="partition-segment ${p.state==='unmounted'?'unmounted':''}" style="width:${drive.size?Math.min(100,100*p.size/drive.size):0}%" title="${e(p.name)} · ${e(fmt(p.size))} · ${e(p.state)}"></span>`).join('');
}
function renderDrives(){
  const drives=state.snapshot.drives;
  $('drive-count').textContent=String(drives.length);$('drive-label').textContent=String(drives.length);
  $('drive-cards').innerHTML=drives.length?drives.map(d=>`<article class="drive-card"><div class="drive-card-body"><div class="drive-card-top"><span class="drive-icon">${icon('drive')}</span><span class="transport">${e(d.transport)} · ${e(d.media)}</span></div><h3 title="${e(d.model)}">${e(d.model)}</h3><div class="drive-meta"><span>${e(d.path)}</span><span aria-hidden="true">·</span><span class="drive-size">${e(fmt(d.size))}</span></div><div class="drive-usage"><span>Mounted usage</span><strong>${d.usage?e(percent(d.usage.percent))+' used':'Unknown'}</strong></div><div class="partition-track" role="img" aria-label="${e(d.partitions.length)} partitions on ${e(d.name)}">${partitionTrack(d)}</div><div class="partition-caption"><span>${d.partitions.length} partition${d.partitions.length===1?'':'s'}</span><span>${d.usage?e(fmt(d.usage.available))+' available':'No exclusive mounted capacity'}</span></div></div><div class="drive-card-footer"><span class="health-mini ${e(d.health.state)}"><i></i>${e(healthLabels[d.health.state]||'Health unknown')}</span><button class="drive-detail" data-drive="${e(d.id)}" aria-label="View details for ${e(d.name)}">View details <span aria-hidden="true">↗</span></button></div></article>`).join(''):'<div class="panel empty-state">No physical drives returned by the collector.</div>';
}
function renderVolumes(){
  if(!state.snapshot)return;
  const all=state.snapshot.volumes,volumes=filterVolumes(all,state.query,state.filter,state.sort);
  $('volume-label').textContent=`${all.length} mounted`; 
  $('volume-rows').innerHTML=volumes.length?volumes.map(v=>`<tr><td><strong>${e(v.label||v.path)}</strong><span class="mount" title="${e(v.mountpoints.join(' · '))}">${e(v.mountpoint)}</span></td><td data-label="Format"><span class="format-tag">${e(v.fstype)}</span></td><td data-label="Capacity">${e(fmt(v.total))}</td><td data-label="Space used"><div class="usage-cell"><span class="usage-track" aria-hidden="true"><span class="usage-fill ${e(v.severity)}" style="width:${v.percent===null?0:Math.min(100,v.percent)}%"></span></span><span>${e(percent(v.percent))}</span></div></td><td data-label="Available">${e(fmt(v.available))}</td><td data-label="Status"><span class="status ${e(v.severity)}">${v.severity==='normal'?'Normal':v.severity==='warning'?'Watch capacity':v.severity==='critical'?'High usage':'Usage unknown'}</span></td></tr>`).join(''):`<tr><td colspan="6" class="empty-cell">${all.length?'No volumes match your filters. Try another path or show all volumes.':'No mounted volumes found. Usage is unknown for unmounted devices.'}</td></tr>`;
  $('volume-results').textContent=`Showing ${volumes.length} of ${all.length} volumes · Usage % = used ÷ (used + available). Reserved space is excluded from available capacity.`;
  const other=state.snapshot.partitions.filter(p=>p.state!=='mounted');
  $('unmounted-list').innerHTML=other.length?other.map(p=>`<div class="unmounted-row"><div><strong>${e(p.path)} ${p.label?'· '+e(p.label):''}</strong><small>${e(p.fstype)} · ${e(p.drive_ids.join(', '))}</small></div><div>${e(fmt(p.size))}<span class="status unknown">${p.state==='swap'?'Swap':'Unmounted · usage unknown'}</span></div></div>`).join(''):'<p class="empty-state">All discovered partitions have a mount point.</p>';
}
function renderActivity(){
  const samples=state.history.slice(-state.range),known=samples.filter(s=>s.read_bps!==null&&s.write_bps!==null);
  const last=known.at(-1),rate=value=>value===undefined||value===null?'Unknown':fmt(value)+'/s';
  $('activity-metrics').innerHTML=`<div class="activity-stat"><small>Latest read</small><strong>${e(rate(last?.read_bps))}</strong></div><div class="activity-stat"><small>Latest write</small><strong>${e(rate(last?.write_bps))}</strong></div><div class="activity-stat"><small>Recorded samples</small><strong>${samples.length}</strong></div>`;
  $('history-caption').textContent=samples.length?`${new Date(samples[0].captured_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})} — ${new Date(samples.at(-1).captured_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}`:'No samples yet';
  if(known.length<2){$('activity-chart').innerHTML='<div class="activity-empty">Building your activity history. Two interval samples are needed to draw a chart.<br>Keep live updates on, or refresh after a few seconds.</div>';return}
  const max=Math.max(1,...known.flatMap(s=>[s.read_bps,s.write_bps]))*1.12;
  // Sample-order x-axis avoids implying interpolation over paused periods.
  const segments=key=>{let groups=[],group=[];for(let i=0;i<samples.length;i++){const s=samples[i];if(!Number.isFinite(s[key])){if(group.length)groups.push(group);group=[];continue}group.push(`${(i*800/Math.max(1,samples.length-1)).toFixed(2)},${(160-s[key]/max*150).toFixed(2)}`)}if(group.length)groups.push(group);return groups.map(points=>`<polyline points="${points.join(' ')}" fill="none" stroke="${key==='read_bps'?'#2f654c':'#bc7a35'}" stroke-width="2.5" vector-effect="non-scaling-stroke"/>`).join('')};
  $('activity-chart').innerHTML=`<div class="activity-scale"><span>Throughput · shared scale</span><span>0 — ${e(rate(max))}</span></div><div class="activity-plot"><svg viewBox="0 0 800 180" preserveAspectRatio="none" role="img" aria-label="Read and write throughput across ${samples.length} recorded samples. Peak scale ${e(rate(max))}.">${segments('read_bps')}${segments('write_bps')}</svg></div>`;
}
function renderHealth(){
  const s=state.snapshot;
  $('smart-scan').disabled=state.source!=='live'||scanPolling;
  $('health-cards').innerHTML=s.drives.map(d=>`<article class="health-card"><span class="status ${e(d.health.state)}">${e(healthLabels[d.health.state]||'Health unknown')}</span><h3>${e(d.model)}</h3><p>${e(d.path)} · ${e(d.health.reason)}</p>${d.health.jit?`<p>Authorized snapshot · ${e(new Date(d.health.collected_at).toLocaleString())}. Rescan to update.</p>`:''}<div class="health-reading"><span>Temperature</span><strong>${Number.isFinite(d.health.temperature_c)?e(d.health.temperature_c)+' °C':'Unknown'}</strong></div><div class="health-reading"><span>Power-on hours</span><strong>${Number.isFinite(d.health.power_on_hours)?e(d.health.power_on_hours):'Unknown'}</strong></div></article>`).join('')||'<p class="empty-state">No physical devices to inspect.</p>';
  $('coverage-content').innerHTML=s.findings.map(f=>`<p><span class="status ${e(f.level)}">${e(f.level)}</span> <strong>${e(f.title)}</strong><br>${e(f.detail)}</p>`).join('')+`<p>Mounted filesystem usage: <strong>${e(s.coverage.usage)}</strong>. Hardware health readings: <strong>${s.coverage.hardware_health} of ${s.drives.length} drives</strong>. Capacity warnings begin at 80%; critical capacity begins at 90%.</p><p>SMART health is device-reported. Missing tools, device support, and permissions can prevent a reading. Automatic updates stay unprivileged; explicit SMART scans use system authentication. Unmounted partitions, file contents, and long-term failure predictions are outside its coverage.</p><p>History retains up to 720 samples locally, taken when this dashboard requests fresh data. I/O requires two counter readings. Capacity changes can also reflect attached or detached volumes.</p>`;
  $('collection-evidence').textContent=JSON.stringify({captured_at:s.captured_at,source:s.source,commands:s.evidence,issues:s.issues},null,2);
}
function render(){
  const s=state.snapshot;
  $('loading').hidden=true;$('dashboard').hidden=false;$('export').disabled=false;
  $('host-name').textContent=s.host;$('demo-notice').hidden=state.source!=='demo';
  $('partial-notice').hidden=!s.issues.length;$('partial-notice').textContent=s.issues.length?`Partial coverage: ${s.issues.join(' · ')}`:'';
  $('nav-alert').hidden=!s.findings.length;
  renderSummary();renderInsights();renderDrives();renderVolumes();renderActivity();renderHealth();setView(state.view);updateSync();
}
function updateSync(){
  $('auto-update').setAttribute('aria-pressed',String(state.auto));$('auto-label').textContent=state.auto?'Live updates · 10s':'Updates paused';
  if(state.snapshot)$('sync-text').textContent=`${state.source==='demo'?'Demo data':'Live host'} · Updated ${new Date(state.snapshot.captured_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}${state.auto?'':' · Paused'}`;
}
async function getJSON(url,signal){const response=await fetch(url,{signal,cache:'no-store'});let data;try{data=await response.json()}catch{throw Error('The collector returned an unreadable response.')}if(!response.ok)throw Error(data.error||`Collector returned HTTP ${response.status}`);return data}
async function load(force=false){
  if(state.busy&&!force)return;
  state.controller?.abort();const controller=new AbortController(),id=++state.request;state.controller=controller;state.busy=true;
  $('refresh').disabled=true;$('refresh').setAttribute('aria-busy','true');
  try{
    const source=state.source;
    // History follows snapshot so its newest persisted sample is included.
    const snapshot=await getJSON(`/api/snapshot?source=${source}`,controller.signal);
    const history=await getJSON(`/api/history?source=${source}`,controller.signal);
    if(id!==state.request)return;
    if(snapshot.source!==source||!Array.isArray(snapshot.drives)||!Array.isArray(snapshot.volumes)||!Array.isArray(snapshot.partitions)||!Array.isArray(snapshot.findings)||!Array.isArray(snapshot.issues)||!snapshot.totals||!snapshot.coverage||!Array.isArray(history.samples))throw Error('The collector returned an unexpected data contract.');
    state.snapshot=snapshot;state.history=history.samples;
    $('error-notice').hidden=true;$('connection').classList.remove('stale');render();
  }catch(error){
    if(error.name==='AbortError'||id!==state.request)return;
    $('loading').hidden=true;$('error-notice').hidden=false;$('connection').classList.add('stale');
    $('error-text').textContent=`${state.snapshot?'Showing the last successful sample. ':''}${error.message}`;
    $('sync-text').textContent=state.snapshot?'Connection interrupted · data is stale':'Collector unavailable · no data yet';
  }finally{if(id===state.request){state.busy=false;$('refresh').disabled=false;$('refresh').removeAttribute('aria-busy')}}
}
$('refresh').addEventListener('click',()=>load());$('retry').addEventListener('click',()=>load());
$('auto-update').addEventListener('click',()=>{state.auto=!state.auto;save();updateSync();if(state.auto)load()});
$('source').value=state.source;$('units').value=state.units;
$('source').addEventListener('change',()=>{state.source=$('source').value;state.snapshot=null;state.history=[];save();$('dashboard').hidden=true;$('export').disabled=true;$('loading').hidden=false;$('error-notice').hidden=true;$('demo-notice').hidden=state.source!=='demo';$('sync-text').textContent='Reading your storage…';load(true)});
$('units').addEventListener('change',()=>{state.units=$('units').value;save();if(state.snapshot)render()});
$('volume-search').addEventListener('input',()=>{state.query=$('volume-search').value;renderVolumes()});
$('volume-filter').addEventListener('change',()=>{state.filter=$('volume-filter').value;renderVolumes()});
$('volume-sort').addEventListener('change',()=>{state.sort=$('volume-sort').value;renderVolumes()});
$('history-range').addEventListener('change',()=>{state.range=Number($('history-range').value);renderActivity()});
function openDrive(id){
  const d=state.snapshot.drives.find(d=>d.id===id);if(!d)return;state.dialogDrive=id;
  $('dialog-title').textContent=d.model;
  $('dialog-content').innerHTML=`<dl class="detail-facts"><div><dt>Device</dt><dd>${e(d.path)}</dd></div><div><dt>Physical capacity</dt><dd>${e(fmt(d.size))}</dd></div><div><dt>Connection</dt><dd>${e(d.transport)} · ${e(d.media)}</dd></div><div><dt>Mounted space available</dt><dd>${d.usage?e(fmt(d.usage.available)):'Unknown'}</dd></div><div><dt>Hardware health</dt><dd>${e(healthLabels[d.health.state])}</dd></div><div><dt>Usage on mounted filesystems</dt><dd>${d.usage?e(percent(d.usage.percent)):'Unknown'}</dd></div></dl><h3>Partition layout</h3>${d.partitions.map(p=>`<div class="detail-partition"><div><strong>${e(p.name)}</strong><small>${e(p.label||p.fstype)} · ${e(p.mountpoints.join(', ')||'No mount point')}</small></div><div>${e(fmt(p.size))}<br><span class="status ${p.state==='mounted'?'normal':'unknown'}">${e(p.state)}</span></div></div>`).join('')||'<p class="dialog-note">No child partitions reported. This drive may contain a whole-device filesystem.</p>'}<p class="dialog-note">${e(d.health.reason)}. Partition layout shows physical allocation. Mounted usage describes accessible filesystems; unmounted and shared filesystem usage is unknown for this drive.</p>`;
  $('drive-dialog').showModal();
}
$('drive-cards').addEventListener('click',event=>{const button=event.target.closest('[data-drive]');if(button)openDrive(button.dataset.drive)});
const closeDialog=()=>$('drive-dialog').close();$('close-dialog').addEventListener('click',closeDialog);$('dialog-done').addEventListener('click',closeDialog);
$('drive-dialog').addEventListener('close',()=>{document.querySelector(`[data-drive="${CSS.escape(state.dialogDrive)}"]`)?.focus();state.dialogDrive=null});
let toastTimer;function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4000)}
$('export').addEventListener('click',async()=>{
  $('export').disabled=true;
  try{const response=await fetch(`/api/export?source=${state.source}`);if(!response.ok)throw Error('Report could not be exported. Try again.');const blob=await response.blob();const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`atlas-storage-${state.source}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);toast('Storage report downloaded.')}catch(error){toast(error.message)}finally{$('export').disabled=!state.snapshot}
});
setView(state.view);updateSync();load();
setInterval(()=>{if(state.auto&&!document.hidden)load()},10000);

let scanPolling=false;
async function trackSmartScan(){
 if(scanPolling)return;scanPolling=true;
 try{
  while(true){
   const job=await getJSON('/api/smart-scan');
   $('smart-scan-status').textContent=job.message;
   $('smart-scan').disabled=job.state==='running'||state.source!=='live';
   if(job.state!=='running'){if(job.state!=='idle')await load();break}
   await new Promise(resolve=>setTimeout(resolve,1000));
  }
 }catch(error){$('smart-scan-status').textContent=error.message;$('smart-scan').disabled=false}
 finally{scanPolling=false;$('smart-scan').disabled=state.source!=='live'}
}
$('smart-scan').addEventListener('click',async()=>{
 if(state.source!=='live')return;
 $('smart-scan').disabled=true;
 try{
  const session=await getJSON('/api/session');
  const response=await fetch('/api/smart-scan',{method:'POST',headers:{'X-Atlas-CSRF':session.csrf}});
  const job=await response.json();if(!response.ok)throw Error(job.error);
  await trackSmartScan();
 }catch(error){$('smart-scan-status').textContent=error.message;$('smart-scan').disabled=false}
});
trackSmartScan();
