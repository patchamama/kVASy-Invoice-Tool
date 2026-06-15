/* EVB Invoice Tool — app.js */

const state = {
  activeEndpointId: null,
  modalDocNr: null,
  modalCompanyNr: null,
};

// ── Tab management ────────────────────────────────────────────────

function showTab(id, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.remove('hidden');
  if (btn) btn.classList.add('active');
  if (id === 't3') loadDownloads();
}

// ── Toast ─────────────────────────────────────────────────────────

function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.className = `fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg max-w-sm transition-opacity`;
  const colors = {
    info:    'bg-indigo-600 text-white',
    success: 'bg-emerald-600 text-white',
    error:   'bg-red-600 text-white',
  };
  el.classList.add(...(colors[type] || colors.info).split(' '));
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 4000);
}

// ── Active endpoint badge ─────────────────────────────────────────

function setActiveEndpoint(id) {
  state.activeEndpointId = id;
  document.getElementById('active-ep-badge').textContent = id || 'none';
  const sel = document.getElementById('ep-select');
  if (sel && id) sel.value = id;
}

// ── Helpers ───────────────────────────────────────────────────────

function envBadge(env) {
  const cls = env === 'prod' ? 'badge-prod' : 'badge-test';
  return `<span class="badge-env ${cls}">${env}</span>`;
}

function spinner() {
  return '<span class="spinner"></span>';
}

async function api(method, url, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  return res.json();
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

// ── Tab 1: Connection Test ────────────────────────────────────────

async function testAll() {
  const btn = document.getElementById('btn-test-all');
  const container = document.getElementById('conn-results');
  btn.disabled = true;
  btn.innerHTML = `${spinner()} Testing…`;
  container.innerHTML = `<div class="flex items-center gap-3 py-6 justify-center text-gray-400 text-sm">${spinner()} Pinging 9 endpoints — this may take up to 30 s…</div>`;

  try {
    const results = await api('POST', '/api/test-connection', { endpoint_id: 'all' });

    if (!Array.isArray(results)) {
      container.innerHTML = `<p class="text-red-500 text-sm">${results.error || 'Unexpected response'}</p>`;
      return;
    }

    const ok = results.filter(r => r.ok).length;

    // Group by division
    const byDiv = {};
    results.forEach(r => {
      if (!byDiv[r.division]) byDiv[r.division] = [];
      byDiv[r.division].push(r);
    });

    const divOrder = ['Netz', 'Vertrieb', 'SEG'];
    const divColors = { Netz: 'bg-blue-50', Vertrieb: 'bg-violet-50', SEG: 'bg-amber-50' };
    const divText   = { Netz: 'text-blue-700', Vertrieb: 'text-violet-700', SEG: 'text-amber-700' };

    let html = `
      <div class="flex items-center gap-4 mb-5 p-3 bg-gray-50 rounded-xl border border-gray-200">
        <div class="text-2xl font-bold ${ok > 0 ? 'text-emerald-600' : 'text-red-500'}">${ok}<span class="text-gray-400 font-normal text-base">/${results.length}</span></div>
        <div class="text-sm text-gray-600">endpoints reachable</div>
        <div class="ml-auto flex gap-2 text-xs text-gray-500">
          <span class="badge-env badge-ok">✓ ${ok} OK</span>
          ${results.length - ok > 0 ? `<span class="badge-env badge-error">✗ ${results.length - ok} failed</span>` : ''}
        </div>
      </div>`;

    for (const div of divOrder) {
      const group = byDiv[div] || [];
      if (!group.length) continue;
      const divOk = group.filter(r => r.ok).length;
      const headerColor = divColors[div] || 'bg-gray-50';
      const textColor   = divText[div]   || 'text-gray-700';

      html += `
        <div class="mb-4 rounded-xl border border-gray-200 overflow-hidden">
          <div class="${headerColor} px-4 py-2.5 flex items-center justify-between border-b border-gray-200">
            <span class="font-semibold text-sm ${textColor}">${div}</span>
            <span class="text-xs ${textColor} opacity-70">${divOk}/${group.length} reachable</span>
          </div>
          <table class="w-full text-left">
            <thead class="text-xs text-gray-400 border-b border-gray-100">
              <tr>
                <th class="px-4 py-2 font-medium w-20">Env</th>
                <th class="px-4 py-2 font-medium">User</th>
                <th class="px-4 py-2 font-medium">URL</th>
                <th class="px-4 py-2 font-medium w-24">Status</th>
                <th class="px-4 py-2 font-medium w-20">Latency</th>
                <th class="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>`;

      group.forEach(r => {
        const shortUrl = r.url ? r.url.replace('http://evb.sivdc.systems:5004/ep/any/', '').replace('/webservices/ias_invoice_receipt_w01/service', '') : '';
        const errorTip = r.error ? r.error.replace(/"/g, '&quot;') : '';
        html += `
              <tr class="border-b border-gray-50 hover:bg-gray-50 ${r.ok ? '' : 'opacity-60'}">
                <td class="px-4 py-3">${envBadge(r.environment)}</td>
                <td class="px-4 py-3 font-mono text-xs text-gray-600">${r.username || ''}</td>
                <td class="px-4 py-3">
                  <span class="font-mono text-xs text-gray-500" title="${r.url || ''}">${shortUrl}</span>
                </td>
                <td class="px-4 py-3">
                  ${r.ok
                    ? '<span class="badge-env badge-ok">✓ OK</span>'
                    : `<span class="badge-env badge-error" title="${errorTip}">✗ Error</span>`}
                </td>
                <td class="px-4 py-3 text-xs text-gray-500 font-mono">${r.ok ? r.latency_ms + ' ms' : '—'}</td>
                <td class="px-4 py-3">
                  ${r.ok ? `<button onclick="selectAndBrowse('${r.id}')"
                    class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-1 rounded-md transition-colors font-medium whitespace-nowrap">
                    Browse →
                  </button>` : `<span class="text-xs text-red-400 truncate max-w-xs block" title="${errorTip}">${r.error ? r.error.substring(0, 60) : ''}</span>`}
                </td>
              </tr>`;
      });

      html += `</tbody></table></div>`;
    }

    container.innerHTML = html;
    toast(`${ok}/${results.length} endpoints reachable`, ok > 0 ? 'success' : 'error');
  } catch (e) {
    container.innerHTML = `<p class="text-red-500 text-sm py-4">Error: ${e.message}</p>`;
    toast('Connection test failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Test All Endpoints`;
  }
}

function selectAndBrowse(endpointId) {
  setActiveEndpoint(endpointId);
  showTab('t2', document.querySelectorAll('.tab-btn')[1]);
}

// ── Tab 2: Invoice Browser ────────────────────────────────────────

async function initEndpointSelect() {
  const data = await api('GET', '/api/endpoints');
  const sel = document.getElementById('ep-select');
  if (!Array.isArray(data)) return;
  data.forEach(ep => {
    const opt = document.createElement('option');
    opt.value = ep.id;
    opt.textContent = `${ep.mandant} — ${ep.division} (${ep.environment})`;
    sel.appendChild(opt);
  });
}

function onEpChange() {
  const id = document.getElementById('ep-select').value;
  setActiveEndpoint(id || null);
  // Reset company dropdown when endpoint changes
  const sel = document.getElementById('company-select');
  sel.innerHTML = '<option value="">— discover or type below —</option>';
}

async function discoverCompanies() {
  const epId = document.getElementById('ep-select').value || state.activeEndpointId;
  if (!epId) { toast('Select an endpoint first', 'error'); return; }

  const btn = document.getElementById('btn-discover');
  btn.disabled = true;
  btn.innerHTML = `${spinner()} Discovering…`;

  try {
    const data = await api('GET', `/api/discover-companies/${epId}`);
    if (data.error) { toast('Error: ' + data.error, 'error'); return; }

    const sel = document.getElementById('company-select');
    sel.innerHTML = '<option value="">— select company —</option>';
    (data.companies || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.company_number;
      opt.textContent = `${c.company_number}${c.company_id ? ` (id: ${c.company_id})` : ''}`;
      sel.appendChild(opt);
    });

    if (data.companies.length === 1) sel.value = data.companies[0].company_number;

    toast(`Found ${data.companies.length} company number(s)`, 'success');
  } catch (e) {
    toast('Discovery failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg> Auto-Discover Companies`;
  }
}

function getCompanyNumber() {
  const fromSelect = document.getElementById('company-select').value;
  const fromManual = document.getElementById('company-manual').value.trim();
  return fromSelect || fromManual;
}

async function listInvoices() {
  const epId = document.getElementById('ep-select').value || state.activeEndpointId;
  if (!epId) { toast('Select an endpoint first', 'error'); return; }
  const company = getCompanyNumber();
  if (!company) { toast('Select or enter a company number', 'error'); return; }

  const belegNr = document.getElementById('beleg-nr').value.trim() || null;

  const btn = document.getElementById('btn-list');
  const status = document.getElementById('invoice-status');
  const results = document.getElementById('invoice-results');
  btn.disabled = true;
  btn.innerHTML = `${spinner()} Loading…`;
  status.textContent = 'Fetching invoices…';
  status.classList.remove('hidden');
  results.innerHTML = '';

  try {
    const data = await api('POST', '/api/list-invoices', {
      endpoint_id: epId,
      company_number: company,
      beleg_nr: belegNr,
    });

    status.classList.add('hidden');

    if (data.error) {
      results.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">${data.error}</div>`;
      toast('Error: ' + data.error, 'error');
      return;
    }

    const invoices = data.invoices || [];
    if (!invoices.length) {
      results.innerHTML = `<p class="text-sm text-gray-400 py-8 text-center">No invoices found for company <strong>${company}</strong></p>`;
      toast('No invoices found', 'info');
      return;
    }

    results.innerHTML = renderInvoiceTable(invoices, epId, company);
    toast(`${invoices.length} invoice(s) loaded`, 'success');
  } catch (e) {
    status.classList.add('hidden');
    results.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">${e.message}</div>`;
    toast('Request failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg> List Invoices`;
  }
}

function renderInvoiceTable(invoices, epId, company) {
  // Detect all unique keys across invoices, prioritize common fields
  const priority = ['belegNr', 'document_number', 'rechnungNrLang', 'invoice_number',
    'kreditornr', 'creditor_number', 'bruttobetrag', 'gross_amount',
    'eingangsdatum', 'receipt_date', 'rechnungsdatum', 'invoice_date'];

  const allKeys = new Set();
  invoices.forEach(inv => Object.keys(inv).forEach(k => allKeys.add(k)));

  const cols = [...priority.filter(k => allKeys.has(k)),
    ...[...allKeys].filter(k => !priority.includes(k))].slice(0, 8);

  const docKey = cols.find(k => ['belegNr', 'document_number'].includes(k));
  const compKey = cols.find(k => ['betriebNr', 'company_number'].includes(k));

  const header = cols.map(k => `<th class="px-3 py-2 font-medium text-left whitespace-nowrap">${k}</th>`).join('');
  const rows = invoices.map((inv, i) => {
    const docNr = inv[docKey] || inv.belegNr || inv.document_number || '';
    const compNr = inv[compKey] || inv.betriebNr || inv.company_number || company;
    const cells = cols.map(k => {
      const v = inv[k];
      return `<td class="px-3 py-2 text-xs text-gray-700 whitespace-nowrap">${v != null ? String(v).substring(0, 40) : '—'}</td>`;
    }).join('');
    return `
      <tr class="border-b border-gray-100 hover:bg-gray-50">
        ${cells}
        <td class="px-3 py-2 whitespace-nowrap">
          <div class="flex gap-1">
            <button onclick="showDetails('${epId}','${docNr}','${compNr}')"
              class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-2 py-1 rounded transition-colors">Details</button>
            <button onclick="quickDownload('${epId}','${docNr}','${compNr}','json')"
              class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-2 py-1 rounded transition-colors">JSON</button>
            <button onclick="quickDownload('${epId}','${docNr}','${compNr}','xml')"
              class="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 px-2 py-1 rounded transition-colors">XML</button>
          </div>
        </td>
      </tr>`;
  }).join('');

  return `
    <div class="text-xs text-gray-500 mb-2">${invoices.length} invoice(s) — company: <strong>${company}</strong></div>
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead class="bg-gray-50 text-xs text-gray-500 border-b border-gray-200">
          <tr>${header}<th class="px-3 py-2 font-medium">Actions</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

async function showDetails(epId, docNr, compNr) {
  state.modalDocNr = docNr;
  state.modalCompanyNr = compNr;
  state.modalEpId = epId;

  document.getElementById('modal-title').textContent = `Invoice: ${docNr}`;
  document.getElementById('modal-body').innerHTML = `<div class="flex justify-center py-8">${spinner()}</div>`;
  document.getElementById('modal').classList.remove('hidden');

  try {
    const data = await api('POST', '/api/get-invoice', {
      endpoint_id: epId,
      document_number: docNr,
      company_number: compNr,
    });
    if (data.error) {
      document.getElementById('modal-body').innerHTML = `<p class="text-red-500 text-sm">${data.error}</p>`;
      return;
    }
    document.getElementById('modal-body').innerHTML = renderDetailTable(data.invoice || {});
  } catch (e) {
    document.getElementById('modal-body').innerHTML = `<p class="text-red-500 text-sm">${e.message}</p>`;
  }
}

function renderDetailTable(obj, depth = 0) {
  if (!obj || typeof obj !== 'object') return `<span>${obj}</span>`;
  if (Array.isArray(obj)) {
    return obj.map((item, i) => `
      <div class="mb-2 border-l-2 border-indigo-200 pl-3">
        <div class="text-xs text-gray-400 mb-1">Item ${i + 1}</div>
        ${renderDetailTable(item, depth + 1)}
      </div>`).join('');
  }
  const rows = Object.entries(obj).map(([k, v]) => {
    const isObj = v && typeof v === 'object';
    return `
      <tr class="border-b border-gray-50">
        <td class="py-1.5 pr-4 text-xs font-medium text-gray-500 whitespace-nowrap w-48">${k}</td>
        <td class="py-1.5 text-xs text-gray-800 ${isObj ? '' : 'font-mono'}">
          ${isObj ? renderDetailTable(v, depth + 1) : (v != null ? String(v) : '<span class="text-gray-300">—</span>')}
        </td>
      </tr>`;
  }).join('');
  return `<table class="w-full"><tbody>${rows}</tbody></table>`;
}

function closeModal(e) {
  if (e.target === document.getElementById('modal')) {
    document.getElementById('modal').classList.add('hidden');
  }
}

async function downloadFromModal(fmt) {
  if (!state.modalDocNr) return;
  await quickDownload(state.modalEpId, state.modalDocNr, state.modalCompanyNr, fmt);
}

async function quickDownload(epId, docNr, compNr, fmt) {
  try {
    const data = await api('POST', '/api/download-invoice', {
      endpoint_id: epId,
      document_number: docNr,
      company_number: compNr,
      format: fmt,
    });
    if (data.error) { toast('Download error: ' + data.error, 'error'); return; }
    toast(`Saved: ${data.filename}`, 'success');
    updateDownloadBadge();
  } catch (e) {
    toast('Download failed: ' + e.message, 'error');
  }
}

// ── Tab 3: Downloads ──────────────────────────────────────────────

async function loadDownloads() {
  const container = document.getElementById('dl-results');
  container.innerHTML = `<div class="flex justify-center py-8">${spinner()}</div>`;
  try {
    const data = await api('GET', '/api/downloads');
    const files = data.files || [];
    updateDownloadBadge(files.length);

    if (!files.length) {
      container.innerHTML = '<p class="text-sm text-gray-400 py-8 text-center">No downloaded files yet</p>';
      return;
    }

    const rows = files.map(f => `
      <tr class="border-b border-gray-100 hover:bg-gray-50">
        <td class="px-4 py-3 font-mono text-xs text-gray-800">${f.filename}</td>
        <td class="px-4 py-3 text-sm text-gray-500">${fmtSize(f.size)}</td>
        <td class="px-4 py-3 text-sm text-gray-500">${fmtDate(f.modified)}</td>
        <td class="px-4 py-3">
          <a href="/api/downloads/${encodeURIComponent(f.filename)}" download
            class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-1 rounded transition-colors">
            Download
          </a>
        </td>
      </tr>`).join('');

    container.innerHTML = `
      <table class="w-full text-left">
        <thead class="bg-gray-50 text-xs text-gray-500 border-b border-gray-200">
          <tr>
            <th class="px-4 py-2 font-medium">Filename</th>
            <th class="px-4 py-2 font-medium">Size</th>
            <th class="px-4 py-2 font-medium">Date</th>
            <th class="px-4 py-2 font-medium"></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    container.innerHTML = `<p class="text-red-500 text-sm py-4 text-center">${e.message}</p>`;
  }
}

function updateDownloadBadge(count) {
  const badge = document.getElementById('dl-count-badge');
  if (count === undefined) {
    // fire-and-forget refresh
    api('GET', '/api/downloads').then(d => updateDownloadBadge((d.files || []).length));
    return;
  }
  if (count > 0) {
    badge.textContent = count;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

// ── Init ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initEndpointSelect();
  updateDownloadBadge();
});
