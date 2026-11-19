import { useEffect, useState } from "react";
import { api } from "../api.js";
import ResultView from "./ResultView.jsx";

const EXAMPLES = [
  "What was the revenue in 2025?",
  "Show revenue by customer country, from highest to lowest.",
  "Give me the monthly revenue for 2025.",
  "Which product appears most often in returned orders?",
  "What was our revenue in 2023?",
];

const MODE_LABELS = {
  tables_only: "Tables only",
  schema: "Schema",
  schema_docs: "Schema + dbt docs",
  schema_docs_examples: "Schema + docs + examples",
};

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("schema_docs");
  const [agent, setAgent] = useState("langgraph");
  const [modes, setModes] = useState(Object.keys(MODE_LABELS));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.config().then((c) => setModes(c.context_modes)).catch(() => {});
  }, []);

  async function submit(q = question) {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.ask({ question: q, context_mode: mode, agent });
      setHistory((h) => [{ ...res, agent }, ...h]);
      setQuestion("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ask">
      <section className="card composer">
        <div className="controls">
          <label>
            Agent
            <div className="segmented">
              {["langgraph", "baseline"].map((a) => (
                <button key={a} className={agent === a ? "active" : ""} onClick={() => setAgent(a)}>
                  {a === "langgraph" ? "LangGraph pipeline" : "LangChain baseline"}
                </button>
              ))}
            </div>
          </label>
          <label className={agent === "baseline" ? "disabled" : ""}>
            Context given to the LLM
            <select value={mode} onChange={(e) => setMode(e.target.value)} disabled={agent === "baseline"}>
              {modes.map((m) => <option key={m} value={m}>{MODE_LABELS[m] ?? m}</option>)}
            </select>
          </label>
        </div>
        <form className="input-row" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a business question… e.g. What is our average order value?"
          />
          <button type="submit" disabled={loading}>{loading ? "Thinking…" : "Ask"}</button>
        </form>
        <div className="chips">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" onClick={() => submit(ex)} disabled={loading}>{ex}</button>
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {history.map((h, i) => <AnswerCard key={history.length - i} item={h} />)}
    </div>
  );
}

function AnswerCard({ item }) {
  const [showTrace, setShowTrace] = useState(false);
  return (
    <section className="card answer-card">
      <div className="answer-head">
        <h3>{item.question}</h3>
        <div className="badges">
          <span className="badge">{item.agent === "baseline" ? "LangChain baseline" : MODE_LABELS[item.context_mode]}</span>
          {item.attempts > 1 && <span className="badge warn">{item.attempts} attempts</span>}
        </div>
      </div>
      <p className="answer">{item.answer}</p>
      {item.sql && (
        <details>
          <summary>Generated SQL</summary>
          <pre className="sql">{item.sql}</pre>
        </details>
      )}
      <ResultView result={item.result} />
      {item.trace?.length > 0 && (
        <>
          <button className="link" onClick={() => setShowTrace((s) => !s)}>
            {showTrace ? "Hide" : "Show"} agent trace ({item.trace.length} steps)
          </button>
          {showTrace && (
            <ol className="trace">
              {item.trace.map((t, i) => (
                <li key={i} className={t.ok === false ? "ko" : ""}>
                  <span className="node">{t.node}</span>
                  {t.ms != null && <span className="muted"> · {t.ms} ms</span>}
                  {t.error && <div className="trace-error">{t.error}</div>}
                  {t.is_fix && <div className="muted">self-correction attempt</div>}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}
