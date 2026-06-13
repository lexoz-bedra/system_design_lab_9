// Theme
const html = document.documentElement;
const themeBtn = document.getElementById('theme-toggle');
themeBtn.addEventListener('click', () => {
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  themeBtn.querySelector('.theme-icon').textContent = isDark ? '☽' : '☀';
  themeBtn.querySelector('.theme-label').textContent = isDark ? 'Тёмная' : 'Светлая';
});

// Tab navigation
const tabBtns = document.querySelectorAll('.tab-nav-btn');
function switchTab(name) {
  tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach(s => {
    s.classList.toggle('active', s.id === 'tab-' + name);
    s.classList.toggle('hidden', s.id !== 'tab-' + name);
  });
}
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    if (!btn.classList.contains('locked')) switchTab(btn.dataset.tab);
  });
});

function unlockTab(name) {
  const btn = document.querySelector(`.tab-nav-btn[data-tab="${name}"]`);
  if (btn) btn.classList.remove('locked');
}

// Elements
const selYear = document.getElementById('sel-year');
const selQuarter = document.getElementById('sel-quarter');
const btnDownload = document.getElementById('btn-download');
const downloadProgressWrap = document.getElementById('download-progress-wrap');
const downloadBar = document.getElementById('download-bar');
const downloadStatusText = document.getElementById('download-status-text');

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const selectedFile = document.getElementById('selected-file');
const btnUpload = document.getElementById('btn-upload');

const pipelineStepsEl = document.getElementById('pipeline-steps');
const dataSummary = document.getElementById('data-summary');
const btnTrain = document.getElementById('btn-train');
const trainStatus = document.getElementById('train-status');
const metricsBlock = document.getElementById('metrics-block');
const featureChartWrap = document.getElementById('feature-chart-wrap');
const predictPanel = document.getElementById('predict-panel');
const btnPredict = document.getElementById('btn-predict');
const predictResult = document.getElementById('predict-result');

let pollInterval = null;
let pipelinePoll = null;
let renderedSteps = new Set();
let dataLoaded = false;
let modelTrained = false;

// Plotly layout helper
function plotlyLayout(extra = {}) {
  const dark = html.getAttribute('data-theme') !== 'light';
  return Object.assign({
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor:  'rgba(0,0,0,0)',
    font: { color: dark ? '#94a3b8' : '#64748b', size: 12 },
    margin: { t: 10, b: 40, l: 50, r: 20 },
    xaxis: { gridcolor: dark ? '#334155' : '#e2e8f0', zerolinecolor: dark ? '#334155' : '#e2e8f0' },
    yaxis: { gridcolor: dark ? '#334155' : '#e2e8f0', zerolinecolor: dark ? '#334155' : '#e2e8f0' },
  }, extra);
}
const PLOTLY_CONF = { responsive: true, displayModeBar: false };

// Period selectors
async function loadPeriods() {
  const { years, quarters } = await fetch('/api/periods').then(r => r.json());
  years.forEach(y => selYear.add(new Option(y, y)));
  quarters.forEach(q => selQuarter.add(new Option(q.label, q.value)));
  selYear.value = years[years.length - 1];
  selQuarter.value = 1;
}
loadPeriods();
loadZones();

async function loadZones() {
  try {
    const zones = await fetch('/api/zones').then(r => r.json());
    if (!Array.isArray(zones)) return;
    const puSel = document.getElementById('p-pu');
    const doSel = document.getElementById('p-do');
    zones.forEach(z => {
      puSel.add(new Option(z.label, z.id));
      doSel.add(new Option(z.label, z.id));
    });
    // Default: Midtown Center (161) → JFK Airport (132)
    puSel.value = 161;
    doSel.value = 132;
  } catch {}
}

// Source tabs
document.querySelectorAll('.source-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.source-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-download').classList.toggle('hidden', tab.dataset.source !== 'download');
    document.getElementById('panel-file').classList.toggle('hidden', tab.dataset.source !== 'file');
  });
});

// Download
btnDownload.addEventListener('click', async () => {
  const year = parseInt(selYear.value);
  const quarter = parseInt(selQuarter.value);
  btnDownload.disabled = true;
  downloadProgressWrap.classList.remove('hidden');
  downloadBar.style.width = '0%';
  downloadStatusText.textContent = 'Подготовка...';
  downloadStatusText.classList.remove('hidden');
  renderedSteps.clear();
  pipelineStepsEl.innerHTML = '';

  await fetch('/api/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ year, quarter }),
  });

  clearInterval(pollInterval);
  pollInterval = setInterval(pollDownloadStatus, 800);
});

async function pollDownloadStatus() {
  let data;
  try { data = await fetch('/api/status').then(r => r.json()); } catch { return; }

  if (data.error) {
    clearInterval(pollInterval);
    downloadStatusText.textContent = 'Ошибка: ' + data.error;
    btnDownload.disabled = false;
    return;
  }
  if (data.downloading) {
    const pct = data.download_progress, mIdx = data.download_month_idx || 0;
    downloadBar.style.width = pct + '%';
    downloadStatusText.textContent = `Скачивание месяца ${mIdx + 1}/3... ${pct}%`;
    return;
  }
  if (data.pipeline_running || data.pipeline_steps_count > 0 || data.data_loaded) {
    clearInterval(pollInterval);
    downloadBar.style.width = '100%';
    downloadStatusText.textContent = 'Файлы скачаны, запускается обработка...';
    btnDownload.disabled = false;
    startPipelineUI();
  }
}

// File upload
dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', e => {
  e.preventDefault(); dropzone.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });
function setFile(file) {
  selectedFile.textContent = `📄 ${file.name} (${formatSize(file.size)})`;
  btnUpload.disabled = false;
}
btnUpload.addEventListener('click', async () => {
  if (!fileInput.files[0]) return;
  btnUpload.disabled = true;
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  const data = await fetch('/api/upload', { method: 'POST', body: formData }).then(r => r.json());
  if (data.error) { alert('Ошибка: ' + data.error); btnUpload.disabled = false; return; }
  renderedSteps.clear();
  pipelineStepsEl.innerHTML = '';
  startPipelineUI();
});

function showNextBtn(tabId, nextTab, label) {
  const tab = document.getElementById(tabId);
  if (tab.querySelector('.next-tab-btn')) return;
  const btn = document.createElement('button');
  btn.className = 'btn btn-primary next-tab-btn';
  btn.style.cssText = 'margin-top:20px;width:100%';
  btn.textContent = label + ' →';
  btn.addEventListener('click', () => switchTab(nextTab));
  tab.appendChild(btn);
}

// Pipeline UI
function startPipelineUI() {
  unlockTab('pipeline');
  showNextBtn('tab-load', 'pipeline', 'Перейти к предобработке');
  clearInterval(pipelinePoll);
  pipelinePoll = setInterval(pollPipeline, 900);
}

async function pollPipeline() {
  let data;
  try { data = await fetch('/api/pipeline/status').then(r => r.json()); } catch { return; }
  if (data.error) {
    clearInterval(pipelinePoll);
    pipelineStepsEl.innerHTML += `<div class="status-msg error">${data.error}</div>`;
    return;
  }
  (data.steps || []).forEach(step => {
    if (!renderedSteps.has(step.id)) {
      renderedSteps.add(step.id);
      pipelineStepsEl.appendChild(renderStep(step));
    }
  });
  if (data.done) {
    clearInterval(pipelinePoll);
    const last = data.steps[data.steps.length - 1];
    onPipelineDone(last);
  }
}

function renderStep(step) {
  const wrap = document.createElement('div');
  wrap.className = 'pipeline-step';
  const badge = step.removed != null
    ? `<span class="badge-removed">−${step.removed.toLocaleString()} строк</span>` : '';
  const rowInfo = step.rows_before != null
    ? `<span class="row-count">${step.rows_before.toLocaleString()} → <strong>${step.rows_after.toLocaleString()}</strong></span>`
    : `<span class="row-count"><strong>${step.rows_after.toLocaleString()}</strong> строк</span>`;
  wrap.innerHTML = `
    <div class="step-header">
      <span class="step-icon">✓</span>
      <div class="step-info">
        <div class="step-title">${step.name}</div>
        <div class="step-desc">${step.desc}</div>
      </div>
      <div class="step-meta">${rowInfo}${badge}</div>
    </div>
    <div class="step-table-wrap">${renderTable(step.sample)}</div>`;
  return wrap;
}

function renderTable({ columns, rows }) {
  const ths = columns.map(c => `<th>${c}</th>`).join('');
  const trs = rows.map(row => `<tr>${row.map(v => `<td>${v == null ? '–' : v}</td>`).join('')}</tr>`).join('');
  return `<table class="data-table"><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
}

function onPipelineDone(lastStep) {
  dataLoaded = true;
  unlockTab('train');
  showNextBtn('tab-pipeline', 'train', 'Перейти к обучению');
  if (lastStep) {
    dataSummary.innerHTML = `
      <div class="stat-card"><div class="stat-value">${lastStep.rows_after.toLocaleString()}</div><div class="stat-label">Строк после обработки</div></div>`;
  }
}

// Train
btnTrain.addEventListener('click', async () => {
  btnTrain.disabled = true;
    setStatus('Обучение запущено...', 'info');
  metricsBlock.classList.add('hidden');
  featureChartWrap.classList.add('hidden');
  await fetch('/api/train', { method: 'POST' });
  clearInterval(pollInterval);
  pollInterval = setInterval(pollTrainStatus, 2000);
});

async function pollTrainStatus() {
  const data = await fetch('/api/status').then(r => r.json());
  if (data.error) {
    clearInterval(pollInterval);
    setStatus('Ошибка: ' + data.error, 'error');
    btnTrain.disabled = false;
    return;
  }
  if (!data.training && data.metrics) {
    clearInterval(pollInterval);
    setStatus('Модель обучена', 'success');
    modelTrained = true;
    btnPredict.disabled = false;
    renderMetrics(data.metrics);
    loadFeatureChart(data.metrics.feature_importance);
    unlockTab('viz');
    loadDashboard();
  }
}

function renderMetrics(m) {
  metricsBlock.innerHTML = `
    <div class="metric-card"><div class="metric-value">${m.mae}</div><div class="metric-label">MAE ($)</div></div>
    <div class="metric-card"><div class="metric-value">${m.rmse}</div><div class="metric-label">RMSE ($)</div></div>
    <div class="metric-card"><div class="metric-value">${m.r2}</div><div class="metric-label">R²</div></div>
    <div class="metric-card"><div class="metric-value">${m.train_size.toLocaleString()}</div><div class="metric-label">Train rows</div></div>
    <div class="metric-card"><div class="metric-value">${m.test_size.toLocaleString()}</div><div class="metric-label">Test rows</div></div>`;
  metricsBlock.classList.remove('hidden');
}

function loadFeatureChart(importance) {
  const items = Object.entries(importance).sort((a, b) => a[1] - b[1]);
  const dark = html.getAttribute('data-theme') !== 'light';
  Plotly.newPlot('feature-chart', [{
    type: 'bar', orientation: 'h',
    x: items.map(i => i[1]),
    y: items.map(i => i[0]),
    marker: { color: '#60a5fa' },
  }], plotlyLayout({ height: 240, margin: { t: 5, b: 30, l: 120, r: 20 } }), PLOTLY_CONF);
  featureChartWrap.classList.remove('hidden');
}

// Predict
btnPredict.addEventListener('click', async () => {
  const body = {
    trip_distance: parseFloat(document.getElementById('p-distance').value),
    trip_duration_min: parseFloat(document.getElementById('p-duration').value),
    hour: parseInt(document.getElementById('p-hour').value),
    day_of_week: parseInt(document.getElementById('p-dow').value),
    passenger_count: parseInt(document.getElementById('p-passengers').value),
    pickup_zone_id: parseInt(document.getElementById('p-pu').value),
    dropoff_zone_id: parseInt(document.getElementById('p-do').value),
  };
  btnPredict.disabled = true;
  const data = await fetch('/api/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }).then(r => r.json());
  btnPredict.disabled = false;
  if (data.error) { predictResult.innerHTML = `<div class="predict-label" style="color:var(--danger)">${data.error}</div>`; }
  else { predictResult.innerHTML = `<div class="predict-fare">$${data.fare}</div><div class="predict-label">ожидаемая стоимость поездки</div>`; }
  predictResult.classList.remove('hidden');
});

// Dashboard
async function loadDashboard() {
  // KPI cards
  const status = await fetch('/api/status').then(r => r.json());
  if (status.stats) renderKPI(status.stats);

  // Charts in parallel
  await Promise.all([
    loadPlotlyChart('/api/charts/heatmap', 'chart-heatmap'),
    loadPlotlyChart('/api/charts/revenue_zones', 'chart-revenue'),
    loadPlotlyChart('/api/charts/hourly', 'chart-hourly'),
    loadPlotlyChart('/api/charts/fare_dist', 'chart-fare'),
  ]);
}

function renderKPI(stats) {
  const kpi = document.getElementById('kpi-cards');
  kpi.innerHTML = `
    <div class="kpi-card"><div class="kpi-value">${(stats.total_rows / 1e6).toFixed(2)}M</div><div class="kpi-label">Поездок</div></div>
    <div class="kpi-card"><div class="kpi-value">$${stats.avg_fare}</div><div class="kpi-label">Средняя стоимость</div></div>
    <div class="kpi-card"><div class="kpi-value">${stats.avg_distance} mi</div><div class="kpi-label">Средняя дистанция</div></div>
    <div class="kpi-card"><div class="kpi-value">${stats.avg_duration} мин</div><div class="kpi-label">Средняя длительность</div></div>`;
}

async function loadPlotlyChart(url, elId) {
  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const fig = await res.json();
    const theme = plotlyLayout();
    // Theme colors override Python defaults, but chart-specific layout (margin, legend) is preserved
    const layout = Object.assign({}, fig.layout, {
      paper_bgcolor: theme.paper_bgcolor,
      plot_bgcolor: theme.plot_bgcolor,
      font: theme.font,
      xaxis: Object.assign({}, theme.xaxis, fig.layout.xaxis),
      yaxis: Object.assign({}, theme.yaxis, fig.layout.yaxis),
    });
    await Plotly.newPlot(elId, fig.data, layout, PLOTLY_CONF);
    Plotly.Plots.resize(document.getElementById(elId));
  } catch (e) {
    document.getElementById(elId).innerHTML = `<p style="color:var(--muted);padding:20px">${e.message}</p>`;
  }
}

function setStatus(msg, type) {
  trainStatus.className = 'status-msg';
  if (!msg) { trainStatus.classList.add('hidden'); return; }
  trainStatus.classList.add(type || 'info');
  trainStatus.classList.remove('hidden');
  trainStatus.textContent = msg;
}
function formatSize(b) {
  if (b > 1e9) return (b/1e9).toFixed(1)+' GB';
  if (b > 1e6) return (b/1e6).toFixed(1)+' MB';
  return (b/1e3).toFixed(0)+' KB';
}
