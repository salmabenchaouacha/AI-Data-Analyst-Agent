.PHONY: install data dbt check api front eval eval-quick

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

data:            ## regenerate seed CSVs (deterministic)
	python scripts/generate_seed_data.py

dbt:             ## seed + build + test + docs (manifest.json used as agent context)
	cd dbt_project && dbt build --profiles-dir . && dbt docs generate --profiles-dir .

check:           ## run every gold SQL on the warehouse
	python scripts/validate_gold_sql.py

api:
	cd backend && uvicorn app.main:app --reload --port 8000

front:
	cd frontend && npm run dev

eval:
	python -m eval.run_eval

eval-quick:
	python -m eval.run_eval --modes schema_docs --no-baseline --limit 5 --no-judge
