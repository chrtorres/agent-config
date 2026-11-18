import {percent,bytes,uptime,profileInfo,findings,coverage,pathFor,report} from './core.mjs';

const $=id=>document.getElementById(id);
const state={mode:'live',running:false,snapshot:null,history:[],job:null,view:'overview',epoch:0,busy:false,pending:false,config:null};
let sampleTimer,jobTimer,toastTimer;
const titles={overview:['Overview','Your system, in focus.','Live signals and careful diagnostics. A clearer path to what matters.'],diagnostics:['Health checks','A question. Then evidence.','Choose a focused check and see exactly what it found.'],processes:['Processes','Meet the moving parts.','A bounded view of the work your system is doing.'],evidence:['Evidence','Keep the context.','What was observed, what remains unknown, and what you choose to retain.']};
function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node}
function toast(message){$('toast').textContent=message;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),4000)}
function error(message){$('connection-error').hidden=!message;$('connection-error').textContent=message||''}
async function api(route,body){const response=await fetch(route,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});let data;try{data=await response.json()}catch{throw Error('The local server returned an unreadable response.')}if(!response.ok)throw Error(data.error||`HTTP ${response.status}`);return data}
function view(name){if(!titles[name])return;state.view=name;for(const node of document.querySelectorAll('.view'))node.hidden=node.id!==`view-${name}`;for(const node of document.querySelectorAll('[data-view]')){const selected=node.dataset.view===name;node.classList.toggle('selected',selected);node.setAttribute('aria-current',selected?'page':'false')}$('breadcrumb').textContent=titles[name][0];$('page-title').textContent=titles[name][1];$('page-subtitle').textContent=titles[name][2];renderEvidence()}
function activeJob(){return state.job&&['running','cancelling'].includes(state.job.status)}
function controls(){const active=activeJob();$('source').disabled=active||state.pending;$('monitor').disabled=state.pending;$('monitor').textContent=state.running?'Pause monitoring Ⅱ':state.snapshot?'Resume monitoring ↗':'Start monitoring ↗';$('session-dot').classList.toggle('running',state.running);$('session-label').textContent=state.running?(state.mode==='demo'?'Demo sampling · every 3s':'Monitoring · every 3s'):state.snapshot?'Paused · last sample retained':'Ready to observe';for(const button of document.querySelectorAll('[data-profile]'))button.disabled=active||state.pending;$('cancel').hidden=!active;$('cancel').disabled=state.job?.status==='cancelling';$('cancel').textContent=state.job?.status==='cancelling'?'Cancelling…':'Cancel check';$('export').disabled=$('export-evidence').disabled=!state.snapshot&&!state.job;$('nav-count').textContent=state.job?`${state.job.results.length}/${state.job.planned.length}`:'—'}

async function sample(){
 const epoch=state.epoch,mode=state.mode;
 if(!state.running)return;
 if(state.busy){clearTimeout(sampleTimer);sampleTimer=setTimeout(sample,100);return}
 state.busy=true;
 try{const data=await api(`/api/snapshot?mode=${mode}`);if(epoch!==state.epoch||!state.running)return;state.snapshot=data;const last=state.history.at(-1);if(!last||last.sequence!==data.sequence)state.history.push({sequence:data.sequence,collected_at:data.collected_at,cpu:data.cpu_percent,memory:data.memory?.percent??null});state.history=state.history.slice(-200);error(null);renderSnapshot();}
 catch(err){if(epoch===state.epoch){error(`Live collection failed: ${err.message} Retained values are from the last successful sample.`);state.running=false;clearTimeout(sampleTimer);controls()}}
 finally{state.busy=false;if(epoch===state.epoch&&state.running)sampleTimer=setTimeout(sample,3000)}
}
function toggleMonitoring(){state.running=!state.running;clearTimeout(sampleTimer);controls();if(state.running)sample()}
async function switchSource(){if(activeJob())return;state.running=false;state.epoch++;clearTimeout(sampleTimer);clearTimeout(jobTimer);state.mode=$('source').value;state.snapshot=null;state.history=[];state.job=null;error(null);$('demo-banner').hidden=state.mode!=='demo';renderSnapshot();renderJob();controls();if(state.mode==='demo'){state.running=true;controls();sample()}}

function renderSnapshot(){const s=state.snapshot;
 $('host-name').textContent=s?.host.name||(state.mode==='demo'?'Synthetic workstation':'This Linux host');
 $('host-description').textContent=s?`${s.host.system} · ${s.host.cpus??'Unknown'} logical CPUs · ${s.host.kernel}`:'Start a session to read the host identity and signals';
 for(const [name,value]of [['cpu',s?.cpu_percent],['memory',s?.memory?.percent],['disk',s?.disk?.percent]]){const node=$(`${name}-value`);node.replaceChildren(document.createTextNode(percent(value)),el('small','', '%'));$(`${name}-meter`).style.width=`${Math.max(0,Math.min(100,value??0))}%`}
 $('cpu-detail').textContent=s?`Load ${s.load?.map(v=>v.toFixed(2)).join(' / ')||'unavailable'} · compare with ${s.host.cpus??'?'} CPUs`:'Waiting for interval samples';
 $('memory-detail').textContent=s?.memory?`${bytes(s.memory.used)} used · ${bytes(s.memory.available)} available`:'Uses available memory, including cache';
 $('disk-detail').textContent=s?.disk?`${bytes(s.disk.available)} available on / · health unverified`:'Capacity on / · drive health unverified';
 $('uptime-value').textContent=uptime(s?.uptime_seconds);
 $('uptime-detail').textContent=s?`Swap occupied: ${bytes(s.memory?.swap_used)} · activity unmeasured`:'No restart actions in this suite';
 $('last-updated').textContent=s?`${s.source==='demo'?'Synthetic sample':'Last sample'} · ${new Date(s.collected_at).toLocaleTimeString()}${state.running?'':' · paused'}`:'No samples collected · local session';
 renderChart();renderFindings();renderProcesses();renderEvidence();controls();
}

function svg(tag,attrs){const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))node.setAttribute(k,v);return node}
function renderChart(){const chart=$('resource-chart');chart.replaceChildren();for(const value of [0,25,50,75,100]){const y=184-value*1.67;chart.append(svg('line',{x1:37,x2:688,y1:y,y2:y,stroke:'#e8eddf','stroke-dasharray':'3 5'}));const label=svg('text',{x:0,y:y+3,fill:'#9aaa8b','font-size':9});label.textContent=`${value}%`;chart.append(label)}
 const history=state.history;
 for(const [key,color]of [['memory','#afbb8b'],['cpu','#568569']]){const path=pathFor(history,key);chart.append(svg('path',{d:path,fill:'none',stroke:color,'stroke-width':2.5,'stroke-linecap':'round','stroke-linejoin':'round'}));const last=history.at(-1);if(Number.isFinite(last?.[key]))chart.append(svg('circle',{cx:history.length>1?688:37,cy:184-last[key]*1.67,r:3.5,fill:color,stroke:'#fffefa','stroke-width':2}))}
 $('chart-empty').hidden=history.length>0;$('chart-range').textContent=`${state.mode==='demo'?'SYNTHETIC':'SESSION'} · ${history.length} SAMPLES`;
 $('chart-start').textContent=history.length?new Date(history[0].collected_at).toLocaleTimeString():'Session start';$('chart-end').textContent=history.length?new Date(history.at(-1).collected_at).toLocaleTimeString():'Now';
 const values=history.map(p=>p.cpu).filter(Number.isFinite);$('chart-summary').textContent=values.length?`CPU mean ${percent(values.reduce((a,b)=>a+b,0)/values.length)}%`:'First CPU interval pending';
}
function renderFindings(){const target=$('findings');target.replaceChildren();const items=findings(state.snapshot,state.job);if(!state.snapshot&&!state.job){const note=el('div','empty-note','No observations yet.');note.append(el('p','','A quiet dashboard is not a health certification. Start monitoring, then run a baseline.'));target.append(note);return}for(const item of items.slice(0,4)){const row=el('div',`finding ${item.level}`);row.append(el('span','finding-icon',item.level==='review'?'!':'◇'));const body=el('div');body.append(el('strong','',item.title),el('p','',item.text));row.append(body);target.append(row)}}
function renderProcesses(){const target=$('process-rows');target.replaceChildren();for(const process of state.snapshot?.processes||[]){const row=el('tr');for(const text of [process.name,`${process.pid} / ${process.ppid}`,process.state,`${percent(process.cpu_percent)}${process.cpu_percent==null?'':'%'}`,bytes(process.rss)])row.append(el('td','',text));target.append(row)}if(!target.children.length){const row=el('tr');const cell=el('td','','Start monitoring to inspect processes.');cell.colSpan=5;row.append(cell);target.append(row)}$('process-foot').textContent=state.snapshot?state.snapshot.host.scope+' '+(state.snapshot.gaps.join(' · ')||'Process list is bounded to 2,000 PIDs; top 20 by memory shown.'):'Exited or inaccessible processes may be omitted.';
 const pressure=$('pressure');pressure.replaceChildren();for(const category of ['cpu','memory','io']){const card=el('div','pressure-card');card.append(el('h3','',`${category==='io'?'I/O':category.toUpperCase()} pressure`),el('strong','',`${percent(state.snapshot?.pressure[category])}%`),el('p','','Share of time with some tasks stalled · 10-second average'));pressure.append(card)}
}

async function runProfile(profile){
 if(state.pending||activeJob())return;state.pending=true;controls();view('diagnostics');
 try{state.job=await api('/api/jobs',{profile,mode:state.mode});renderJob();error(null);scheduleJob()}
 catch(err){error(`Could not start diagnostic: ${err.message}`)}finally{state.pending=false;controls()}
}
function scheduleJob(){clearTimeout(jobTimer);if(activeJob())jobTimer=setTimeout(pollJob,300)}
async function pollJob(){try{const job=await api('/api/job');if(job?.id===state.job?.id){state.job=job;renderJob();if(!activeJob())toast(job.status==='cancelled'?'Check cancelled. Collected evidence retained.':'Check complete. Review the evidence and coverage.')}error(null)}catch(err){error(`Diagnostic status unavailable: ${err.message} The server may still be finishing its bounded check.`)}finally{scheduleJob()}}
function renderJob(){const job=state.job;
 if(!job){$('job-source').textContent='NO CHECKS RUN YET';$('job-title').textContent='Start with a baseline';$('job-summary').textContent='Choose a check on the left to collect inspectable evidence.';$('job-progress').style.width='0%';$('check-results').replaceChildren();const empty=el('div','large-empty');empty.append(el('span','','⌕'),el('h3','','A useful answer starts with a good question.'),el('p','','Run a quick baseline, then inspect each exact command and result.'));const button=el('button','button primary','Run quick baseline ↗');button.dataset.profile='baseline';empty.append(button);$('check-results').append(empty);$('check-guidance').hidden=true;renderFindings();renderEvidence();controls();return}
 const target=$('check-results'),openIds=new Set([...target.querySelectorAll('details[open]')].map(n=>n.dataset.key));
 $('job-source').textContent=`${job.source==='demo'?'SYNTHETIC FIXTURE':'LOCAL READ-ONLY'} · ${job.status.toUpperCase()}`;$('job-title').textContent=job.title;
 const review=job.results.filter(r=>r.assessment==='review').length,limited=job.results.filter(r=>r.assessment==='limited').length;
 $('job-summary').textContent=`${job.results.length} of ${job.planned.length} checks collected · ${review} to review · ${limited} coverage gaps${job.status==='cancelled'?' · remaining checks not run':''}`;
 $('job-progress').style.width=`${job.results.length/job.planned.length*100}%`;target.replaceChildren();
 for(const key of job.planned){const result=job.results.find(r=>r.id===key);if(!result){const row=el('div','check-result');const summary=el('div','');summary.style.cssText='padding:14px;display:flex;justify-content:space-between;gap:10px;font-size:10px';summary.append(el('span','',key.replaceAll('-',' ')),el('span','result-status pending',job.active===key?'Collecting…':job.status==='cancelled'?'Not run':'Pending'));row.append(summary);target.append(row);continue}
  const details=el('details','check-result');details.dataset.key=key;details.open=openIds.has(key);const summary=el('summary');summary.append(el('span','',result.assessment==='review'?'!':'◇'),el('strong','',result.title),el('span',`result-status ${result.assessment}`,result.assessment==='review'?'Review':result.assessment==='limited'?'Limited':'Observed'));details.append(summary);
  const content=el('div','check-content');content.append(el('p','',result.summary||'Incomplete check.'),el('div','check-meta',`${result.status} · exit ${result.returncode??'—'} · ${result.duration_ms} ms · ${new Date(result.started_at).toLocaleString()}${result.truncated?' · OUTPUT CAPPED':''}`),el('code','command',result.argv.join(' ')),el('pre','check-output',result.output|| (result.status==='missing'?'Command is not installed. No package installation was attempted.':result.status==='cancelled'?'Cancelled before output was collected.':'(No output)')));details.append(content);target.append(details)
 }
 const guidance=job.profile==='baseline'?'An empty package audit and no failed units are bounded observations. Capacity, inode use, updates, drive health, and thermal limits still need context.':state.config?.guidance[job.profile];$('check-guidance').textContent=guidance||'';$('check-guidance').hidden=!guidance;
 renderFindings();renderEvidence();controls();
}
function renderEvidence(){const target=$('coverage');target.replaceChildren();for(const [title,status,description]of coverage(state.snapshot,state.job)){const row=el('div','coverage-row'),body=el('div');body.append(el('strong','',title),el('p','',description));row.append(body,el('span',`result-status ${status}`,status==='limited'?'Unverified':status==='review'?'Review':'Observed'));target.append(row)}
 const facts=$('session-facts');facts.replaceChildren();for(const [key,value]of [['Source',state.mode==='demo'?'Synthetic fixture':'This host'],['Host',state.snapshot?.host.name||'Not sampled'],['Retained chart samples',String(state.history.length)],['Latest check',state.job?`${state.job.title} · ${state.job.status}`:'Not run'],['Storage','Memory only · explicit download'],['Collection','3 seconds while monitoring']]){const row=el('div');row.append(el('dt','',key),el('dd','',value));facts.append(row)}
}
function exportReport(){if(!state.snapshot&&!state.job)return;const payload=report(state.snapshot,state.history,state.job),blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=el('a');link.href=url;link.download=`fieldwork-${state.mode}-${new Date().toISOString().replaceAll(':','-')}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Report downloaded. Nothing uploaded.')}
function buildProfiles(){for(const [key,profile]of Object.entries(state.config.profiles)){const info=profileInfo[key],card=el('button','profile-card');card.dataset.profile=key;const foot=el('span','profile-foot',`${info.count} bounded checks`);foot.append(el('span','','↗'));card.append(el('span','profile-icon',info.icon),el('strong','',profile.title),el('p','',info.description),foot);$('profile-cards').append(card);const option=el('button','profile-option');option.dataset.profile=key;const text=el('div');text.append(el('strong','',profile.title),el('small','',`${info.count} checks · up to ${info.count*8}s`));option.append(el('span','profile-icon',info.icon),text);$('profile-list').append(option)}}
document.addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;if(button.dataset.view)view(button.dataset.view);if(button.dataset.go)view(button.dataset.go);if(button.dataset.profile)runProfile(button.dataset.profile)});
$('monitor').addEventListener('click',toggleMonitoring);$('source').addEventListener('change',switchSource);$('export').addEventListener('click',exportReport);$('export-evidence').addEventListener('click',exportReport);
$('cancel').addEventListener('click',async()=>{try{state.job=await api('/api/cancel',{id:state.job.id});renderJob();scheduleJob()}catch(err){error(err.message)}});
$('walkthrough').addEventListener('click',()=>$('tour-dialog').showModal());for(const key of ['close-tour','tour-start'])$(key).addEventListener('click',()=>$('tour-dialog').close());
document.querySelector('.brand').addEventListener('click',event=>{event.preventDefault();view('overview')});
try{state.config=await api('/api/config');buildProfiles();const job=await api('/api/job');if(job){state.job=job;state.mode=job.source;$('source').value=job.source;$('demo-banner').hidden=job.source!=='demo';renderJob();scheduleJob()}renderSnapshot();view('overview')}
catch(err){error(`Local server unavailable: ${err.message} Start server.py from the project directory.`);$('monitor').disabled=true}
