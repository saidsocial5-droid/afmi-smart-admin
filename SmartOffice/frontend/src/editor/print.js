// Aperçu paginé et impression (PDF via « Imprimer » du navigateur ou de WebView2).
// En-têtes et pieds de page : boîtes de marge CSS @page (première page, pages paires/impaires, numéros de page).

const esc = (s) => String(s ?? '').replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, ' ');

export function deepMerge(base, over) {
  const out = { ...(base || {}) };
  Object.entries(over || {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === '') return;
    out[k] = v && typeof v === 'object' && !Array.isArray(v) && typeof out[k] === 'object' ? deepMerge(out[k], v) : v;
  });
  return out;
}

const logoUrl = (logo, origin) => {
  if (logo.funder_logo) return `${origin}/api/funders/${logo.funder_logo}/logo`;
  return `${origin}/api/files/${logo.file_id}/image`;
};

/** Variables CSS et règles communes à l'éditeur et à l'impression, tirées de la charte. */
export function chartCss(style, layout) {
  const c = style.colors || {}, f = style.fonts || {}, t = style.table || {};
  return `
    .doc-body { font-family: "${esc(f.body || 'Calibri')}", Calibri, Arial, sans-serif; font-size: ${f.size_pt || 11}pt; color: ${c.text || '#1F2937'}; }
    .doc-body h1, .doc-body h2, .doc-body h3 { font-family: "${esc(f.headings || f.body || 'Calibri')}", Calibri, Arial, sans-serif; color: ${c.primary || '#1B4332'}; }
    .doc-body table th, .doc-body .data-table thead tr { background: ${t.header_bg || '#1B4332'}; color: ${t.header_color || '#FFFFFF'}; }
    .doc-body table td, .doc-body table th { border: 1px solid ${t.border_color || '#CBD5E1'}; }
    .doc-body .data-table tbody tr:nth-child(even) { background: ${t.stripe || '#F8F9FA'}; }
    ${layout?.heading_numbering ? `
    .doc-body { counter-reset: h1; }
    .doc-body h1 { counter-reset: h2; } .doc-body h2 { counter-reset: h3; }
    .doc-body h1::before { counter-increment: h1; content: counter(h1) ". "; }
    .doc-body h2::before { counter-increment: h2; content: counter(h1) "." counter(h2) " "; }
    .doc-body h3::before { counter-increment: h3; content: counter(h1) "." counter(h2) "." counter(h3) " "; }` : ''}
  `;
}

const LOGO_BOXES = ['header-left', 'header-center', 'header-right', 'footer-left', 'footer-center', 'footer-right'];

function marginBoxes(layout, style, fields, origin, variant) {
  const h = layout.header || {}, ft = layout.footer || {};
  const boxes = {};
  const text = variant === 'first' ? (h.first_page_text ?? h.text) : variant === 'left' ? (h.even_text || h.text) : h.text;
  if (text) boxes['top-center'] = `content: "${esc(fill(text, fields))}"; font-size: 8.5pt; color: #6B7280;`;
  (layout.logos || []).forEach((logo) => {
    if (!LOGO_BOXES.includes(logo.position)) return;
    const box = logo.position.replace('header', 'top').replace('footer', 'bottom');
    boxes[box] = `content: ""; background: url("${logoUrl(logo, origin)}") no-repeat center / contain; height: ${logo.height_mm || 14}mm; width: 45mm;`;
  });
  const showNumbers = ft.page_numbers !== false && !(variant === 'first' && ft.first_page_different);
  const numberBox = variant === 'left' && ft.odd_even_different ? 'bottom-left' : 'bottom-right';
  // Une règle :first ou :left n'efface pas les boîtes de la règle générale : on les vide explicitement.
  boxes['bottom-right'] = 'content: none;';
  if (variant === 'left' || variant === 'first') boxes['bottom-left'] = boxes['bottom-left'] || 'content: none;';
  if (showNumbers) boxes[numberBox] = `content: "Page " counter(page) " / " counter(pages); font-size: 8.5pt; color: #6B7280;`;
  const footer = [ft.text, ...(style.mentions || [])].filter(Boolean).map((s) => fill(s, fields)).join(' — ');
  if (footer) boxes['bottom-center'] = `content: "${esc(footer)}"; font-size: 7.5pt; color: #6B7280;`;
  return Object.entries(boxes).map(([k, v]) => `@${k} { ${v} }`).join('\n');
}

const fill = (text, fields) => String(text).replace(/\{(\w+)\}/g, (m, k) => fields?.[k] ?? m);

/**
 * Document HTML autonome prêt à imprimer : contenu rendu de l'éditeur (blocs dynamiques compris, tels qu'affichés),
 * version finale (suppressions en révision masquées, ajouts acceptés), notes numérotées en fin de document.
 */
export function buildPrintHtml({ editorDom, title, style, layout, fields, language, origin }) {
  const eff = deepMerge(style, layout);
  const m = eff.margins_mm || {};
  const clone = editorDom.cloneNode(true);
  clone.querySelectorAll('.no-print, .ProseMirror-gapcursor, .ProseMirror-separator').forEach((n) => n.remove());
  clone.querySelectorAll('del.tc-del').forEach((n) => n.remove());
  clone.querySelectorAll('ins.tc-ins').forEach((n) => n.replaceWith(...n.childNodes));
  clone.querySelectorAll('[contenteditable]').forEach((n) => n.removeAttribute('contenteditable'));
  clone.querySelectorAll('span.comment').forEach((n) => n.replaceWith(...n.childNodes));
  clone.querySelectorAll('[data-field="page"], [data-field="pages"]').forEach((n) => n.remove());
  clone.querySelectorAll('img').forEach((img) => { if (img.getAttribute('src')?.startsWith('/')) img.setAttribute('src', origin + img.getAttribute('src')); });
  const notes = [];
  clone.querySelectorAll('sup.footnote-ref').forEach((sup) => {
    notes.push(sup.getAttribute('data-footnote'));
    sup.textContent = String(notes.length);
  });
  const notesHtml = notes.length
    ? `<section class="footnotes"><hr/><ol>${notes.map((n) => `<li>${n.replace(/</g, '&lt;')}</li>`).join('')}</ol></section>` : '';
  const dir = language === 'ar' ? 'rtl' : 'ltr';
  return `<!doctype html><html lang="${language || 'fr'}" dir="${dir}"><head><meta charset="utf-8"><title>${(title || 'Document').replace(/</g, '&lt;')}</title>
<style>
@page { size: A4; margin: ${m.top || 25}mm ${m.right || 20}mm ${m.bottom || 22}mm ${m.left || 20}mm; ${marginBoxes(eff, eff, fields, origin, 'right')} }
@page :left { ${marginBoxes(eff, eff, fields, origin, 'left')} }
@page :first { ${marginBoxes(eff, eff, fields, origin, 'first')} }
html, body { margin: 0; background: white; }
${chartCss(eff, eff)}
.doc-body { line-height: 1.45; }
.doc-body p { margin: 0 0 6pt; }
.doc-body h1 { font-size: 18pt; margin: 14pt 0 8pt; } .doc-body h2 { font-size: 14pt; margin: 12pt 0 6pt; } .doc-body h3 { font-size: 12pt; margin: 10pt 0 4pt; }
.doc-body h1, .doc-body h2, .doc-body h3 { break-after: avoid; }
.doc-body table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9.5pt; break-inside: auto; }
.doc-body td, .doc-body th { padding: 3pt 5pt; vertical-align: top; }
.doc-body tr { break-inside: avoid; }
.doc-body .num { text-align: end; white-space: nowrap; }
.doc-body .total { font-weight: bold; }
.doc-body .page-break { break-after: page; height: 0; border: 0; }
.doc-body .columns-2 { column-count: 2; column-gap: 8mm; } .doc-body .columns-3 { column-count: 3; column-gap: 6mm; }
.doc-body img { max-width: 100%; }
.doc-body .photo-grid { display: grid; gap: 4mm; counter-reset: none; }
.doc-body .photo-figure { margin: 0; break-inside: avoid; }
.doc-body .photo-figure img { width: 100%; height: 55mm; object-fit: cover; }
.doc-body .photo-figure figcaption { font-size: 8.5pt; color: #374151; margin-top: 1mm; }
.doc-body { counter-reset: photo; }
.doc-body .photo-num::before { counter-increment: photo; content: "Photo n° " counter(photo) " : "; font-weight: bold; }
.doc-body .photo-credit { color: #6B7280; }
.doc-body .toc-title { font-weight: bold; font-size: 13pt; margin-bottom: 4pt; }
.doc-body .toc-list { list-style: none; padding: 0; } .doc-body .toc-l2 { padding-inline-start: 6mm; } .doc-body .toc-l3 { padding-inline-start: 12mm; }
.doc-body .toc-num { margin-inline-end: 3mm; } .doc-body .toc-empty { display: none; }
.doc-body .field-chip { background: none; border: 0; padding: 0; }
.doc-body .bar-chart { width: 100%; max-height: 110mm; }
.doc-body .chart-title { font-weight: bold; font-size: 10pt; }
.doc-body .block-empty { color: #6B7280; font-style: italic; }
.footnotes { font-size: 8.5pt; margin-top: 10mm; }
</style></head><body><main class="doc-body">${clone.innerHTML}${notesHtml}</main></body></html>`;
}
