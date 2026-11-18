export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function bytes(value, units='binary', digits=1) {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Unknown';
  const base=units==='decimal'?1000:1024, labels=units==='decimal'?['B','KB','MB','GB','TB','PB']:['B','KiB','MiB','GiB','TiB','PiB'];
  let index=0, amount=Math.max(0,value);
  while(amount>=base && index<labels.length-1) { amount/=base; index++; }
  return `${new Intl.NumberFormat('en-US',{maximumFractionDigits:digits}).format(amount)} ${labels[index]}`;
}
export const percent = value => value === null || !Number.isFinite(value) ? 'Unknown' : `${Number(value.toFixed(1))}%`;
export function filterVolumes(volumes, query='', status='all', sort='usage') {
  const term=query.trim().toLowerCase();
  const result=volumes.filter(v=>(status==='all'||(status==='attention'?['warning','critical'].includes(v.severity):v.severity==='normal')) && [v.path,v.label,v.fstype,...v.mountpoints].join(' ').toLowerCase().includes(term));
  return result.sort((a,b)=>sort==='available'?(b.available??-1)-(a.available??-1):sort==='name'?(a.label||a.path).localeCompare(b.label||b.path):(b.percent??-1)-(a.percent??-1));
}
export function chartPoints(samples, key, width=800, height=160) {
  const values=samples.map(s=>s[key]).filter(Number.isFinite);
  if (!values.length) return '';
  const max=Math.max(...values,1)*1.15;
  return samples.map((s,i)=>Number.isFinite(s[key])?`${(i*width/Math.max(1,samples.length-1)).toFixed(2)},${(height-s[key]/max*height).toFixed(2)}`:null).filter(Boolean).join(' ');
}
