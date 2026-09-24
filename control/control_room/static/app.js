"use strict";

const $ = (id) => document.getElementById(id);
const fmtTime = (value) => {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("nl-NL", {hour12:false});
};
const fmtBytes = (n) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "UNKNOWN";
  const units = ["B","KB","MB","GB","TB"]; let x=Number(n), i=0;
  while (x >= 1024 && i < units.length-1) { x/=1024; i++; }
  return `${x.toFixed(i > 1 ? 1 : 0)} ${units[i]}`;
};
const val = (v) => (v === null || v === undefined || v === "" ? "UNKNOWN" : String(v));
const addText = (parent, tag, text, cls) => { const el=document.createElement(tag); if(cls) el.className=cls; el.textContent=text; parent.appendChild(el); return el; };

function truth(label, value, cls="") {
  const d=document.createElement("div"); d.className="truth";
  addText(d,"span",label,"label"); addText(d,"span",val(value),`value ${cls}`.trim()); return d;
}
function renderTruth(s) {
  const root=$("truthBar"); root.replaceChildren();
  root.append(
    truth("Economic status", s.project.economic_status),
    truth("System", s.system_health.status, `status-${s.system_health.status}`),
    truth("Live trading", s.project.live_trading === false ? "OFF" : val(s.project.live_trading), s.project.live_trading === false ? "status-HEALTHY":"status-WARNING"),
    truth("Paid actions", s.project.paid_actions === false ? "LOCKED" : val(s.project.paid_actions)),
    truth("Wallet", s.project.wallet_actions === false ? "LOCKED" : val(s.project.wallet_actions)),
    truth("Git HEAD", s.git.head || "UNKNOWN"),
    truth("Dashboard", "READ ONLY", "status-HEALTHY")
  );
}
function renderActivity(s) {
  const root=$("activity"); root.replaceChildren();
  if (!s.activity.length) { addText(root,"div","Geen activity-evidence gevonden.","empty"); return; }
  s.activity.forEach(e => {
    const row=document.createElement("div"); row.className="event";
    addText(row,"span",fmtTime(e.at),"when"); addText(row,"span",val(e.kind),"kind");
    const title=addText(row,"span",val(e.title),"title"); title.title=val(e.source);
    addText(row,"span",val(e.status),"status"); root.appendChild(row);
  });
}
function renderAlerts(s) {
  $("alertCount").textContent=String(s.alerts.length); const root=$("alerts"); root.replaceChildren();
  if (!s.alerts.length) { addText(root,"div","Geen dashboard-alerts.","empty"); return; }
  s.alerts.forEach(a => { const d=document.createElement("div"); d.className=`alert ${a.severity}`; addText(d,"strong",`${a.severity} · ${a.code}`); addText(d,"span",a.message); root.appendChild(d); });
}
function kv(rootId, pairs) {
  const root=$(rootId); root.replaceChildren(); pairs.forEach(([k,v]) => { addText(root,"div",k,"k"); addText(root,"div",val(v),"v"); });
}
function renderHealth(s) {
  $("healthBadge").textContent=s.system_health.status;
  $("healthBadge").className=`pill status-${s.system_health.status}`;
  kv("health", [["Snapshot",fmtTime(s.generated_at)],["Read only",s.dashboard.read_only],["Outbound calls",s.dashboard.outbound_network_calls],["Mutation endpoints",s.dashboard.mutation_endpoints],["Parse errors",s.system_health.parse_error_count],["Registry version",s.project.registry_version]]);
}
function renderGit(s) {
  $("gitBadge").textContent=s.git.status; $("gitBadge").className=`pill status-${s.git.status}`;
  kv("git", [["Branch",s.git.branch],["HEAD",s.git.head],["Dirty",s.git.dirty],["Ahead",s.git.ahead],["Behind",s.git.behind],["Changes",(s.git.changes||[]).length]]);
}
function renderAgents(s) {
  const root=$("agents"); root.replaceChildren();
  if (!s.agents.length) { addText(root,"div","agents/registry.json ontbreekt of is onleesbaar.","empty"); return; }
  s.agents.forEach(a => {
    const d=document.createElement("div"); d.className="agent"; const h=document.createElement("div"); h.className="agent-head";
    addText(h,"h3",a.id); addText(h,"span",a.runtime_status,"pill"); d.appendChild(h);
    addText(d,"p",a.purpose || "—");
    const meta=document.createElement("div"); meta.className="muted"; meta.textContent=`${val(a.authority)} · last seen: ${fmtTime(a.last_seen)} · ${val(a.last_state)}`; d.appendChild(meta);
    const caps=document.createElement("div"); caps.className="caps"; (a.capabilities||[]).forEach(c=>addText(caps,"span",c,"cap")); d.appendChild(caps); root.appendChild(d);
  });
}
function renderTasks(s) {
  const body=$("tasks"); body.replaceChildren();
  if (!s.tasks.length) { const tr=document.createElement("tr"), td=document.createElement("td"); td.colSpan=6; td.className="empty"; td.textContent="Geen bekende task/result JSON-evidence."; tr.appendChild(td); body.appendChild(tr); return; }
  s.tasks.slice(0,60).forEach(t => {
    const tr=document.createElement("tr");
    [fmtTime(t.at), val(t.task_id), val(t.hypothesis_id), val(t.task_class || t.operation), val(t.status || t.state || t.last_transition), val(t.source)].forEach((text,i)=>{ const td=document.createElement("td"); td.textContent=text; if(i===4) td.className=`status-${String(text).toUpperCase()}`; tr.appendChild(td); });
    body.appendChild(tr);
  });
}
function renderResources(s) {
  const r=s.resources, m=r.memory||{}, d=r.disk||{};
  kv("resources", [["CPU cores",r.cpu_count],["Load 1/5/15",r.load_1_5_15 ? r.load_1_5_15.map(x=>Number(x).toFixed(2)).join(" / ") : "UNKNOWN"],["RAM used",m.used_percent === null ? "UNKNOWN" : `${m.used_percent}%`],["RAM total",fmtBytes(m.total_bytes)],["Disk used",d.used_percent === null ? "UNKNOWN" : `${d.used_percent}%`],["Disk free",fmtBytes(d.free_bytes)],["Host uptime",r.uptime_seconds === null ? "UNKNOWN" : `${Math.floor(r.uptime_seconds/3600)} h`]]);
}
function renderProvenance(s) {
  const root=$("provenance"); root.replaceChildren(); s.provenance.forEach(p => { const d=document.createElement("div"); d.className="prov"; const dot=document.createElement("span"); dot.className=`dot ${p.exists ? "yes":""}`; d.appendChild(dot); addText(d,"span",p.path,"path"); addText(d,"span",p.exists ? fmtTime(p.mtime) : "missing","mtime"); root.appendChild(d); });
}
function render(s) { renderTruth(s); renderActivity(s); renderAlerts(s); renderHealth(s); renderGit(s); renderAgents(s); renderTasks(s); renderResources(s); renderProvenance(s); $("refreshState").textContent=`snapshot ${fmtTime(s.generated_at)}`; }

async function refresh() {
  try { const res=await fetch("/api/snapshot",{cache:"no-store"}); if(!res.ok) throw new Error(`HTTP ${res.status}`); render(await res.json()); }
  catch(err) { $("refreshState").textContent=`dashboard fout: ${err.message}`; $("healthBadge").textContent="DISCONNECTED"; $("healthBadge").className="pill status-CRITICAL"; }
}
function tick(){ $("clock").textContent=new Date().toLocaleTimeString("nl-NL",{hour12:false}); }
tick(); refresh(); setInterval(tick,1000); setInterval(refresh,2000);
