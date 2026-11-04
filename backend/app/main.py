import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import ROOT_DIR
from backend.app.api.routes import health, images, analysis, planning, mission

app = FastAPI(
    title="RoverMind API",
    version="0.1.0",
    description="Planetary exploration decision support system: SAM 3.1 visual segmentation, terrain-risk costmap, and custom A* path planning."
)

# Allowed origins for CORS: configurable via CORS_ORIGINS env var for production, with safe local defaults
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

env_origins = os.environ.get("CORS_ORIGINS")
if env_origins:
    ALLOWED_ORIGINS = [orig.strip() for orig in env_origins.split(",") if orig.strip()]
else:
    ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS

# Enable CORS with strict explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adds defensive HTTP security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Register route modules under both root and /api for frontend compatibility
for prefix in ["", "/api"]:
    app.include_router(health.router, prefix=prefix)
    app.include_router(images.router, prefix=prefix)
    app.include_router(analysis.router, prefix=prefix)
    app.include_router(planning.router, prefix=prefix)
    app.include_router(mission.router, prefix=prefix)

# Mount frontend production build if available
dist_dir = ROOT_DIR / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
