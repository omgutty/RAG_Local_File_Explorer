/* Chat page — SSE-driven Q&A with live pipeline stage updates */

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const messages = document.getElementById('chat-messages');
  const pipelineDetail = document.getElementById('pipeline-detail-chat');

  let history = [];

  function addMessage(role, content, meta) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = content;
    if (meta) {
      const metaDiv = document.createElement('div');
      metaDiv.className = 'msg-meta';
      metaDiv.textContent = meta;
      div.appendChild(metaDiv);
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showDetail(detailId) {
    pipelineDetail.querySelectorAll('.detail-card').forEach(el => {
      el.classList.toggle('visible', el.dataset.detail === detailId);
    });
  }

  function clearDetails() {
    pipelineDetail.querySelectorAll('.detail-card').forEach(el => {
      el.classList.remove('visible');
    });
  }

  async function sendQuery(query) {
    if (!query.trim()) return;

    disableInput(true);
    addMessage('user', escapeHtml(query));
    clearDetails();

    input.value = '';
    history.push({ role: 'user', content: query });

    try {
      const resp = await fetch('/chat/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, history }),
      });

      if (!resp.ok) {
        addMessage('assistant', `Error: ${resp.statusText}`);
        disableInput(false);
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));

            // Show pipeline stages
            if (data.type === 'stage') {
              // Update sidebar stage indicators if they exist
              const stages = document.querySelectorAll('[data-stage]');
              stages.forEach(el => {
                el.classList.remove('active', 'done');
                if (el.dataset.stage === data.stage) el.classList.add('active');
              });
            }

            if (data.type === 'progress') {
              if (data.stage === 'rewrite' && data.status === 'done') {
                showDetail('rewrite');
                const container = document.getElementById('rewrite-content');
                if (data.rewrites && data.rewrites.length > 0) {
                  container.innerHTML = `
                    <strong>Original:</strong> <em>${escapeHtml(data.original)}</em><br>
                    <strong>Rewrites:</strong>
                    <ol>${data.rewrites.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ol>
                  `;
                } else {
                  container.innerHTML = '<em>Rewrites disabled or failed — using original query only.</em>';
                }
              }

              if (data.stage === 'search' && data.status === 'done') {
                showDetail('search');
                const container = document.getElementById('search-content');
                container.innerHTML = `
                  <table>
                    <tr><th>Method</th><th>Results</th><th>Top Score</th></tr>
                    <tr><td>Dense</td><td>${data.dense_count}</td><td>${data.dense_top5?.[0]?.score ?? '-'}</td></tr>
                    <tr><td>Sparse</td><td>${data.sparse_count}</td><td>${data.sparse_top5?.[0]?.score ?? '-'}</td></tr>
                    <tr><td><strong>RRF Fused</strong></td><td>${data.fused_count}</td><td>${data.rrf_top5?.[0]?.score ?? '-'}</td></tr>
                  </table>
                `;
              }

              if (data.stage === 'rerank' && data.status === 'done') {
                showDetail('rerank');
                const container = document.getElementById('rerank-content');
                if (data.top_chunks) {
                  container.innerHTML = '<strong>Top chunks after re-ranking:</strong>';
                  data.top_chunks.forEach((chunk, i) => {
                    container.innerHTML += `
                      <div class="chunk-card mt-8">
                        <div class="chunk-meta">
                          <span class="chunk-badge">#${i+1}</span>
                          <span class="chunk-badge">Score: ${chunk.score}</span>
                        </div>
                        <div class="chunk-text">${chunk.text_preview}</div>
                      </div>
                    `;
                  });
                }
              }
            }

            // Final answer
            if (data.type === 'answer') {
              const citations = data.citations?.length
                ? `\n\nSources: ${data.citations.join(', ')}`
                : '';
              addMessage('assistant', renderMarkdown(data.content) + citations);
              history.push({ role: 'assistant', content: data.content });

              // Mark sidebar stages as done
              document.querySelectorAll('[data-stage]').forEach(el => {
                el.classList.remove('active');
                el.classList.add('done');
              });
            }

          } catch (e) {
            console.warn('Failed to parse SSE line:', line, e);
          }
        }
      }
    } catch (e) {
      addMessage('assistant', `Connection error: ${e.message}`);
    } finally {
      disableInput(false);
    }
  }

  function disableInput(disabled) {
    input.disabled = disabled;
    sendBtn.disabled = disabled;
    if (!disabled) input.focus();
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderMarkdown(text) {
    // Simple markdown rendering (bold, code, newlines)
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\[(Chunk \d+)\]/g, '<span class="chunk-badge referenced">$1</span>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  sendBtn.addEventListener('click', () => sendQuery(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuery(input.value);
    }
  });
});
