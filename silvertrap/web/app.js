'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const defang = value => String(value).replace(/https:\/\//gi, 'hxxps://').replace(/http:\/\//gi, 'hxxp://').replace(/\./g, '[.]').replace(/@/g, '[@]');
function eventKey() { const bytes = new Uint8Array(12); window.crypto.getRandomValues(bytes); return 'ui:' + Array.from(bytes, b => b.toString(16).padStart(2, '0')).join(''); }
let token = '', state = {overview: null, cases: [], indicators: {items: []}}, currentCase = null;
let activeTab = 'reconstruction', selectedStage = 'theft', newMode = 'simulation', query = '', statusFilter = 'all', toastTimer, routeGeneration = 0, lastRoute = '';

async function api(path, data) {
  const response = await fetch(path, {method: data === undefined ? 'GET' : 'POST', headers: {Authorization: `Bearer ${token}`, ...(data === undefined ? {} : {'Content-Type': 'application/json'})}, ...(data === undefined ? {} : {body: JSON.stringify(data)})});
  const result = await response.json();
  if (!response.ok) { if (response.status === 401 && !$('#workspace').hidden) lock(); throw new Error(result.error || 'Request failed'); }
  return result;
}
function toast(message) { clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false; toastTimer = setTimeout(() => $('#toast').hidden = true, 6500); }
function lock() { token = ''; currentCase = null; routeGeneration++; $('#workspace').hidden = true; $('#login').hidden = false; $('#access-code').value = ''; $('#access-code').focus(); }
function pill(status) { return `<span class="pill ${status === 'paused' ? 'amber' : status === 'closed' ? 'gray' : ''}"><span class="status-dot"></span>${escape(status === 'active' ? 'Active' : status === 'paused' ? 'Paused' : 'Closed')}</span>`; }
function action(label, name, extra = '', classes = '') { return `<button class="button ${classes}" data-action="${name}" ${extra}>${label}</button>`; }
function coverage(n) { return `<div class="coverage" aria-label="${n} of 6 stages observed">${Array.from({length: 6}, (_, i) => `<span class="${i < n ? 'filled' : ''}"></span>`).join('')}</div><small class="case-subtitle">${n}/6 observed</small>`; }
function banner() { return state.overview.stopped ? '<div class="stop-banner" role="status">Emergency stop is active. Evidence remains available; new intake, simulations, approvals, and analysis are paused.</div>' : ''; }
function heading(title, description, buttons = '', eyebrow = 'FRAUD INTELLIGENCE OPERATIONS') { return `${banner()}<div class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p>${description}</p></div><div class="heading-actions">${buttons}</div></div>`; }
function metric(label, value, note, icon) { return `<div class="metric"><div class="metric-label">${label}<span class="metric-icon" aria-hidden="true">${icon}</span></div><div class="metric-value">${String(value).padStart(2, '0')}</div><div class="metric-note">${note}</div></div>`; }
function caseRows(cases) {
  return cases.map(c => `<tr><td><button class="case-title" data-action="open-case" data-id="${escape(c.id)}">${escape(c.title)}</button><span class="case-id mono">${escape(c.id)}</span> <span class="case-subtitle">· ${escape(c.mode)}</span></td><td><span class="case-subtitle">${escape(c.classification)}</span></td><td>${coverage(c.coverage)}</td><td>${pill(c.status)}</td><td><span class="number">${c.indicator_count}</span></td><td><button class="text-link" data-action="open-case" data-id="${escape(c.id)}" aria-label="Open ${escape(c.title)}">↗</button></td></tr>`).join('') || '<tr><td colspan="6" class="empty">No investigations match. Start a simulation or import a transcript.</td></tr>';
}
function caseTable(cases, title = 'Recent investigations', subtitle = 'From first contact to financial objective', all = false) {
  return `<section class="panel"><div class="section-heading"><h2>${title}<small>${subtitle}</small></h2>${all ? '<a href="#cases" class="text-link">View all ↗</a>' : '<span class="pill gray">Evidence linked</span>'}</div><div class="table-wrap"><table><thead><tr><th>INVESTIGATION</th><th>SCAM HYPOTHESIS</th><th>STAGE COVERAGE</th><th>STATUS</th><th>INDICATORS</th><th></th></tr></thead><tbody>${caseRows(cases)}</tbody></table></div><div class="table-bottom"><span>${cases.length} investigations shown</span><span>Observations ≠ verified attribution</span></div></section>`;
}
function miniPersonas() {
  return state.overview.personas.map(p => `<div class="mini-persona"><span class="avatar">${p.initials}</span><div><h3>${escape(p.name)}</h3><p>Fictional · ${p.age} · ${state.cases.filter(c => c.persona_id === p.id && c.status === 'active').length} active cases</p></div><span>↗</span></div>`).join('');
}
function overview() {
  const o = state.overview, shared = state.indicators.items.filter(i => i.case_count > 1), lead = shared[0];
  return heading('Understand the operation.', 'Reconstruct the methodology behind every conversation.', action('＋ New investigation', 'new', '', 'primary')) +
    `<div class="metrics">${metric('Investigations', o.cases, '<strong>Case-by-case</strong> evidence isolation', '▤')}${metric('Active conversations', o.active, 'Controlled simulations & research', '◎')}${metric('Unique indicators', o.indicators, 'Extracted from inbound messages', '⌘')}${metric('Pending reviews', o.pending, 'Local decisions · no external delivery', '◷')}</div>
    <div class="overview-grid">${caseTable(state.cases.slice(0, 5), 'Investigation desk', 'A clear record of how each approach unfolds', true)}<aside class="panel insight-card"><div class="insight-icon">⌘</div><p class="eyebrow">CONNECTED EVIDENCE</p><h2>Different conversations.<br>Shared signals.</h2><p>Spot recurring infrastructure across your cases, then inspect the evidence behind the connection.</p><div class="insight-stat">${String(shared.length).padStart(2, '0')}</div><div class="insight-caption">indicators appearing in multiple cases</div>${lead ? `<div class="indicator-lead"><code>${escape(defang(lead.normalized))}</code><small>Observed in ${lead.case_count} cases · ${escape(lead.kind)}</small></div>` : ''}<a href="#indicators" class="text-link">Explore indicator library ↗</a></aside></div>
    <section class="method-panel"><div class="method-header"><h2>One conversation. A complete picture.</h2><small>THE RECONSTRUCTION PIPELINE</small></div><div class="method-grid"><div class="method-item"><span class="method-num">01 / OBSERVE</span><h3>Capture the approach</h3><p>Record inbound evidence with an isolated conversation history.</p></div><div class="method-item"><span class="method-num">02 / ANALYZE</span><h3>Recognize the method</h3><p>Extract authority claims, pressure tactics, and requested actions.</p></div><div class="method-item"><span class="method-num">03 / RECONSTRUCT</span><h3>Connect the stages</h3><p>Trace the attack chain and leave unobserved stages visible.</p></div><div class="method-item"><span class="method-num">04 / REVIEW</span><h3>Make evidence useful</h3><p>Inspect each source, test hypotheses, and export a case report.</p></div></div></section>
    <div class="section-heading subheading"><h3>Synthetic persona desk</h3><a href="#personas" class="text-link">Meet the personas ↗</a></div><div class="persona-strip">${miniPersonas()}</div>`;
}
function casesView() {
  const visible = state.cases.filter(c => `${c.id} ${c.title} ${c.classification}`.toLowerCase().includes(query.toLowerCase()) && (statusFilter === 'all' || c.status === statusFilter));
  return heading('Investigations', 'Each case keeps its own memory, evidence, limits, and review history.', action('＋ New investigation', 'new', '', 'primary')) +
    `<div class="filters"><div class="search"><span aria-hidden="true">⌕</span><input id="case-search" aria-label="Search investigations" placeholder="Search title, hypothesis, or case ID" value="${escape(query)}"></div><select id="status-filter" aria-label="Filter by status">${['all', 'active', 'paused', 'closed'].map(s => `<option value="${s}" ${s === statusFilter ? 'selected' : ''}>${s === 'all' ? 'All statuses' : s.charAt(0).toUpperCase()+s.slice(1)}</option>`).join('')}</select></div>` + caseTable(visible, 'Investigation register', `${visible.length} of ${state.cases.length} cases`);
}
function indicatorsView() {
  return heading('The indicator library', 'Follow shared signals back to their source conversations.') + `<p class="note">${escape(state.indicators.caveat || 'Shared indicators are leads, not proof of common ownership.')} Values are displayed as text; URLs are defanged and never opened.</p><section class="panel"><div class="table-wrap"><table><thead><tr><th>TYPE</th><th>INDICATOR</th><th>CASES</th><th>OBSERVATIONS</th><th>SOURCE INVESTIGATIONS</th></tr></thead><tbody>${state.indicators.items.map(i => `<tr><td><span class="pill gray">${escape(i.kind)}</span></td><td class="indicator-cell mono">${escape(defang(i.normalized))}</td><td>${i.case_count > 1 ? `<span class="pill amber">${i.case_count} shared</span>` : '1'}</td><td>${i.occurrences}</td><td>${i.cases.map(c => `<button class="indicator-case" data-action="open-case" data-id="${escape(c.id)}">${escape(c.title)} ↗</button>`).join('')}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">Run a simulation or add evidence to begin collecting indicators.</td></tr>'}</tbody></table></div></section>`;
}
function personasView() {
  return heading('Synthetic, by design.', 'Three fictional identities. Consistent voices. Independent case memories.', action('＋ Start a case', 'new', '', 'primary'), 'SYNTHETIC PERSONA DESK') + `<div class="persona-grid">${state.overview.personas.map(p => `<article class="panel persona-card"><span class="avatar">${p.initials}</span><h2>${escape(p.name)}</h2><p>Fictional identity · Age ${p.age}</p><dl class="persona-spec"><dt>Background</dt><dd>${escape(p.background)}</dd><dt>Conversation style</dt><dd>${escape(p.style)}</dd><dt>Active cases</dt><dd>${state.cases.filter(c => c.persona_id === p.id && c.status === 'active').length}</dd><dt>Available actions</dt><dd>Ask, clarify, and record a local draft.</dd></dl></article>`).join('')}</div><p class="note subheading">Persona replies use vetted adaptive templates. They do not contain real accounts, financial credentials, payment tokens, or executable actions. Local model analysis is separate from the persona.</p>`;
}
const ROLES = [['Persona agent', 'Maintains a fictional voice with stage-aware, nonrepeating questions.'], ['Behavioral analyst', 'Finds urgency, secrecy, threats, and authority claims.'], ['Scam classifier', 'Proposes a category from explicit phrase evidence.'], ['Financial analyst', 'Separates observed requests from suspected objectives.'], ['Intelligence extractor', 'Normalizes indicators and preserves source offsets.'], ['Reconstruction agent', 'Orders evidence without inventing skipped stages.'], ['Safety supervisor', 'Enforces limits, queues, isolation, and emergency stop.']];
function controlsView() {
  const o = state.overview, l = o.limits;
  return heading('Control the operation.', 'Explicit boundaries, predictable resource use, and a stop that persists across restarts.', '', 'OPERATIONAL CONTROLS') + `<div class="control-grid"><section class="panel"><p class="eyebrow">NETWORK CONTROL</p><h2>${o.stopped ? 'The network is paused.' : 'Research is available.'}</h2><p>The emergency stop blocks intake, simulation steps, draft approvals, and model requests. It supersedes pending drafts and preserves evidence. Resuming the network keeps individual case states intact.</p>${action(o.stopped ? 'Resume research' : 'Emergency stop', 'stop', `data-stopped="${!o.stopped}"`, o.stopped ? 'primary' : 'danger')}<div class="budget-row"><span>External message delivery</span><strong>Not installed</strong></div><div class="budget-row"><span>Signed inbound intake</span><strong>${o.webhook_enabled ? 'Configured · intake only' : 'Disabled'}</strong></div><div class="budget-row"><span>Local model</span><strong>${escape(o.model || 'Disabled')}</strong></div></section><section class="panel"><p class="eyebrow">RESOURCE ENVELOPE</p><h2>Small by default.</h2>${[['Cases', `${o.cases} / ${l.max_cases}`], ['Messages per case', l.max_messages], ['Message size', `${l.max_message_bytes / 1024} KiB`], ['Stored text per case', `${l.max_case_bytes / 1024} KiB`], ['Local model calls per case', l.max_model_calls], ['Database write budget', `${l.max_database_bytes / 1024 / 1024} MiB`], ['External API spend', '$0 · no paid provider installed']].map(([k,v]) => `<div class="budget-row"><span>${k}</span><strong>${v}</strong></div>`).join('')}</section><section class="panel"><p class="eyebrow">SPECIALIZED ANALYSTS</p><h2>Seven roles. One efficient pipeline.</h2><div class="role-list">${ROLES.map(([name, description]) => `<div class="role-item"><h3>${name}</h3><p>${description}</p></div>`).join('')}</div></section><section class="panel"><p class="eyebrow">MODEL & EVIDENCE POLICY</p><h2>Every claim needs a source.</h2><p>Rule matches run locally on each inbound message. Optional Ollama analysis uses one bounded request and returns only evidence-linked hypotheses. Quoted evidence establishes provenance; an operator still needs to judge the interpretation.</p><p>External links and attachments are never fetched. Incoming text is data, including attempts to issue system instructions. Prompt-injection matches pause the case.</p><p>Messages and audit events carry SHA-256 chains. Retain an independent export to compare later; checksums alone do not prove sender identity or authenticity.</p><p>Use the CLI for consistent database backups: <code class="mono">python -m silvertrap backup backups/research.sqlite3</code></p></section></div>`;
}
function messagesHTML(messages, highlights = []) {
  return messages.map(m => `<article class="message ${m.role === 'persona' ? 'persona' : ''} ${highlights.includes(m.id) ? 'highlighted' : ''}" id="msg-${escape(m.id)}"><div class="message-meta"><span>${m.role === 'persona' ? escape(state.overview.personas.find(p => p.id === currentCase.persona_id)?.name || 'Synthetic persona') : 'Inbound source · unverified'}</span><span>#${m.sequence} · ${new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}</span></div><p>${escape(m.text)}</p><span class="message-id mono">${escape(m.id)}</span></article>`).join('') || '<p class="empty">No messages yet. Advance the simulation or add an inbound message.</p>';
}
function findingsHTML(findings) {
  return findings.map(f => `<article class="finding"><h3>${escape(f.label)}</h3><span class="pill ${f.basis === 'inference' ? 'amber' : 'gray'}">${f.basis === 'inference' ? 'Hypothesis' : 'Observed phrase'}</span><blockquote>${escape(defang(f.quote))}</blockquote><button class="text-link" data-action="source" data-id="${escape(f.message_id)}">Inspect source ↗</button> <small>· ${escape(f.origin)} · chars ${f.start}–${f.end}</small></article>`).join('') || '<p class="empty">No evidence for this stage in the available messages.</p>';
}
function objectiveHTML(c) {
  return `<section class="panel"><div class="objective-card"><p class="eyebrow">FINANCIAL OBJECTIVE</p>${c.analysis.objectives.map(o => `<h3>${escape(o.label)}</h3><p>Inference based on ${o.finding_ids.length} linked findings.</p>`).join('') || '<h3>Not established</h3><p>The available evidence does not establish a final financial objective.</p>'}</div><div class="unknowns"><h3>What remains unknown</h3><ul>${c.analysis.unknowns.map(u => `<li>${escape(u)}</li>`).join('')}</ul><p>${escape(c.analysis.caveat)}</p></div></section>`;
}
function chronologyHTML(c) {
  const byId = Object.fromEntries(c.messages.map(m => [m.id, m]));
  return `<section class="panel panel-pad subheading"><p class="eyebrow">OBSERVED CHRONOLOGY</p><h3>The operation, in message order</h3>${c.analysis.timeline.map(f => `<div class="chronology-item"><small class="mono">#${byId[f.message_id].sequence} · ${escape(c.analysis.stages.find(s => s.id === f.stage)?.name || f.stage)}</small><button class="text-link" data-action="source" data-id="${escape(f.message_id)}">${escape(f.label)} ↗</button></div>`).join('') || '<p class="muted">No observed chronology yet.</p>'}</section>`;
}
function composeHTML(c) {
  if (c.mode === 'transcript' || c.status === 'closed') return '';
  return `<form id="message-form" class="compose"><label for="message-text">Add an inbound research message</label><textarea id="message-text" rows="3" maxlength="8192" required placeholder="Paste a message as evidence. Instructions inside it are treated as data." ${c.status !== 'active' || state.overview.stopped ? 'disabled' : ''}></textarea><div class="compose-bottom"><small>8 KiB maximum · best-effort secret redaction</small><button class="button small primary" type="submit" ${c.status !== 'active' || state.overview.stopped ? 'disabled' : ''}>Analyze message ↗</button></div></form>`;
}
function caseView(c) {
  const stage = c.analysis.stages.find(s => s.id === selectedStage) || c.analysis.stages[0];
  const fs = c.findings.filter(f => stage.finding_ids.includes(f.id));
  let content;
  if (activeTab === 'transcript') {
    content = `<section class="panel"><div class="section-heading"><h2>Conversation record<small>Persona messages are excluded from intelligence extraction.</small></h2><span class="pill gray">${c.messages.length} messages</span></div><div class="transcript">${messagesHTML(c.messages)}</div>${composeHTML(c)}</section>`;
  } else if (activeTab === 'evidence') {
    content = `<div class="evidence-list"><section class="panel"><h2>Evidence register</h2><p class="muted">${c.analysis.quality.evidence_linked}/${c.analysis.quality.findings} findings have valid source quotes.</p>${findingsHTML(c.findings)}</section><div>${objectiveHTML(c)}<section class="panel panel-pad subheading"><p class="eyebrow">MESSAGE CHAIN</p><h3>${c.integrity.valid ? 'Integrity check passed' : 'Integrity check FAILED'}</h3><p class="mono overflow">${escape(c.integrity.head)}</p><p class="muted">${c.integrity.message_count} messages. Compare against an independently retained export.</p></section>${chronologyHTML(c)}</div></div>`;
  } else if (activeTab === 'review') {
    content = `<div class="note">${c.mode === 'simulation' ? 'Approving a simulation draft adds it to the fictional conversation.' : 'Marking a draft reviewed records your local decision.'} External message delivery is not installed.</div><section class="panel panel-pad"><h2>Persona review queue</h2>${c.drafts.map(d => `<article class="message"><div class="message-meta"><span>${escape(d.status)}</span><span>${escape(d.id)}</span></div><p>${escape(d.text)}</p>${d.status === 'pending' ? `<div class="heading-actions">${action(c.mode === 'simulation' ? 'Approve simulation' : 'Mark reviewed', 'decide', `data-id="${escape(d.id)}" data-decision="approve" ${state.overview.stopped || c.status !== 'active' ? 'disabled' : ''}`, 'small primary')}${action('Reject', 'decide', `data-id="${escape(d.id)}" data-decision="reject" ${state.overview.stopped || c.status !== 'active' ? 'disabled' : ''}`, 'small')}</div>` : ''}</article>`).join('') || '<div class="empty">No drafts yet. Add evidence or run a simulation.</div>'}</section>`;
  } else {
    content = `<div class="detail-grid"><section class="panel"><div class="section-heading"><h2>${escape(stage.name)}<small>${stage.observed ? `${stage.message_ids.length} source messages linked to this stage` : 'This stage has not been observed'}</small></h2><span class="pill ${stage.observed ? '' : 'gray'}">${stage.observed ? 'Observed' : 'Evidence gap'}</span></div><div class="findings">${findingsHTML(fs)}</div><div class="section-heading"><h2>Source conversation<small>Highlighted messages support the selected stage.</small></h2></div><div class="transcript">${messagesHTML(c.messages, stage.message_ids)}</div>${composeHTML(c)}</section><div>${objectiveHTML(c)}<section class="panel panel-pad subheading"><p class="eyebrow">SUPERVISOR</p><h3>${c.safety_alerts.length ? 'Requests requiring boundaries' : 'No supervisor pattern matched'}</h3><p class="muted">${c.safety_alerts.map(a => escape(a.replace(/_/g, ' '))).join(' · ') || 'Continue to review source evidence.'}</p><small class="muted">Source requests cannot execute actions.</small></section></div></div>`;
  }
  const disabled = c.status !== 'active' || state.overview.stopped;
  return `${banner()}<a class="back-link" href="#cases">← All investigations</a><div class="page-heading case-heading"><div><div class="case-meta"><span class="mono">${escape(c.id)}</span>${pill(c.status)}<span class="pill gray">${escape(c.mode === 'simulation' ? 'Fictional simulation' : c.mode)}</span></div><h1>${escape(c.title)}</h1><p>${escape(c.analysis.classification)} · ${c.analysis.coverage.observed}/6 stages observed · ${c.messages.length}/${c.limits.messages} messages</p></div><div class="heading-actions">${action('↓ Evidence', 'export-json')}${action('↓ Report', 'export-md')}</div></div>
    <section class="panel"><div class="section-heading"><h2>Scam operation reconstruction<small>Select a stage to inspect its evidence. Unobserved stages stay visible.</small></h2><span class="pill gray">${c.analysis.quality.evidence_linked} source-linked findings</span></div><div class="stage-map">${c.analysis.stages.map((s, i) => `<button class="stage-node ${s.observed ? 'observed' : ''} ${s.id === stage.id ? 'selected' : ''}" data-action="stage" data-id="${s.id}" aria-pressed="${s.id === stage.id}"><span class="stage-number">0${i+1} ${s.observed ? '●' : '○'}</span><strong>${s.name}</strong><small>${s.state === 'operator_closed' ? 'Operator closed' : s.observed ? `${s.finding_ids.length} findings` : 'Unobserved'}</small></button>`).join('')}</div><div class="graph-caption"><span>Observed phases can overlap or repeat; this view does not invent a fixed order.</span><span>Source offsets use Unicode code points.</span></div></section>
    <div class="case-toolbar"><div>${c.mode === 'simulation' ? `${action('▷ Next exchange', 'step', disabled || c.cursor >= c.scenario_total ? 'disabled' : '')}${action('Run remaining scenario', 'run', disabled || c.cursor >= c.scenario_total ? 'disabled' : '')}<span class="pill gray">${c.cursor}/${c.scenario_total} exchanges</span>` : ''}${c.status !== 'closed' && c.mode !== 'transcript' ? action(c.status === 'active' ? 'Pause case' : 'Resume case', 'status', `data-status="${c.status === 'active' ? 'paused' : 'active'}" ${state.overview.stopped && c.status === 'paused' ? 'disabled' : ''}`) : ''}${c.status !== 'closed' ? action('Close case', 'status', 'data-status="closed"') : ''}</div><div>${action('✧ Local model second opinion', 'model', `${!state.overview.model || c.status === 'closed' || state.overview.stopped ? 'disabled' : ''} title="Optional Ollama analysis; configure a local model to enable"`)}<small class="muted">${c.model_calls}/${c.limits.model_calls} calls</small></div></div>
    <div class="case-tabs" role="tablist" aria-label="Investigation details">${[['reconstruction','Reconstruction'],['transcript','Transcript'],['evidence','Evidence & gaps'],['review',`Review queue (${c.drafts.filter(d => d.status === 'pending').length})`]].map(([id, label]) => `<button role="tab" aria-selected="${activeTab === id}" class="${activeTab === id ? 'active' : ''}" data-action="tab" data-id="${id}">${label}</button>`).join('')}</div>${content}`;
}
async function loadState() {
  const [overviewData, casesData, indicatorsData] = await Promise.all([api('/api/overview'), api('/api/cases'), api('/api/indicators')]);
  state = {overview: overviewData, cases: casesData.items, indicators: indicatorsData};
  $('#case-count').textContent = overviewData.cases;
  $('#footer-state').textContent = overviewData.stopped ? 'Emergency stop active · evidence preserved' : 'External delivery is not installed';
}
async function render(refresh = false) {
  if (!token) return;
  const generation = ++routeGeneration;
  const route = location.hash.slice(1) || 'overview', [view, id] = route.split('/');
  if (refresh || !state.overview) await loadState();
  if (generation !== routeGeneration || !token) return;
  for (const item of document.querySelectorAll('#navigation a')) item.classList.toggle('active', item.dataset.view === (view === 'case' ? 'cases' : view));
  const names = {overview:'Overview', cases:'Investigations', case:'Investigation', indicators:'Indicator library', personas:'Synthetic personas', controls:'Controls & limits', activity:'Audit trail'};
  $('#crumb').textContent = names[view] || 'Overview';
  if (view === 'case' && id) {
    const next = await api(`/api/cases/${encodeURIComponent(id)}`);
    if (generation !== routeGeneration || !token) return;
    if (currentCase?.id !== next.id) { activeTab = 'reconstruction'; selectedStage = next.analysis.stages.find(s => s.id === 'theft' && s.observed)?.id || next.analysis.stages.find(s => s.observed)?.id || 'contact'; }
    currentCase = next;
    $('#main').innerHTML = caseView(next);
  } else if (view === 'activity') {
    const events = await api('/api/events');
    if (generation !== routeGeneration || !token) return;
    $('#main').innerHTML = heading('A record of every decision.', 'Case activity, supervisor actions, and evidence hashes in one local audit trail.', '', 'OPERATIONAL AUDIT') + `<section class="panel">${events.items.map(event => `<article class="audit-event"><time>${escape(new Date(event.created_at).toLocaleString())}</time><strong>${escape(event.kind)}</strong><code>${escape(event.payload)}</code></article>`).join('') || '<div class="empty">No activity yet.</div>'}</section><p class="note subheading">The database stores the event hash chain. This view shows the 100 most recent events.</p>`;
  } else $('#main').innerHTML = ({overview, cases: casesView, indicators: indicatorsView, personas: personasView, controls: controlsView}[view] || overview)();
  if (lastRoute !== route) { window.scrollTo(0, 0); lastRoute = route; }
}
function showNew() {
  $('#scenario').innerHTML = state.overview.scenarios.map(s => `<option value="${s.id}">${escape(s.title)}</option>`).join('');
  $('#persona').innerHTML = state.overview.personas.map(p => `<option value="${p.id}">${escape(p.name)} · ${p.age}</option>`).join('');
  updateScenario(); $('#dialog-error').textContent = ''; $('#new-dialog').showModal();
}
function updateScenario() { $('#scenario-description').textContent = state.overview.scenarios.find(s => s.id === $('#scenario').value)?.description || ''; }
async function download(type) {
  const response = await fetch(`/api/cases/${currentCase.id}/${type === 'json' ? 'export.json' : 'report.md'}`, {headers: {Authorization: `Bearer ${token}`}});
  if (!response.ok) throw new Error('Evidence export failed');
  const url = URL.createObjectURL(await response.blob()), a = document.createElement('a');
  a.href = url; a.download = `${currentCase.id}.${type}`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(type === 'json' ? 'Evidence package exported. Keep an independent copy of the manifest.' : 'Case report exported.');
}
$('#login-form').addEventListener('submit', async event => {
  event.preventDefault(); token = $('#access-code').value.trim(); const button = $('button', event.target); button.disabled = true;
  try { await loadState(); $('#login-error').textContent = ''; $('#access-code').value = ''; $('#login').hidden = true; $('#workspace').hidden = false; await render(); }
  catch (error) { token = ''; $('#login-error').textContent = error.message; }
  finally { button.disabled = false; }
});
$('#lock').addEventListener('click', lock);
$('#refresh').addEventListener('click', () => render(true).then(() => toast('Workspace refreshed.')).catch(error => toast(error.message)));
$('#mobile-menu').addEventListener('click', () => $('.sidebar').classList.toggle('open'));
$('#navigation').addEventListener('click', event => { if (event.target.closest('a')) $('.sidebar').classList.remove('open'); });
$('#close-dialog').addEventListener('click', () => $('#new-dialog').close());
$('#scenario').addEventListener('change', updateScenario);
$('.segmented').addEventListener('click', event => {
  const button = event.target.closest('[data-mode]'); if (!button) return;
  newMode = button.dataset.mode;
  for (const mode of ['simulation', 'research', 'import']) $(`#${mode}-fields`).hidden = mode !== newMode;
  for (const b of document.querySelectorAll('[data-mode]')) b.classList.toggle('selected', b === button);
});
$('#new-form').addEventListener('submit', async event => {
  event.preventDefault(); const button = $('button[type="submit"]', event.target); button.disabled = true; $('#dialog-error').textContent = '';
  try {
    let result;
    if (newMode === 'import') {
      let payload; try { payload = JSON.parse($('#import-json').value); } catch { throw new Error('Enter valid transcript JSON.'); }
      result = await api('/api/import', {title: $('#import-title').value.trim() || 'Imported transcript', messages: Array.isArray(payload) ? payload : payload.messages});
    } else if (newMode === 'research') result = await api('/api/cases', {title: $('#case-title').value.trim() || 'Controlled research', persona_id: $('#persona').value});
    else { result = await api('/api/cases', {scenario: $('#scenario').value}); if ($('#run-now').checked) result = await api(`/api/cases/${result.id}/simulate`, {all_steps: true}); }
    $('#new-dialog').close(); await loadState(); currentCase = null; location.hash = `case/${result.id}`; toast('Investigation created.');
  } catch (error) { $('#dialog-error').textContent = error.message; } finally { button.disabled = false; }
});
$('#main').addEventListener('click', async event => {
  const button = event.target.closest('[data-action]'); if (!button || button.disabled) return;
  const name = button.dataset.action;
  if (name === 'new') return showNew();
  if (name === 'open-case') { location.hash = `case/${button.dataset.id}`; return; }
  if (name === 'stage') { selectedStage = button.dataset.id; activeTab = 'reconstruction'; $('#main').innerHTML = caseView(currentCase); return; }
  if (name === 'tab') { activeTab = button.dataset.id; $('#main').innerHTML = caseView(currentCase); return; }
  if (name === 'source') {
    activeTab = 'transcript'; $('#main').innerHTML = caseView(currentCase);
    const source = document.getElementById(`msg-${button.dataset.id}`); if (source) { source.classList.add('highlighted'); source.scrollIntoView({behavior: 'smooth', block: 'center'}); } return;
  }
  button.disabled = true;
  try {
    if (name === 'export-json' || name === 'export-md') await download(name === 'export-json' ? 'json' : 'md');
    else if (name === 'stop') { await api('/api/controls', {stopped: button.dataset.stopped === 'true'}); await render(true); toast(button.dataset.stopped === 'true' ? 'Emergency stop applied and persisted.' : 'Research resumed.'); }
    else {
      const base = `/api/cases/${currentCase.id}`;
      if (name === 'step' || name === 'run') await api(`${base}/simulate`, {all_steps: name === 'run'});
      if (name === 'status') await api(`${base}/status`, {status: button.dataset.status});
      if (name === 'decide') await api(`${base}/drafts/${button.dataset.id}`, {decision: button.dataset.decision});
      if (name === 'model') { button.textContent = 'Analyzing locally…'; const result = await api(`${base}/analyze`, {}); toast(`${result.accepted} source-linked hypotheses ${result.cached ? 'loaded from cache' : 'recorded'}.`); }
      await render(true);
    }
  } catch (error) { toast(error.message); } finally { if (button.isConnected) button.disabled = false; }
});
$('#main').addEventListener('submit', async event => {
  if (event.target.id !== 'message-form') return;
  event.preventDefault(); const button = $('button', event.target); button.disabled = true;
  try { await api(`/api/cases/${currentCase.id}/messages`, {text: $('#message-text').value, idempotency_key: eventKey()}); await render(true); toast('Evidence recorded. Check the case state and persona review queue.'); }
  catch (error) { toast(error.message); } finally { if (button.isConnected) button.disabled = false; }
});
$('#main').addEventListener('input', event => {
  if (event.target.id !== 'case-search') return;
  const position = event.target.selectionStart; query = event.target.value; $('#main').innerHTML = casesView(); $('#case-search').focus(); $('#case-search').setSelectionRange(position, position);
});
$('#main').addEventListener('change', event => { if (event.target.id === 'status-filter') { statusFilter = event.target.value; $('#main').innerHTML = casesView(); } });
window.addEventListener('hashchange', () => render().catch(error => { $('#main').innerHTML = `<p class="error">${escape(error.message)}</p><a class="text-link" href="#cases">Return to investigations</a>`; }));
