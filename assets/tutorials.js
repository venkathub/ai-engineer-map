// Deliberately small Markdown subset: paragraphs, headings, lists, links and code.
// Raw HTML is always escaped; no dependency or HTML injection is needed.
const escape = (value) => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

export async function tutorialCatalog() {
  const response = await fetch("content/tutorials.json");
  if (!response.ok) throw new Error("Tutorial catalog unavailable");
  const catalog = await response.json();
  if (catalog.schemaVersion !== 1 || !Array.isArray(catalog.path) || !catalog.lessons ||
      !catalog.path.every(id => typeof id === "string" && Object.hasOwn(catalog.lessons, id))) throw new Error("Invalid tutorial catalog");
  for (const entry of Object.values(catalog.lessons)) {
    if (!/^content\/rag\/[a-z0-9-]+\.md$/.test(entry.path) ||
        !/^labs\/[a-z0-9_/-]+\.py$/.test(entry.starter) || entry.starter.includes("..") ||
        !/^\d{4}-\d{2}-\d{2}$/.test(entry.reviewedAt)) throw new Error("Invalid tutorial entry");
  }
  return catalog;
}

export function renderTutorial(markdown, sourceUrl) {
  const inline = (text) => {
    let html = "", cursor = 0;
    for (const match of text.matchAll(/`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\)/g)) {
      html += escape(text.slice(cursor, match.index));
      if (match[1]) html += `<code>${escape(match[1])}</code>`;
      else {
        const url = new URL(match[3], sourceUrl);
        const base = new URL(sourceUrl);
        const allowed = url.protocol === "https:" || (url.origin === base.origin && ["http:", "https:"].includes(url.protocol));
        html += allowed ? `<a href="${escape(url.href)}" rel="noreferrer">${escape(match[2])}</a>` : escape(match[2]);
      }
      cursor = match.index + match[0].length;
    }
    return html + escape(text.slice(cursor));
  };
  const html = [], headings = [];
  let paragraph = [], list = [], code = [], fence = null, section = false;
  const flush = () => {
    if (paragraph.length) { html.push(`<p>${inline(paragraph.join(" "))}</p>`); paragraph = []; }
    if (list.length) { html.push(`<ul>${list.map(line => `<li>${inline(line)}</li>`).join("")}</ul>`); list = []; }
  };
  for (const line of markdown.split(/\r?\n/)) {
    const marker = line.match(/^(~~~|```)/)?.[1];
    if (fence) {
      if (marker === fence) { html.push(`<pre><code>${escape(code.join("\n"))}</code></pre>`); code = []; fence = null; }
      else code.push(line);
      continue;
    }
    if (marker) { flush(); fence = marker; continue; }
    if (line.startsWith("# ")) continue;
    if (line.startsWith("## ")) {
      flush();
      if (section) html.push("</section>");
      const heading = {id:`tutorial-section-${headings.length + 1}`, title:line.slice(3)};
      headings.push(heading);
      html.push(`<section id="${heading.id}"><h2>${escape(heading.title)}</h2>`); section = true;
    } else if (line.startsWith("### ")) { flush(); html.push(`<h3>${inline(line.slice(4))}</h3>`); }
    else if (line.startsWith("- ")) { if (paragraph.length) flush(); list.push(line.slice(2)); }
    else if (!line.trim()) flush();
    else { if (list.length) flush(); paragraph.push(line); }
  }
  if (fence) throw new Error("Unclosed code block");
  flush();
  if (section) html.push("</section>");
  if (!headings.length) throw new Error("Tutorial has no sections");
  return {html:html.join(""), headings};
}
