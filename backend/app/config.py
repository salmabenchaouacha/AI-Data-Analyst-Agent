"""Central settings, read from environment variables (.env supported)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # LLM used by the agent ("provider:model", see langchain init_chat_model)
    agent_model: str = os.getenv("AGENT_MODEL", "openai:gpt-4o-mini")
    # LLM used as judge -> ideally a stronger / different model than the agent
    judge_model: str = os.getenv("JUDGE_MODEL", "openai:gpt-4o")
    duckdb_path: Path = Path(os.getenv("DUCKDB_PATH", ROOT / "data" / "warehouse.duckdb"))
    dbt_manifest: Path = Path(os.getenv("DBT_MANIFEST", ROOT / "dbt_project" / "target" / "manifest.json"))
    examples_path: Path = ROOT / "backend" / "app" / "agent" / "examples.yaml"
    # schema where dbt materialises the marts (dbt-duckdb default: "main")
    marts_schema: str = os.getenv("MARTS_SCHEMA", "main")
    max_retries: int = int(os.getenv("MAX_SQL_RETRIES", "2"))
    max_rows: int = int(os.getenv("MAX_RESULT_ROWS", "200"))


settings = Settings()

# Tables the agent is allowed to query (the dbt marts).
ALLOWED_TABLES = ("fct_orders", "fct_order_items", "dim_customers", "dim_products")

# Context modes compared in the ablation study.
CONTEXT_MODES = ("tables_only", "schema", "schema_docs", "schema_docs_examples")
