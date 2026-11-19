import { useState } from "react";
import AskPage from "./components/AskPage.jsx";
import EvalPage from "./components/EvalPage.jsx";

export default function App() {
  const [tab, setTab] = useState("ask");
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span>
          <div>
            <h1>AI Data Analyst Agent</h1>
            <p>Text-to-SQL over dbt models · LangGraph · evaluated</p>
          </div>
        </div>
        <nav className="tabs">
          <button className={tab === "ask" ? "active" : ""} onClick={() => setTab("ask")}>Ask</button>
          <button className={tab === "eval" ? "active" : ""} onClick={() => setTab("eval")}>Evaluation</button>
        </nav>
      </header>
      <main>{tab === "ask" ? <AskPage /> : <EvalPage />}</main>
    </div>
  );
}
