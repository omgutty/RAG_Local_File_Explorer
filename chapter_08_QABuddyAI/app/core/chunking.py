"""Per-source chunkers.

Atomic sources (code units, CSV rows, tickets, failure blocks) get NO overlap;
prose gets ~15% overlap. Sizes are characters (~4 chars per token) and come
from config.yaml.
"""
import re

# ---- prose core (ported from ch07 rag_core.chunk_text) ---------------------


def chunk_text(text, size=2048, overlap=300):
    text = (text or "").strip()
    if len(text) <= size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind(". "), window.rfind("\n"))
            if cut > int(size * 0.6):
                end = start + cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


# ---- markdown / docs -------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def split_headings(text):
    """Split markdown-ish text into (heading_trail, body) sections."""
    lines = (text or "").splitlines()
    trail, sections, buf = [], [], []

    def flush(current_trail):
        body = "\n".join(buf).strip()
        if body:
            sections.append((current_trail, body))
        buf.clear()

    current = ""
    for ln in lines:
        m = HEADING_RE.match(ln)
        if m:
            flush(current)
            level, title = len(m.group(1)), m.group(2).strip()
            trail[:] = [t for t in trail if t[0] < level] + [(level, title)]
            current = " > ".join(t[1] for t in trail)
        else:
            buf.append(ln)
    flush(current)
    if not sections and (text or "").strip():
        sections = [("", text.strip())]
    return sections


def chunk_doc(text, size=2048, overlap=300):
    """Heading-aware doc chunks: [{'text', 'heading'}]."""
    out = []
    for heading, body in split_headings(text):
        prefix = f"[{heading}]\n" if heading else ""
        for piece in chunk_text(body, size, overlap):
            out.append({"text": prefix + piece, "heading": heading})
    return out


# ---- transcripts -----------------------------------------------------------

TURN_RE = re.compile(r"^\s*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?[A-Z][\w .\-]{0,40}:\s")


def split_transcript(text, size=3600, overlap=480):
    """Pack speaker turns into windows; never cut inside a turn."""
    lines = (text or "").splitlines()
    turns, buf = [], []
    for ln in lines:
        if TURN_RE.match(ln) and buf:
            turns.append("\n".join(buf))
            buf = [ln]
        else:
            buf.append(ln)
    if buf:
        turns.append("\n".join(buf))
    if len(turns) <= 1:
        return chunk_text(text, size, overlap)

    chunks, cur = [], ""
    for t in turns:
        if cur and len(cur) + len(t) + 1 > size:
            chunks.append(cur.strip())
            tail = cur[-overlap:]
            nl = tail.find("\n")
            cur = (tail[nl + 1:] + "\n" if nl != -1 else "") + t
        else:
            cur = f"{cur}\n{t}" if cur else t
    if cur.strip():
        chunks.append(cur.strip())
    return [c for c in chunks if c]


# ---- code (Java / TS / JS), brace-aware unit extraction --------------------

CODE_KEYWORDS = {"if", "for", "while", "switch", "catch", "else", "return",
                 "new", "try", "do", "throw", "super", "this"}

JAVA_SIG = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|abstract|synchronized|native|default|strictfp)\s+)*"
    r"(?:(?P<kind>class|interface|enum|record)\s+(?P<cname>[\w$]+)"
    r"|(?:[\w$<>\[\],.\s]+?\s+)?(?P<mname>[\w$]+)\s*\([^;{}]*\)\s*(?:throws\s+[\w,.\s]+)?)"
    r"\s*\{")

TS_SIGS = [
    ("class", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(?P<name>[\w$]+)")),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>[\w$]*)\s*\(")),
    ("arrow", re.compile(r"^\s*(?:export\s+)?const\s+(?P<name>[\w$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w$]+)\s*(?::[^=]+)?=>")),
    ("test", re.compile(r"^\s*(?P<name>test|it|describe)(?:\.\w+)?\s*\(\s*['\"`]")),
    ("method", re.compile(r"^\s*(?:(?:public|private|protected|static|readonly|override|async)\s+)*(?P<name>[\w$]+)\s*\([^;{}]*\)\s*(?::\s*[^{;=]+)?\s*\{")),
]

STRING_RE = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`")


def _clean_line(line):
    line = STRING_RE.sub('""', line)
    line = re.sub(r"/\*.*?\*/", "", line)
    line = re.sub(r"//.*$", "", line)
    return line


def _match_sig(line, lang):
    if lang == "java":
        m = JAVA_SIG.match(line)
        if m:
            name = m.group("cname") or m.group("mname")
            if name and name not in CODE_KEYWORDS:
                return name
        return None
    for _, rx in TS_SIGS:
        m = rx.match(line)
        if m:
            name = (m.groupdict().get("name") or "anonymous") or "anonymous"
            if name not in CODE_KEYWORDS:
                return name
    return None


def _extend_start(lines, start):
    """Pull leading annotations / decorators / doc comments into the unit."""
    s = start
    for _ in range(10):
        if s - 1 < 0:
            break
        prev = lines[s - 1].strip()
        if prev.startswith(("@", "/**", "*", "*/", "//")) and prev:
            s -= 1
        else:
            break
    return s


def _window_lines(lines, start, size, overlap_lines=4):
    """Line-window fallback splitter; returns (line_start, line_end, text) 0-indexed inclusive."""
    out, i = [], 0
    n = len(lines)
    while i < n:
        cur, j = 0, i
        while j < n and (cur + len(lines[j]) + 1 <= size or j == i):
            cur += len(lines[j]) + 1
            j += 1
        text = "\n".join(lines[i:j]).strip()
        if text:
            out.append((start + i, start + j - 1, text))
        if j >= n:
            break
        i = max(j - overlap_lines, i + 1)
    return out


def split_code(src, lang, max_chars=2000, min_chars=250, fallback_size=1600, fallback_overlap=200):
    """Return [{'text', 'name', 'line_start', 'line_end'}] with 1-indexed lines.

    Units are methods/classes/test blocks found via signature + brace matching.
    Oversized classes decompose into their methods; leftovers (imports, fields)
    become windowed chunks; tiny units merge forward.
    """
    lines = (src or "").splitlines()
    if not lines:
        return []

    units, open_units, depth = [], [], 0
    for idx, raw in enumerate(lines):
        cleaned = _clean_line(raw)
        opens, closes = cleaned.count("{"), cleaned.count("}")
        if depth <= 2 and opens > 0:
            name = _match_sig(raw, lang)
            if name:
                open_units.append([_extend_start(lines, idx), name, depth])
        depth += opens - closes
        for u in open_units[:]:
            if depth <= u[2]:
                units.append({"start": u[0], "end": idx, "name": u[1], "odepth": u[2]})
                open_units.remove(u)
    for u in open_units:  # unclosed (parse drift): close at EOF
        units.append({"start": u[0], "end": len(lines) - 1, "name": u[1], "odepth": u[2]})

    if not units:
        pieces = _window_lines(lines, 0, fallback_size, max(2, fallback_overlap // 60))
        return [{"text": t, "name": None, "line_start": s + 1, "line_end": e + 1} for s, e, t in pieces]

    def text_of(u):
        return "\n".join(lines[u["start"]:u["end"] + 1])

    # resolve nesting: keep small outer units whole, decompose big ones into children
    units.sort(key=lambda u: (u["start"], -(u["end"] - u["start"])))
    keep, covered = [], set()

    def children_of(u):
        return [c for c in units if c is not u and c["start"] >= u["start"] and c["end"] <= u["end"]
                and c["odepth"] > u["odepth"]]

    for u in units:
        if u["start"] in covered:
            continue
        kids = children_of(u)
        if len(text_of(u)) <= max_chars or not kids:
            keep.append(u)
            for k in kids:
                covered.add(k["start"])
            covered.add(u["start"])
        else:
            # emit the class skeleton (its lines minus child ranges) later via leftovers
            covered.add(u["start"])

    kept_ranges = sorted((u["start"], u["end"]) for u in keep)

    def in_kept(i):
        return any(s <= i <= e for s, e in kept_ranges)

    chunks = []
    for u in sorted(keep, key=lambda u: u["start"]):
        t = text_of(u)
        if len(t) > max_chars:
            for s, e, piece in _window_lines(lines[u["start"]:u["end"] + 1], u["start"], fallback_size):
                chunks.append({"text": piece, "name": u["name"], "line_start": s + 1, "line_end": e + 1})
        else:
            chunks.append({"text": t, "name": u["name"], "line_start": u["start"] + 1, "line_end": u["end"] + 1})

    # leftovers: imports, fields, class headers not covered by kept units
    i, n = 0, len(lines)
    while i < n:
        if in_kept(i):
            i += 1
            continue
        j = i
        while j < n and not in_kept(j):
            j += 1
        block = "\n".join(lines[i:j]).strip()
        if len(block) >= 40:
            for s, e, piece in _window_lines(lines[i:j], i, fallback_size):
                chunks.append({"text": piece, "name": None, "line_start": s + 1, "line_end": e + 1})
        i = j

    chunks.sort(key=lambda c: c["line_start"])

    # merge tiny chunks forward
    merged = []
    for c in chunks:
        if merged and len(merged[-1]["text"]) < min_chars and \
                len(merged[-1]["text"]) + len(c["text"]) <= max_chars:
            prev = merged[-1]
            prev["text"] += "\n" + c["text"]
            prev["line_end"] = c["line_end"]
            prev["name"] = prev["name"] or c["name"]
        else:
            merged.append(dict(c))
    return merged


# ---- logs ------------------------------------------------------------------

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
FAIL_TRIG = re.compile(r"(<<< FAILURE!|<<< ERROR!|Traceback \(most recent|^\[ERROR\]|\bFAILED\b|"
                       r"BUILD FAILURE|AssertionError|[A-Z]\w+(?:Exception|Error)[:\s])")
STACK_RE = re.compile(r"^\s+at\s+[\w$.<>/]+\(|^\s+File \"|^Caused by:|^\s+\.\.\. \d+ more")
EXC_RE = re.compile(r"\b([A-Z][\w$.]*(?:Exception|Error))\b")
TEST_RE = re.compile(r"\b([\w$.]*Tests?)\.([\w$]+)\b|\b([\w$.]*Tests?)\b")


def split_log_failures(text, max_block_chars=2400, context_lines=12):
    """Extract failure blocks + a build summary from a CI console log."""
    lines = [ANSI_RE.sub("", ln) for ln in (text or "").splitlines()]
    n = len(lines)
    triggers = [i for i, ln in enumerate(lines) if FAIL_TRIG.search(ln)]

    blocks = []
    for t in triggers:
        start = max(0, t - context_lines)
        end = t
        while end + 1 < n and (STACK_RE.match(lines[end + 1]) or FAIL_TRIG.search(lines[end + 1])):
            end += 1
        blocks.append([start, min(n - 1, end + 2)])

    merged = []
    for b in sorted(blocks):
        if merged and b[0] <= merged[-1][1] + 2:
            merged[-1][1] = max(merged[-1][1], b[1])
        else:
            merged.append(b)

    failures = []
    for s, e in merged:
        btext = "\n".join(lines[s:e + 1]).strip()
        if len(btext) > max_block_chars:
            btext = btext[:max_block_chars // 2] + "\n...[truncated]...\n" + btext[-max_block_chars // 2:]
        test_name = None
        m = TEST_RE.search(btext)
        if m:
            test_name = f"{m.group(1)}.{m.group(2)}" if m.group(1) and m.group(2) else (m.group(3) or m.group(1))
        exc = EXC_RE.search(btext)
        failures.append({"text": btext, "test_name": test_name,
                         "exception": exc.group(1) if exc else None,
                         "line_start": s + 1, "line_end": e + 1})

    head = "\n".join(lines[:15]).strip()
    tail = "\n".join(lines[-15:]).strip()
    summary = (head + "\n...\n" + tail) if n > 30 else "\n".join(lines).strip()
    return {"failures": failures, "summary": summary}
