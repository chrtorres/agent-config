export const initialFiles = {'Welcome.md':'# Welcome\n\nThis is your agent’s workspace. Read, create, and edit files here.\n', 'Notes/ideas.md':'# Ideas\n\n- Make room for a small experiment.\n- Keep the useful bits.\n'};
export class Workspace {
  constructor(files=initialFiles) { this.files={...files}; }
  resolve(path) {
    if(typeof path!=='string'||path.startsWith('/')||path.includes('\\')) throw Error('Use a relative workspace path.');
    const parts=[];
    for(const part of path.split('/')) {
      if(part==='..') { if(!parts.length) throw Error('Path is outside the workspace.'); parts.pop(); }
      else if(part&&part!=='.') parts.push(part);
    }
    return parts.join('/');
  }
  execute(name,args={}) {
    const path=this.resolve(args.path??'.');
    if(name==='ls') return Object.keys(this.files).filter(p=>!path||p.startsWith(path+'/')).join('\n')||'(empty folder)';
    if(name==='read') { if(!(path in this.files)) throw Error('File not found: '+path); return this.files[path]; }
    if(name==='write') { if(!path||typeof args.content!=='string')throw Error('A file path and content are required.'); this.files[path]=args.content; return 'Created '+path; }
    if(name==='edit') {
      const original=this.execute('read',{path});
      if(!args.oldText||original.split(args.oldText).length!==2)throw Error('Edit must match one unique region.');
      this.files[path]=original.replace(args.oldText,args.newText);return 'Updated '+path;
    }
    if(name==='grep') return Object.entries(this.files).flatMap(([p,t])=>t.split('\n').flatMap((line,i)=>line.includes(args.pattern)?[`${p}:${i+1} ${line}`]:[])).join('\n')||'No matches.';
    if(name==='find')return Object.keys(this.files).filter(p=>p.includes(args.pattern)).join('\n')||'No matches.';
    throw Error('Unknown tool: '+name);
  }
}
export function planFor(text,files) {
  const lower=text.toLowerCase();
  if(/escape|outside|\.\.\//.test(lower))return {steps:[{name:'write',args:{path:'../outside.txt',content:'Should be blocked.'}}],reply:'The workspace boundary blocked that path. Nothing was written outside your files.'};
  if(/edit|change|update/.test(lower)) {
    const path='Notes/hello.md';
    if(!files[path])return {steps:[{name:'write',args:{path,content:'# Hello\n\nMade with your agent.\n'}}],reply:'Created Notes/hello.md. Ask me to edit the note next.'};
    return {steps:[{name:'read',args:{path}},{name:'edit',args:{path,oldText:files[path],newText:'# Hello\n\nMade with your agent. Edited together, one small step at a time.\n'}}],reply:'Updated your note. You can open the new version in Files.'};
  }
  if(/write|create|note|save/.test(lower))return {steps:[{name:'write',args:{path:'Notes/hello.md',content:'# Hello\n\nMade with your agent.\n'}}],reply:'Your note is saved in Notes/hello.md. You can open it in Files or ask me to edit it.'};
  if(/search|find|grep/.test(lower))return {steps:[{name:'grep',args:{pattern:'experiment'}}],reply:'Found “experiment” in Notes/ideas.md. Search runs against your workspace files.'};
  if(/read|welcome/.test(lower))return {steps:[{name:'read',args:{path:'Welcome.md'}}],reply:'Your welcome file explains the workspace: you can read, create, and edit files here. File changes ask for your approval.'};
  if(/list|files|workspace/.test(lower))return {steps:[{name:'ls',args:{path:'.'}}],reply:`Here are your ${Object.keys(files).length} workspace files. Tap a tool card to inspect its output, or open the Files tab.`};
  return {steps:[],reply:'I’m the scripted demo agent. Try “read my welcome file”, “create a note”, “edit my note”, “search my files”, or “test a workspace escape”. The file tools really run in this browser’s local workspace.'};
}
