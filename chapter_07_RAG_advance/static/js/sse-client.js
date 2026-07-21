/* SSE client for /ingest real-time pipeline tracking */

document.addEventListener('DOMContentLoaded', () => {
  const ingestUrl = window.INGEST_URL;
  if (!ingestUrl) return;

  const source = new EventSource(ingestUrl);
  const stages = document.querySelectorAll('[data-stage]');
  const detailPanels = document.querySelectorAll('[data-detail]');
  const completeCard = document.getElementById('complete-card');
  const completeMsg = document.getElementById('complete-message');

  // Overall progress
  const progressFill  = document.getElementById('overall-progress-fill');
  const progressLabel = document.getElementById('overall-stage-label');
  const progressPct   = document.getElementById('overall-percentage');

  // Stage → weight mapping for overall % bar
  const STAGE_WEIGHTS = {
    warm:   0,
    read:   10,
    build:  25,
    chunk:  40,
    embed:  55,   // base; embed updates dynamically
    index:  85,
    done:  100,
  };

  let currentStage = null;
  let embedCurrent = 0;
  let embedTotal   = 0;

  function updateProgress(stage, extraPct) {
    const base = STAGE_WEIGHTS[stage] ?? 0;
    let pct   = base;
    if (stage === 'embed' && embedTotal > 0) {
      // Within embed: scale 55→85 based on progress
      const embedPct = embedCurrent / embedTotal;
      pct = 55 + embedPct * 30;  // 55 → 85
    }
    if (extraPct !== undefined) pct = extraPct;
    pct = Math.min(100, Math.max(0, pct));
    if (progressFill)  progressFill.style.width  = pct + '%';
    if (progressPct)   progressPct.textContent   = Math.round(pct) + '%';
    if (progressLabel) progressLabel.textContent = 'Stage: ' + (stage || '…');
  }

  function setStageActive(stageId) {
    currentStage = stageId;
    stages.forEach(el => {
      el.classList.remove('active', 'done');
      if (el.dataset.stage === stageId) el.classList.add('active');
    });
    updateProgress(stageId);
  }
  function setStageDone(stageId) {
    stages.forEach(el => {
      if (el.dataset.stage === stageId) {
        el.classList.remove('active');
        el.classList.add('done');
      }
    });
    // Advance overall bar to next stage's base weight
    if (stageId !== 'embed') updateProgress(stageId);
  }
  function showDetail(detailId) {
    detailPanels.forEach(el => {
      el.classList.toggle('visible', el.dataset.detail === detailId);
    });
  }

  source.addEventListener('stage', (e) => {
    const data = JSON.parse(e.data);
    setStageActive(data.stage);
  });

  source.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    if (data.status === 'done') {
      setStageDone(data.stage);
    }

    // ── Read stage ──
    if (data.stage === 'read' && data.status === 'done') {
      showDetail('read');
      const container = document.getElementById('read-stats');
      container.innerHTML = `
        <div class="stat"><div class="stat-value">${data.rows}</div><div class="stat-label">Rows</div></div>
        <div class="stat"><div class="stat-value">${data.columns.length}</div><div class="stat-label">Columns</div></div>
      `;
    }

    // ── Chunk stage ──
    if (data.stage === 'chunk' && data.status === 'done') {
      showDetail('chunk');
      const stats = document.getElementById('chunk-stats');
      stats.innerHTML = `
        <div class="stat"><div class="stat-value">${data.total_chunks}</div><div class="stat-label">Chunks</div></div>
        <div class="stat"><div class="stat-value">${data.avg_chars}</div><div class="stat-label">Avg chars</div></div>
        <div class="stat"><div class="stat-value">${data.min_chars}</div><div class="stat-label">Min chars</div></div>
        <div class="stat"><div class="stat-value">${data.max_chars}</div><div class="stat-label">Max chars</div></div>
      `;

      const hist = document.getElementById('chunk-histogram');
      if (data.histogram) {
        hist.innerHTML = '<strong class="text-muted">Chunk size distribution</strong>';
        const maxCount = Math.max(...data.histogram.map(b => b.count));
        data.histogram.forEach(bin => {
          const pct = maxCount > 0 ? (bin.count / maxCount * 100).toFixed(0) : 0;
          hist.innerHTML += `
            <div class="hist-bar">
              <span class="hist-label">${bin.bin_start}–${bin.bin_end}</span>
              <div class="hist-bar-fill" style="width:${pct}%"></div>
              <span class="text-muted" style="font-size:0.75rem;">${bin.count}</span>
            </div>
          `;
        });
      }

      const samples = document.getElementById('chunk-samples');
      if (data.samples) {
        samples.innerHTML = '<strong class="text-muted">Sample chunks (first 5)</strong>';
        data.samples.forEach(s => {
          samples.innerHTML += `
            <div class="chunk-card mt-8">
              <div class="chunk-meta">
                <span class="chunk-badge">Chunk ${s.index}</span>
                <span class="chunk-badge">Doc ${s.doc_index}</span>
                <span class="chunk-badge">chars ${s.start_char}–${s.end_char}</span>
              </div>
              <div class="chunk-text">${s.text}</div>
            </div>
          `;
        });
      }
    }

    // ── Embed stage ──
    if (data.stage === 'embed') {
      showDetail('embed');
      const progress = document.getElementById('embed-progress');

      if (data.status === 'embedding') {
        embedCurrent = data.current;
        embedTotal   = data.total;
        const pct = data.total > 0 ? ((data.current / data.total) * 100).toFixed(1) : 0;
        progress.innerHTML = `
          <div class="flex items-center justify-between mb-8">
            <span class="text-muted">Embedding: ${data.current} / ${data.total} chunks</span>
            <span class="text-muted" style="font-weight:600;">${pct}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${pct}%"></div>
          </div>
        `;
        updateProgress('embed');
      } else if (data.status === 'done') {
        progress.innerHTML = '<span class="text-muted" style="font-weight:600;">✅ Embedding complete</span>';
        updateProgress('embed', 85);
        const previews = document.getElementById('embed-previews');
        if (data.dense_preview) {
          previews.innerHTML = `
            <div class="mt-8">
              <strong class="text-muted">Dense vector preview (first ${data.dense_preview.length} dims)</strong>
              <div class="mono" style="overflow-x:auto;">[${data.dense_preview.join(', ')}]</div>
            </div>
            <div class="mt-8">
              <strong class="text-muted">Sparse top-5 tokens</strong>
              <table>
                <tr><th>Token ID</th><th>Weight</th></tr>
                ${(data.sparse_top5 || []).map(t => `<tr><td>${t.token_id}</td><td>${t.weight}</td></tr>`).join('')}
              </table>
            </div>
          `;
        }
      }
    }

    // ── Index stage ──
    if (data.stage === 'index' && data.status === 'done') {
      showDetail('index');
      const stats = document.getElementById('index-stats');
      stats.innerHTML = `
        <div class="stat"><div class="stat-value">${data.collection}</div><div class="stat-label">Collection</div></div>
        <div class="stat"><div class="stat-value">${data.points_count}</div><div class="stat-label">Points</div></div>
      `;
      updateProgress('done');
    }
  });

  source.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data);
    completeCard.style.display = 'block';
    completeMsg.textContent = data.message;
    updateProgress('done', 100);
    source.close();
  });

  source.addEventListener('error', (e) => {
    console.error('SSE error:', e);
  });
});
