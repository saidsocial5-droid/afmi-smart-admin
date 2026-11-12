import React from 'react';

// Graphique en barres horizontales « prévu / réalisé » en SVG (aucune bibliothèque) : s'imprime et s'exporte tel quel.
export default function BarChart({ series, colors, unit = '', legend = ['Prévu', 'Réalisé'] }) {
  if (!series?.length) return <div className="block-empty">Aucune donnée à représenter.</div>;
  const max = Math.max(...series.flatMap((s) => [s.planned || 0, s.actual || 0]), 1);
  const rowH = 34, labelW = 210, width = 640, barW = width - labelW - 90;
  const height = series.length * rowH + 30;
  const primary = colors?.primary || '#1B4332', secondary = colors?.secondary || '#D4A373';
  const fmt = (v) => Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="bar-chart" role="img" aria-label="Graphique prévu et réalisé">
      {series.map((s, i) => {
        const y = 10 + i * rowH;
        const pw = ((s.planned || 0) / max) * barW, aw = ((s.actual || 0) / max) * barW;
        return (
          <g key={i}>
            <text x={labelW - 8} y={y + 16} textAnchor="end" fontSize="11" fill="#374151">{s.label.length > 32 ? s.label.slice(0, 31) + '…' : s.label}</text>
            <rect x={labelW} y={y + 2} width={pw} height="11" fill={secondary} opacity="0.55" />
            <rect x={labelW} y={y + 15} width={aw} height="11" fill={primary} />
            <text x={labelW + Math.max(pw, aw) + 6} y={y + 18} fontSize="10" fill="#374151">{fmt(s.actual)} / {fmt(s.planned)} {unit}</text>
          </g>
        );
      })}
      <g transform={`translate(${labelW}, ${height - 12})`} fontSize="10" fill="#374151">
        <rect width="10" height="8" fill={secondary} opacity="0.55" /><text x="14" y="8">{legend[0]}</text>
        <rect x="70" width="10" height="8" fill={primary} /><text x="84" y="8">{legend[1]}</text>
      </g>
    </svg>
  );
}
