import os

ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_artifacts"))
# Comma-separated list of exact origins, e.g. "https://smartstock.vercel.app,http://localhost:3000"
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
# Optional regex (e.g. Vercel preview deployments): "https://smartstock-.*\.vercel\.app"
ALLOWED_ORIGIN_REGEX = os.environ.get("ALLOWED_ORIGIN_REGEX") or None
