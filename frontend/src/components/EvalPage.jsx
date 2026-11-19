import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";

const pct = (v) => (v == null ? "–" : `${Math.round(v * 100)}%`);
const CONFIG_LABELS = {
  tables_only: "Tables only",
  schema: "Schema",
  schema_docs: "Schema + docs",
  schema_docs_examples: "Docs + examples",
  baseline: "LangChain baseline",
};
const label = (c) => CONFIG_LABELS[c] ?? c;

export default function EvalPage() {
  const [runs, setRuns] = useState([]);
  const [runId, setRunId] = useState(null);
  const [run, setRun] = useState(null);
  const [onlyFailures, setOnlyFailures] = useState(true);
  const [config, setConfig] = useState("all");
  const [error, setError] = useState(null);

  useEffect(() => {
    api.runs().then((r) => { setRuns(r); setRunId(r[0] ?? null); }).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (runId) api.run(runId).then(setRun).catch((e) => setError(e.message));
  }, [runId]);

  const configs = run ? Object.keys(run.summary) : [];
  const chartData = configs.map((c) => ({
    name: label(c),
    "Execution accuracy": Math.round(run.summary[c].execution_accuracy * 100),
    "Answer accuracy (judge)": run.summary[c].answer_accuracy == null ? null : Math.round(run.summary[c].answer_accuracy * 100),
  }));
  const tags = useMemo(() => {
    if (!run) return [];
    return [...new Set(configs.flatMap((c) => Object.keys(run.summary[c].accuracy_by_tag)))].sort();
  }, [run]);
  const errorCats = useMemo(() => {
    if (!run) return [];
    return [...new Set(configs.flatMap((c) => Object.keys(run.summary[c].errors)))].sort();
  }, [run]);

  if (error) return <p className="error">{error}</p>;
  if (!runs.length) {
    return (
      <section className="card empty">
        <h3>No evaluation run yet</h3>
        <p>Run <code>python -m eval.run_eval</code> from the repo root, then refresh.</p>
      </section>
    );
  }
  if (!run) return <p className="muted">Loading…</p>;

  const items = run.items.filter(
    (it) => (config === "all" || it.config === config) && (!onlyFailures || !it.exec_match)
  );

  return (
    <div className="eval">
      <section className="card">
        <div className="eval-head">
          <div>
            <h2>Evaluation · 30 questions</h2>
            <p className="muted">Agent: {run.agent_model} · Judge: {run.judge_model ?? "disabled"} · {run.created_at}</p>
          </div>
          <select value={runId} onChange={(e) => setRunId(e.target.value)}>
            {runs.map((r) => <option key={r}>{r}</option>)}
          </select>
        </div>
        <div className="kpis">
          {configs.map((c) => (
            <div key={c} className="kpi">
              <span className="kpi-label">{label(c)}</span>
              <span className="kpi-value">{pct(run.summary[c].execution_accuracy)}</span>
              <span className="muted">grounded {pct(run.summary[c].grounded_rate)}
                {run.summary[c].avg_attempts != null && ` · ${run.summary[c].avg_attempts} tries`}</span>
            </div>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => `${v}%`} />
            <Legend />
            <Bar dataKey="Execution accuracy" fill="var(--accent)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Answer accuracy (judge)" fill="var(--accent-2)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <div className="grid-2">
        <section className="card">
          <h3>Accuracy by difficulty tag</h3>
          <div className="table-wrap">
            <table className="heat">
              <thead><tr><th>tag</th>{configs.map((c) => <th key={c}>{label(c)}</th>)}</tr></thead>
              <tbody>
                {tags.map((t) => (
                  <tr key={t}>
                    <td>{t}</td>
                    {configs.map((c) => {
                      const v = run.summary[c].accuracy_by_tag[t];
                      return <td key={c} className="num" style={{ background: heat(v) }}>{pct(v)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="card">
          <h3>Failure root causes (judge)</h3>
          {errorCats.length === 0 ? <p className="muted">No failures classified (judge disabled or 100% accuracy).</p> : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>category</th>{configs.map((c) => <th key={c}>{label(c)}</th>)}</tr></thead>
                <tbody>
                  {errorCats.map((e) => (
                    <tr key={e}><td>{e}</td>{configs.map((c) => <td key={c} className="num">{run.summary[c].errors[e] ?? 0}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <section className="card">
        <div className="eval-head">
          <h3>Per-question results</h3>
          <div className="controls inline">
            <select value={config} onChange={(e) => setConfig(e.target.value)}>
              <option value="all">All configs</option>
              {configs.map((c) => <option key={c} value={c}>{label(c)}</option>)}
            </select>
            <label className="check">
              <input type="checkbox" checked={onlyFailures} onChange={(e) => setOnlyFailures(e.target.checked)} /> failures only
            </label>
          </div>
        </div>
        {items.map((it) => (
          <details key={`${it.config}-${it.id}`} className={`qrow ${it.exec_match ? "ok" : "ko"}`}>
            <summary>
              <span className="status">{it.exec_match ? "✓" : "✗"}</span>
              <span className="qid">{it.id}</span>
              <span className="qtext">{it.question}</span>
              <span className="badge">{label(it.config)}</span>
              {it.error_category && it.error_category !== "none" && <span className="badge warn">{it.error_category}</span>}
            </summary>
            <div className="qdetail">
              <div><h4>Gold SQL</h4><pre className="sql">{it.gold_sql}</pre></div>
              <div><h4>Agent SQL</h4><pre className="sql">{it.pred_sql ?? "(none)"}</pre></div>
              <p><b>Answer:</b> {it.answer}</p>
              {it.ungrounded_numbers?.length > 0 && <p className="error">Ungrounded numbers: {it.ungrounded_numbers.join(", ")}</p>}
              {it.judge_explanation && <p className="muted"><b>Judge:</b> {it.judge_explanation}</p>}
            </div>
          </details>
        ))}
      </section>
    </div>
  );
}

function heat(v) {
  if (v == null) return "transparent";
  // red (0) -> green (1), low alpha so text stays readable in both themes
  const hue = Math.round(v * 120);
  return `hsla(${hue}, 70%, 45%, 0.22)`;
}
