import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const fmt = (v) => (isNum(v) ? v.toLocaleString("en-US", { maximumFractionDigits: 2 }) : v ?? "∅");

/** Pick a chart automatically: one label column + one numeric column, 2+ rows. */
function chartSpec(result) {
  if (!result || result.rows.length < 2) return null;
  const { columns, rows } = result;
  const labelIdx = columns.findIndex((_, i) => rows.every((r) => !isNum(r[i])));
  const valueIdx = columns.findIndex((_, i) => i !== labelIdx && rows.every((r) => isNum(r[i]) || r[i] === null));
  if (labelIdx < 0 || valueIdx < 0) return null;
  const data = rows.map((r) => ({ label: String(r[labelIdx]), value: r[valueIdx] }));
  const isTime = data.every((d) => /^\d{4}(-\d{2})?(-\d{2})?$/.test(d.label));
  return { data, type: isTime ? "line" : "bar", valueName: columns[valueIdx] };
}

export default function ResultView({ result }) {
  if (!result) return null;
  const spec = chartSpec(result);
  return (
    <div className="result">
      {spec && (
        <div className="chart">
          <ResponsiveContainer width="100%" height={240}>
            {spec.type === "line" ? (
              <LineChart data={spec.data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={fmt} width={70} />
                <Tooltip formatter={(v) => [fmt(v), spec.valueName]} />
                <Line type="monotone" dataKey="value" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            ) : (
              <BarChart data={spec.data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={fmt} width={70} />
                <Tooltip formatter={(v) => [fmt(v), spec.valueName]} />
                <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {result.rows.map((r, i) => (
              <tr key={i}>
                {r.map((v, j) => <td key={j} className={isNum(v) ? "num" : ""}>{fmt(v)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        {result.truncated && <p className="muted">Result truncated.</p>}
      </div>
    </div>
  );
}
