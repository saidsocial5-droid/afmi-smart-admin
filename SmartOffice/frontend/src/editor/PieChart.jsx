import React from 'react';

const PALETTE = ['#1B4332', '#D4A373', '#2D6A4F', '#BC6C25', '#52B788', '#7F5539', '#95D5B2', '#DDA15E', '#40916C', '#B08968'];

/** Camembert SVG avec légende (valeurs et parts). */
export default function PieChart({ title, slices, colors }) {
  const total = (slices || []).reduce((s, x) => s + x.value, 0);
  if (!total) return <div className="block-empty">{title} : aucune donnée.</div>;
  const palette = colors?.primary ? [colors.primary, colors.secondary || '#D4A373', ...PALETTE.slice(2)] : PALETTE;
  let angle = -Math.PI / 2;
  const r = 70, cx = 80, cy = 80;
  const arcs = slices.map((s, i) => {
    const a = (s.value / total) * Math.PI * 2;
    const x1 = cx + r * Math.cos(angle), y1 = cy + r * Math.sin(angle);
    angle += a;
    const x2 = cx + r * Math.cos(angle), y2 = cy + r * Math.sin(angle);
    const d = slices.length === 1 ? `M ${cx - r} ${cy} a ${r} ${r} 0 1 0 ${2 * r} 0 a ${r} ${r} 0 1 0 ${-2 * r} 0`
      : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${a > Math.PI ? 1 : 0} 1 ${x2} ${y2} Z`;
    return <path key={i} d={d} fill={palette[i % palette.length]} stroke="#fff" strokeWidth="1" />;
  });
  const fmt = (v) => v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (
    <figure className="pie-figure">
      <figcaption className="chart-title">{title}</figcaption>
      <div className="pie-row">
        <svg viewBox="0 0 160 160" className="pie-svg" role="img" aria-label={title}>{arcs}</svg>
        <table className="pie-legend"><tbody>
          {slices.map((s, i) => (
            <tr key={i}><td><span className="pie-swatch" style={{ background: palette[i % palette.length] }} /></td>
              <td>{s.label}</td><td className="num">{fmt(s.value)} MAD</td><td className="num">{((100 * s.value) / total).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %</td></tr>
          ))}
        </tbody></table>
      </div>
    </figure>
  );
}
