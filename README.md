# SmartStock AI

SmartStock AI is a demand-forecasting and inventory-planning demo. It combines a
LightGBM forecast service, safety-stock calculations, a PuLP allocation optimizer,
and a Next.js dashboard.

**Live dashboard:** [smartstock-nryo77q9e-jaykrai111-8746s-projects.vercel.app](https://smartstock-nryo77q9e-jaykrai111-8746s-projects.vercel.app/)

The repository includes a small **synthetic M5-format dataset** and generated
model artifacts so the demo can run without downloading proprietary or external
datasets. The operational inputs (lead times, costs, supply, capacity, and
current inventory) are simulated. The included results must not be presented as
benchmarks on the real M5 dataset.

## Repository layout

```text
backend/    FastAPI service, Dockerfile, and inference model artifacts
frontend/   Next.js dashboard
training/   Data preparation, training, evaluation, simulation, and notebooks
tests/      Backend and model tests
sql/        DuckDB analysis
docs/       API reference
data/       Local data directories; raw and processed data are not committed
```

## Quick start

### Backend and training

```bash
pip install -r training/requirements.txt
make all
python backend/predict_cli.py FOODS_1_001 CA_1
make api
```

The API is available at `http://localhost:7860`; interactive documentation is
available at `http://localhost:7860/docs`.

`make all` generates synthetic data, trains the models, runs the simulation,
exports the inference artifacts, and runs the tests. To run only the tests:

```bash
python -m pytest -q
```

### Frontend

```bash
make frontend
```

The dashboard runs at `http://localhost:3000` and uses
`NEXT_PUBLIC_API_URL=http://localhost:7860` by default.

### Docker

Build and run the backend from the repository root:

```bash
docker build -t smartstock-api backend
docker run --rm -p 7860:7860 smartstock-api
```

Check the service from PowerShell with:

```powershell
curl.exe http://localhost:7860/health
```

## Using real M5 data

The training pipeline accepts the M5 Forecasting - Accuracy file format:
`calendar.csv`, `sales_train_validation.csv`, and `sell_prices.csv`. Place
those files under `data/raw/m5/`, then prepare and train the selected stores
and items:

```bash
python training/scripts/prepare_data.py --stores CA_1 CA_2 TX_1 --n-items 100
make train simulate export
```

Do not commit raw or processed datasets. Any performance numbers should be
generated from a documented run and reported with its dataset, split, and
configuration.

## API and deployment

The main API endpoints are documented in [docs/api.md](docs/api.md).

For a Render backend deployment:

1. Create a Render Web Service from this repository.
2. Set the service root directory to `backend`.
3. Use the Docker runtime and expose port `7860`.
4. Set `ALLOWED_ORIGINS` to the deployed frontend URL.

For a Vercel deployment:

1. Import this repository and set the root directory to `frontend`.
2. Set `NEXT_PUBLIC_API_URL` to the public backend URL.
3. Add the Vercel domain to the backend's allowed origins.

Never place secrets in `NEXT_PUBLIC_*` variables or commit them to the
repository.

## Limitations

This is a demonstration system. The checked-in model artifacts are generated
from synthetic data, and inventory operations are simulated. Validate model
quality, calibration, costs, service levels, and operational constraints on
your own data before using the system for decisions.
