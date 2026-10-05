"""One command: SKU + store in -> 28-day forecast + inventory recommendation out.
    python backend/predict_cli.py FOODS_1_001 CA_1 [--current 120] [--lead 5] [--service 0.95]
This is the exact function the FastAPI /recommendation endpoint calls."""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import config  # noqa: E402
from app.engine import Engine, UnknownSeries  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("item_id"); ap.add_argument("store_id")
ap.add_argument("--current", type=float); ap.add_argument("--lead", type=int); ap.add_argument("--service", type=float, default=0.95)
a = ap.parse_args()
try:
    out = Engine(config.ARTIFACT_DIR).recommendation(a.item_id, a.store_id, current_inventory=a.current, lead_time_days=a.lead, service_level=a.service)
except UnknownSeries as e:
    sys.exit(f"error: {e}")
out.pop("placement"); out["daily"] = out["daily"][:7] + [{"...": f"{len(out['daily']) - 7} more days"}]
print(json.dumps(out, indent=2))
