.PHONY: data train simulate export all test api frontend sql
data:      ## synthetic M5-format data (skip if you downloaded real M5 into data/raw/m5) + prepare
	python training/scripts/make_synthetic_m5.py && python training/scripts/prepare_data.py
train:     ## baselines + LightGBM + quantiles + MLflow
	python training/scripts/train.py --mlflow
simulate:
	python training/scripts/simulate_business.py
export:    ## copy artifacts into backend/ and verify parity
	python training/scripts/export_artifacts.py
all: data train simulate export test
test:
	python -m pytest -q
api:
	cd backend && uvicorn app.main:app --reload --port 7860
frontend:
	cd frontend && npm install && NEXT_PUBLIC_API_URL=http://localhost:7860 npm run dev
sql:
	python sql/run_sql.py
