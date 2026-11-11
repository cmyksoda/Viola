// Small markdown renderer: everything is escaped first, so model output can't inject HTML.

const escapeHtml = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const KEYWORDS = new Set((
  "if else elif for while do return function def class import from export default const let var new " +
  "try catch except finally raise throw with as in of is not and or async await yield lambda pass break " +
  "continue switch case match struct enum impl trait fn pub mod use mut static void int char float double " +
  "bool long unsigned signed typedef sizeof public private protected interface extends implements package " +
  "go func type map chan defer select local then end elseif true false null nil None True False self this " +
  "echo fi esac done then until"
).split(" "));

const HASH_COMMENT = new Set([
  "py", "python", "sh", "bash", "zsh", "shell", "yaml", "yml", "toml", "ruby",
  "rb", "r", "perl", "make", "makefile", "dockerfile", "conf", "ini", "nix",
]);
const DASH_COMMENT = new Set(["sql", "lua", "haskell", "hs"]);

function highlight(code, lang) {
  lang = (lang || "").toLowerCase();
  const comment = HASH_COMMENT.has(lang)
    ? "#[^\\n]*"
    : DASH_COMMENT.has(lang)
      ? "--[^\\n]*"
      : "\\/\\/[^\\n]*|\\/\\*[\\s\\S]*?\\*\\/";
  const re = new RegExp(
    `(${comment})|("(?:\\\\.|[^"\\\\\\n])*"|'(?:\\\\.|[^'\\\\\\n])*'|\`(?:\\\\.|[^\`\\\\])*\`)|(\\b\\d[\\d_.xXa-fA-F]*\\b)|([A-Za-z_][\\w]*)`,
    "g",
  );
  let out = "";
  let last = 0;
  for (const m of code.matchAll(re)) {
    out += escapeHtml(code.slice(last, m.index));
    const [text, com, str, num, word] = m;
    if (com) out += `<span class="tk-com">${escapeHtml(text)}</span>`;
    else if (str) out += `<span class="tk-str">${escapeHtml(text)}</span>`;
    else if (num) out += `<span class="tk-num">${escapeHtml(text)}</span>`;
    else if (word && KEYWORDS.has(word)) out += `<span class="tk-kw">${text}</span>`;
    else if (word && code[m.index + text.length] === "(") out += `<span class="tk-fn">${text}</span>`;
    else out += escapeHtml(text);
    last = m.index + text.length;
  }
  return out + escapeHtml(code.slice(last));
}

function safeUrl(url) {
  return /^(https?:|mailto:)/i.test(url) ? url : null;
}

// Link labels reuse the outer stash, so code inside a label isn't lost, and skip autolinks to avoid nested <a>.
function inline(text, stash = [], autolink = true) {
  const keep = (html) => `\u0000${stash.push(html) - 1}\u0000`;
  text = text.replace(/(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/g, (_, __, code) =>
    keep(`<code>${escapeHtml(code.trim())}</code>`),
  );
  // The label stays on one line, or a reply full of unmatched "[" makes every render scan to the end of the text.
  text = text.replace(/\[([^\]\n]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, (all, label, url) => {
    const ok = safeUrl(url);
    if (!ok) return all;
    return keep(`<a href="${escapeHtml(ok)}" target="_blank" rel="noreferrer">${inline(label, stash, false)}</a>`);
  });
  if (autolink) {
    text = text.replace(/<?(https?:\/\/[^\s<>)]+[^\s<>).,;:!?'"])>?/g, (_, url) =>
      keep(`<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(url)}</a>`),
    );
  }
  text = escapeHtml(text);
  text = text
    .replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g, "<strong>$1</strong>")
    .replace(/__(?=\S)([\s\S]*?\S)__(?!\w)/g, "<strong>$1</strong>")
    .replace(/(^|[^*\w])\*(?=\S)([^*]*?\S)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/(^|[^\w])_(?=\S)([^_]*?\S)_(?!\w)/g, "$1<em>$2</em>")
    .replace(/~~(?=\S)([\s\S]*?\S)~~/g, "<del>$1</del>");
  return text.replace(/\u0000(\d+)\u0000/g, (_, i) => stash[i]);
}

const LIST_ITEM = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
const FENCE = /^\s*(```+|~~~+)\s*([\w+#.-]*)/;

const TABLE_DELIMITER = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

const isTableStart = (lines, i) =>
  lines[i].includes("|") && i + 1 < lines.length && TABLE_DELIMITER.test(lines[i + 1]);

// Rejoins parts split at "\|" by hand because regex lookbehind is a syntax error before Safari 16.4.
function splitRow(line) {
  const cells = [];
  for (const part of line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|")) {
    if (cells.length && cells[cells.length - 1].endsWith("\\")) cells[cells.length - 1] += `|${part}`;
    else cells.push(part);
  }
  return cells.map((c) => c.trim());
}

function codeBlock(code, lang) {
  const label = escapeHtml(lang || "text");
  return (
    `<div class="code-block"><div class="code-head"><span>${label}</span>` +
    `<button class="code-copy" type="button">Copy</button></div>` +
    `<pre><code>${highlight(code, lang)}</code></pre></div>`
  );
}

// Where an item's text starts; five or more spaces after the marker mean code, so the column stays at marker + 1.
function contentColumn(line, m) {
  const markerEnd = m[1].length + m[2].length;
  const gap = line.length - m[3].length - markerEnd;
  return markerEnd + (gap > 4 ? 1 : gap);
}

function renderList(lines) {
  const first = lines[0].match(LIST_ITEM);
  const base = first[1].length;
  const ordered = /\d/.test(first[2]);
  const start = ordered ? parseInt(first[2], 10) : 1;
  const items = [];
  let loose = false;
  let strip = 0;
  for (const line of lines) {
    const m = line.match(LIST_ITEM);
    if (m && m[1].length <= base) {
      items.push([m[3]]);
      strip = contentColumn(line, m);
    } else if (items.length) {
      if (!line.trim()) loose = true;
      items[items.length - 1].push(line.replace(new RegExp(`^\\s{0,${strip}}`), ""));
    }
  }
  const tag = ordered ? "ol" : "ul";
  const startAttr = ordered && start !== 1 ? ` start="${start}"` : "";
  const body = items
    .map((item) => {
      while (item.length > 1 && !item[item.length - 1].trim()) item.pop();
      const nested = item.slice(1).some((l) => l.trim());
      if (!nested && !loose) return `<li>${inline(item[0])}</li>`;
      if (!loose) return `<li>${inline(item[0])}${renderBlocks(item.slice(1))}</li>`;
      return `<li>${renderBlocks(item)}</li>`;
    })
    .join("");
  return `<${tag}${startAttr}>${body}</${tag}>`;
}

function renderBlocks(lines) {
  let html = "";
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    const fence = line.match(FENCE);
    if (fence) {
      const close = new RegExp(`^\\s*${fence[1][0] === "`" ? "`" : "~"}{${fence[1].length},}\\s*$`);
      const body = [];
      const unindent = new RegExp(`^\\s{0,${line.length - line.trimStart().length}}`);
      i++;
      while (i < lines.length && !close.test(lines[i])) body.push(lines[i++].replace(unindent, ""));
      i++;
      html += codeBlock(body.join("\n"), fence[2]);
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$/);
    if (heading) {
      const level = heading[1].length;
      html += `<h${level}>${inline(heading[2])}</h${level}>`;
      i++;
      continue;
    }
    if (/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)) {
      html += "<hr>";
      i++;
      continue;
    }
    if (/^\s*>/.test(line)) {
      const quote = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) quote.push(lines[i++].replace(/^\s*>\s?/, ""));
      html += `<blockquote>${renderBlocks(quote)}</blockquote>`;
      continue;
    }
    if (isTableStart(lines, i)) {
      const head = splitRow(line);
      const aligns = splitRow(lines[i + 1]).map((c) =>
        c.endsWith(":") ? (c.startsWith(":") ? "center" : "right") : "",
      );
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(splitRow(lines[i++]));
      const cell = (tag, text, col) =>
        `<${tag}${aligns[col] ? ` style="text-align:${aligns[col]}"` : ""}>${inline(text || "")}</${tag}>`;
      html +=
        `<div class="table-wrap"><table><thead><tr>${head.map((c, k) => cell("th", c, k)).join("")}</tr></thead>` +
        `<tbody>${rows
          .map((r) => `<tr>${head.map((_, k) => cell("td", r[k], k)).join("")}</tr>`)
          .join("")}</tbody></table></div>`;
      continue;
    }
    if (LIST_ITEM.test(line)) {
      const block = [line];
      const [, lead, marker] = line.match(LIST_ITEM);
      const indent = lead.length;
      const ordered = /\d/.test(marker);
      i++;
      while (i < lines.length) {
        const next = lines[i];
        if (!next.trim()) {
          const after = lines[i + 1];
          if (after !== undefined && (LIST_ITEM.test(after) || /^\s{2,}\S/.test(after))) {
            block.push(next);
            i++;
            continue;
          }
          break;
        }
        const m = next.match(LIST_ITEM);
        if (m && m[1].length < indent) break;
        if (m && m[1].length === indent && /\d/.test(m[2]) !== ordered) break;
        if (!m && !/^\s/.test(next) && FENCE.test(next)) break;
        block.push(next);
        i++;
      }
      html += renderList(block);
      continue;
    }
    const para = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !FENCE.test(lines[i]) &&
      !/^(#{1,6})\s/.test(lines[i]) &&
      !/^\s*>/.test(lines[i]) &&
      !(para.length && (LIST_ITEM.test(lines[i]) || isTableStart(lines, i)))
    ) {
      para.push(lines[i++].trim());
    }
    // A line no branch above could take must still be consumed, or this loop never ends.
    if (!para.length) para.push(lines[i++].trim());
    html += `<p>${inline(para.join("\n")).replace(/\n/g, "<br>")}</p>`;
  }
  return html;
}

export function renderMarkdown(text) {
  // NUL delimits inline placeholders, so literal NULs must not reach the parser (CommonMark maps them to U+FFFD).
  return renderBlocks(text.replace(/\r\n?/g, "\n").replace(/\u0000/g, "\uFFFD").split("\n"));
}

export { escapeHtml };
