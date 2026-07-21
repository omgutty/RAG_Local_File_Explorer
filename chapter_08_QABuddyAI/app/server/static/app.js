/* QABuddy.ai chat client: SSE streaming, source filters, citations, ingest. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const thread = $("#thread");
  const input = $("#q");
  const sendBtn = $("#send");
  const statusLine = $("#status-line");
  const history = []; // {role, content}
  let busy = false;

  // ---------- helpers ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function md(text) {
    // tiny markdown: fences, inline code, bold, headers, lists, [n] cites
    let t = esc(text);
    t = t.replace(/```(\w*)\n([\s\S]*?)```/g, (_, l, code) => `<pre><code>${code}</code></pre>`);
    t = t.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    t = t.replace(/^### (.*)$/gm, "<h3>$1</h3>").replace(/^## (.*)$/gm, "<h2>$1</h2>").replace(/^# (.*)$/gm, "<h1>$1</h1>");
    t = t.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
    t = t.replace(/^\s*[-*] (.*)$/gm, "<li>$1</li>").replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, "<ul>$1</ul>");
    t = t.replace(/^\s*\d+\. (.*)$/gm, "<li>$1</li>");
    t = t.replace(/\[(\d{1,2})\]/g, '<span class="cite-ref" data-n="$1">[$1]</span>');
    t = t.split(/\n{2,}/).map(p => /^<(h\d|ul|pre|li)/.test(p.trim()) ? p : `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
    return t;
  }

  function el(html) {
    const d = document.createElement("div");
    d.innerHTML = html.trim();
    return d.firstElementChild;
  }

  const scrollDown = () => { thread.scrollTop = thread.scrollHeight; };
  const setStatus = (s) => { statusLine.innerHTML = `${esc(s)}<span class="caret">▌</span>`; };

  // ---------- stats / health ----------
  async function refreshStats() {
    try {
      const st = await (await fetch("/api/stats")).json();
      $("#kb-total").textContent = st.total ?? 0;
      Object.entries(st.by_source || {}).forEach(([k, v]) => {
        const n = $(`#count-${CSS.escape(k)}`);
        if (n) n.textContent = v;
      });
    } catch { /* server booting */ }
  }
  async function health() {
    try {
      const h = await (await fetch("/api/health")).json();
      $("#health-dot").classList.add(h.ok ? "ok" : "bad");
      $("#health-dot").title = `llm key ${h.llm_key ? "set" : "MISSING"} · qdrant ${h.qdrant}`;
      setStatus(h.llm_key ? "online" : "online · LLM KEY MISSING");
    } catch {
      $("#health-dot").classList.add("bad");
      setStatus("server unreachable");
    }
  }

  // ---------- chat ----------
  function selectedSources() {
    return $$(".src-filter").filter(c => c.checked).map(c => c.value);
  }

  function addUserMsg(q) {
    thread.appendChild(el(`<div class="msg msg-user"><div class="bubble">${esc(q)}</div></div>`));
    scrollDown();
  }

  function addBotShell() {
    const node = el(`
      <div class="msg msg-bot">
        <div class="msg-head"><span>qabuddy</span><span class="mode-badge hidden"></span><span class="head-time"></span></div>
        <div class="bubble thinking">retrieving from knowledge base…</div>
        <div class="cites hidden"><div class="cites-head">sources</div></div>
      </div>`);
    thread.appendChild(node);
    scrollDown();
    return node;
  }

  function renderCitations(node, items) {
    const box = $(".cites", node);
    items.forEach((c, i) => {
      const card = el(`
        <div class="cite" data-st="${esc(c.source_type)}" data-n="${c.n}" style="animation-delay:${i * 60}ms">
          <div class="cite-top">
            <span class="cite-n">[${c.n}]</span>
            <span class="kb-swatch st-${esc(c.source_type)}"></span>
            <span class="cite-label">${esc(c.label)}</span>
            <span class="cite-path">${esc(c.ref)}</span>
            <span class="cite-score">${(c.rerank ?? 0).toFixed(2)}</span>
          </div>
          <div class="cite-snippet">${esc(c.snippet || "")}</div>
        </div>`);
      card.addEventListener("click", () => card.classList.toggle("open"));
      box.appendChild(card);
    });
    if (items.length) box.classList.remove("hidden");
  }

  async function send(qText) {
    const q = (qText ?? input.value).trim();
    if (!q || busy) return;
    busy = true;
    sendBtn.disabled = true;
    input.value = "";
    autoGrow();
    $(".hello")?.remove();
    addUserMsg(q);
    const node = addBotShell();
    const bubble = $(".bubble", node);
    let answer = "";
    setStatus("retrieving");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          sources: selectedSources(),
          mode: $("#mode").value || null,
          history: history.slice(-6),
        }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.error || `HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          if (!frame.startsWith("data:")) continue;
          const ev = JSON.parse(frame.slice(5));
          handle(ev);
        }
      }

      function handle(ev) {
        if (ev.type === "meta") {
          const b = $(".mode-badge", node);
          b.textContent = ev.mode;
          b.classList.remove("hidden");
          setStatus(`mode ${ev.mode} · searching`);
        } else if (ev.type === "citations") {
          renderCitations(node, ev.items || []);
          setStatus("generating");
        } else if (ev.type === "token") {
          if (!answer) bubble.classList.remove("thinking");
          answer += ev.text;
          bubble.innerHTML = `<div class="answer">${md(answer)}</div>`;
          scrollDown();
        } else if (ev.type === "done") {
          bubble.innerHTML = `<div class="answer${ev.no_answer ? " no-answer" : ""}">${md(ev.answer)}</div>
            <div class="answer-foot">${ev.no_answer ? "below confidence threshold · " : ""}${ev.elapsed}s</div>`;
          $(".head-time", node).textContent = `${ev.elapsed}s`;
          wireCiteRefs(node);
          history.push({ role: "user", content: q }, { role: "assistant", content: ev.answer.slice(0, 800) });
          setStatus("online");
        } else if (ev.type === "error") {
          bubble.classList.remove("thinking");
          bubble.innerHTML = `<div class="err">✖ ${esc(ev.message)}</div>`;
          setStatus("error");
        }
      }
    } catch (e) {
      bubble.classList.remove("thinking");
      bubble.innerHTML = `<div class="err">✖ ${esc(e.message)}</div>`;
      setStatus("error");
    } finally {
      busy = false;
      sendBtn.disabled = false;
      scrollDown();
      input.focus();
    }
  }

  function wireCiteRefs(node) {
    $$(".cite-ref", node).forEach(ref => {
      ref.addEventListener("click", () => {
        const card = $(`.cite[data-n="${ref.dataset.n}"]`, node);
        if (!card) return;
        card.classList.add("open", "flash");
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => card.classList.remove("flash"), 1200);
      });
    });
  }

  // ---------- ingest ----------
  $("#ingest-toggle").addEventListener("click", () => {
    const p = $("#ingest-panel");
    p.classList.toggle("hidden");
    $("#ingest-toggle").textContent = p.classList.contains("hidden") ? "open" : "close";
  });

  $("#ingest-run").addEventListener("click", () => {
    const src = $("#ingest-source").value;
    const force = $("#ingest-force").checked ? "&force=1" : "";
    const log = $("#ingest-log");
    const bar = $("#ingest-bar");
    $("#ingest-progress").classList.remove("hidden");
    $("#ingest-run").disabled = true;
    log.textContent = "";
    bar.style.width = "0%";
    const es = new EventSource(`/api/ingest?source=${src}${force}`);
    const line = (s) => { log.textContent += s + "\n"; log.scrollTop = log.scrollHeight; };
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data);
      if (ev.stage === "load" && ev.status === "done") line(`[${ev.source}] ${ev.docs} chunks / ${ev.files} files`);
      else if (ev.stage === "diff") line(`[${ev.source}] changed=${ev.changed} unchanged=${ev.unchanged} removed=${ev.removed}`);
      else if (ev.stage === "embed") {
        bar.style.width = `${Math.round(100 * ev.done / Math.max(ev.total, 1))}%`;
        setStatus(`ingest ${ev.done}/${ev.total}`);
      } else if (ev.stage === "done") { line(`[${ev.source}] ✔ ${ev.chunks ?? 0} chunks (${ev.embedded ?? 0} embedded)`); bar.style.width = "100%"; }
      else if (ev.stage === "error") line(`✖ ${ev.message}`);
      else if (ev.stage === "skipped") line(`[${ev.source}] skipped (${ev.reason})`);
    };
    es.onerror = () => {
      es.close();
      $("#ingest-run").disabled = false;
      setStatus("online");
      refreshStats();
      line("stream closed");
    };
  });

  // ---------- composer ----------
  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }
  input.addEventListener("input", autoGrow);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener("click", () => send());
  $$(".sug").forEach(b => b.addEventListener("click", () => send(b.textContent)));
  $("#btn-all").addEventListener("click", () => $$(".src-filter").forEach(c => c.checked = true));
  $("#btn-none").addEventListener("click", () => $$(".src-filter").forEach(c => c.checked = false));

  // ---------- boot ----------
  health();
  refreshStats();
  setInterval(refreshStats, 30000);
})();
