import React from 'react';
import BarChart from './BarChart';
import PieChart from './PieChart';

const money = (v) => (v === null || v === undefined ? '' : (v / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const number = (v) => (v === null || v === undefined ? '' : Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 }));
const percent = (v) => (v === null || v === undefined ? '—' : `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`);

function cell(value, format) {
  if (typeof value === 'string' || value === null || value === undefined) return value ?? '';
  if (format === 'money') return money(value);
  if (format === 'percent') return percent(value);
  return number(value);
}

/** Libellé : « **gras** » pour les sous-totaux, indentation conservée pour le détail. */
function label(text) {
  if (typeof text !== 'string') return text;
  const indent = text.match(/^\s*/)[0].length;
  const clean = text.trim();
  const bold = clean.startsWith('**') && clean.endsWith('**');
  const body = bold ? clean.slice(2, -2) : clean;
  return <span style={{ paddingInlineStart: `${indent * 2}mm`, fontWeight: bold ? 700 : undefined }}>{body}</span>;
}

/** Tableau générique des rapports annuels (formats : text, money, number, percent), graphiques éventuels. */
export default function GenericTable({ data, style }) {
  const thStyle = { background: style?.table?.header_bg, color: style?.table?.header_color };
  if (data.pies) {
    return (
      <div className="pies">
        {data.pies.map((p, i) => <PieChart key={i} title={p.title} slices={p.slices} colors={style?.colors} />)}
      </div>
    );
  }
  const formats = data.formats || [];
  return (
    <div>
      {data.rows.length === 0 ? <div className="block-empty">Aucune donnée.</div> : (
        <table className="data-table">
          <thead><tr style={thStyle}>{data.columns.map((c, i) => <th key={i} className={formats[i] && formats[i] !== 'text' ? 'num' : ''}>{c}</th>)}</tr></thead>
          <tbody>
            {data.rows.map((r, i) => (
              <tr key={i} className={typeof r[0] === 'string' && r[0].trim().startsWith('**') ? 'subtotal' : ''}>
                {r.map((v, j) => <td key={j} className={formats[j] && formats[j] !== 'text' ? 'num' : ''}>{j === 0 ? label(v) : cell(v, formats[j])}</td>)}
              </tr>
            ))}
            {data.total && (
              <tr className="total">{data.total.map((v, j) => <td key={j} className={formats[j] && formats[j] !== 'text' ? 'num' : ''}>{j === 0 ? v : cell(v, formats[j])}</td>)}</tr>
            )}
          </tbody>
        </table>
      )}
      {data.chart?.type === 'bars' && (
        <div className="mt-2">
          <BarChart series={data.chart.series} colors={style?.colors} unit="MAD" legend={data.chart.legend} />
        </div>
      )}
      {(data.notes || []).map((n, i) => <div key={i} className="table-note">{n}</div>)}
    </div>
  );
}
