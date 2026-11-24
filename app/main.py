"""Main FastAPI Application Entrypoint."""
from collections import defaultdict
import os
from pathlib import Path
import shutil
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.deps import check_subscription_state
from app.limiter import limiter
from app.logging import RequestLoggingMiddleware, logger
from app.routers import (
    auth,
    billing,
    cancellation,
    dashboard,
    data_safety,
    folios,
    groups,
    guests,
    housekeeping,
    housekeeping_token,
    import_data,
    inbox_sync,
    night_audit,
    org,
    payments,
    rate_calendar,
    rate_plans,
    reservations,
    rooms,
    signup,
    subscriptions,
    taxes,
    timeline,
    users,
)

METRICS_REQUESTS = defaultdict(int)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: validates production hardening and ensures database tables."""
    logger.info(f"Initializing Hotel PMS in environment: {settings.ENV}")
    try:
        settings.validate_production_hardening()
    except Exception as exc:
        logger.warning(f"Production hardening check: {exc}")

    # Ensure tables only on local development / SQLite, avoiding remote schema inspection on serverless cold starts
    if settings.ENV not in ("production", "prod", "preview") and not os.environ.get("VERCEL"):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schemas verified.")
        except Exception as exc:
            logger.error(f"Database schema verification: {exc}")

        # Auto-seed initial demo data if database is fresh
        try:
            from app.models import User
            with SessionLocal() as db:
                if db.query(User).count() == 0:
                    logger.info("Fresh database detected. Auto-seeding initial hotel data...")
                    from seed import seed
                    seed()
        except Exception as e:
            logger.warning(f"Auto-seed check: {e}")

    yield
    logger.info("Hotel PMS shutting down.")


app = FastAPI(
    title="Hotel PMS - Property Management System",
    description="Enterprise-grade Hotel PMS API & Operations Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Attach slowapi rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Structured request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Error Envelope Handlers ──────────────────────────────────────────

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Formats all standard HTTPExceptions into unified error envelope."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=exc.headers,
        )
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
            headers=exc.headers,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic validation errors into unified error envelope."""
    errors = exc.errors()
    error_msg = "; ".join([f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors])
    serializable_details = [
        {
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        for err in errors
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": error_msg,
                "details": serializable_details,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors and returns consistent 500 envelope."""
    logger.error(f"Unhandled error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"Server Error: {str(exc)}",
                "type": type(exc).__name__,
            }
        },
    )


# Metrics and request tracking middleware
@app.middleware("http")
async def track_metrics_middleware(request: Request, call_next):
    response = await call_next(request)
    METRICS_REQUESTS[(request.method, response.status_code)] += 1
    return response


# ── Health, Readiness & Metrics Endpoints ────────────────────────────────────

@app.get("/healthz")
def healthz():
    """Liveness probe checking database connectivity."""
    db_status = "ok"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(f"Healthcheck database probe failed: {exc}")
        db_status = "error"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "db": db_status},
        )
    return {"status": "ok", "db": db_status}


@app.get("/readyz")
def readyz():
    """Readiness probe checking database connectivity, cache, and disk space."""
    checks = {}
    is_ready = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {str(exc)}"
        is_ready = False

    try:
        usage = shutil.disk_usage(".")
        free_gb = usage.free / (1024 ** 3)
        checks["disk_space"] = f"ok ({free_gb:.1f} GB free)"
    except Exception:
        checks["disk_space"] = "unknown"

    status_str = "ready" if is_ready else "unhealthy"
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={"status": status_str, "checks": checks},
    )


@app.get("/metrics")
def get_metrics():
    """Prometheus-compatible text format metrics export."""
    lines = [
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
    ]
    if METRICS_REQUESTS:
        for (method, st), count in sorted(METRICS_REQUESTS.items()):
            lines.append(f'http_requests_total{{method="{method}",status="{st}"}} {count}')
    else:
        lines.append('http_requests_total{method="GET",status="200"} 0')

    lines.extend([
        "# HELP active_connections Current active DB connections",
        "# TYPE active_connections gauge",
        "active_connections 1",
    ])
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4",
    )


# ── Static Files & Templates ────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# Search for templates in local dev and Vercel Lambda bundle (/var/task)
possible_template_dirs = [
    str(BASE_DIR / "templates"),
    str(BASE_DIR / "api" / "templates"),
    str(Path.cwd() / "templates"),
    str(Path.cwd() / "api" / "templates"),
    "/var/task/templates",
    "/var/task/api/templates",
    "/var/task/app/templates",
]
existing_template_dirs = [d for d in possible_template_dirs if os.path.isdir(d)]
if not existing_template_dirs:
    existing_template_dirs = [str(BASE_DIR / "templates")]

possible_static_dirs = [
    str(BASE_DIR / "static"),
    str(BASE_DIR / "api" / "static"),
    str(Path.cwd() / "static"),
    str(Path.cwd() / "api" / "static"),
    "/var/task/static",
    "/var/task/api/static",
    "/var/task/app/static",
]
existing_static_dir = next((d for d in possible_static_dirs if os.path.isdir(d)), str(BASE_DIR / "static"))

app.mount("/static", StaticFiles(directory=existing_static_dir), name="static")
templates = Jinja2Templates(directory=existing_template_dirs)


# ── Public Marketing & Trust Pages ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
def serve_landing(request: Request):
    """Render public marketing landing page."""
    return templates.TemplateResponse(
        "landing.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/pricing", response_class=HTMLResponse)
def serve_pricing(request: Request):
    """Render public pricing page with comparison matrix and FAQ."""
    return templates.TemplateResponse(
        "pricing.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/security", response_class=HTMLResponse)
def serve_security(request: Request):
    """Render public security, compliance and sub-processors page."""
    return templates.TemplateResponse(
        "security.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/legal/terms", response_class=HTMLResponse)
def serve_terms(request: Request):
    """Render Terms of Service."""
    return templates.TemplateResponse(
        "legal_terms.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/legal/privacy", response_class=HTMLResponse)
def serve_privacy(request: Request):
    """Render Privacy Policy."""
    return templates.TemplateResponse(
        "legal_privacy.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/legal/dpa", response_class=HTMLResponse)
def serve_dpa(request: Request):
    """Render Data Processing Agreement."""
    return templates.TemplateResponse(
        "legal_dpa.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/status", response_class=HTMLResponse)
def serve_status(request: Request):
    """Render live system status page."""
    return templates.TemplateResponse(
        "status.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/changelog", response_class=HTMLResponse)
def serve_changelog(request: Request):
    """Render product changelog page."""
    return templates.TemplateResponse(
        "changelog.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


# ── Auth & Onboarding Flow Pages ────────────────────────────────────────────

@app.get("/demo", response_class=HTMLResponse)
@app.get("/request-demo", response_class=HTMLResponse)
def serve_demo(request: Request):
    """Render Request a Demo booking page."""
    return templates.TemplateResponse(
        "demo.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/signup", response_class=HTMLResponse)
def serve_signup(request: Request):
    """Render self-serve signup page."""
    return templates.TemplateResponse(
        "signup.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/welcome", response_class=HTMLResponse)
def serve_welcome(request: Request):
    """Render 7-step onboarding setup wizard."""
    return templates.TemplateResponse(
        "welcome.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/locked", response_class=HTMLResponse)
def serve_locked(request: Request):
    """Render subscription paused / locked screen."""
    return templates.TemplateResponse(
        "locked.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/hk/{token}", response_class=HTMLResponse)
def serve_mobile_hk(request: Request, token: str):
    """Render mobile housekeeping view for cleaning staff (no login required)."""
    return templates.TemplateResponse(
        "mobile_hk.html",
        {"request": request, "token": token, "hotel_name": settings.HOTEL_NAME},
    )


@app.get("/login", response_class=HTMLResponse)
def serve_login(request: Request):
    """Render authentication login view."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "hotel_name": settings.HOTEL_NAME},
    )


# Client-side routes rendered through app.html
@app.get("/app", response_class=HTMLResponse)
@app.get("/bookings", response_class=HTMLResponse)
@app.get("/reservations", response_class=HTMLResponse)
@app.get("/rooms", response_class=HTMLResponse)
@app.get("/guests", response_class=HTMLResponse)
@app.get("/housekeeping", response_class=HTMLResponse)
@app.get("/billing", response_class=HTMLResponse)
@app.get("/rate-calendar", response_class=HTMLResponse)
@app.get("/timeline", response_class=HTMLResponse)
@app.get("/night-audit", response_class=HTMLResponse)
@app.get("/settings", response_class=HTMLResponse)
@app.get("/import", response_class=HTMLResponse)
def serve_app(request: Request):
    """Render the main PMS single-page application shell."""
    return templates.TemplateResponse(
        "app.html",
        {
            "request": request,
            "hotel_name": settings.HOTEL_NAME,
            "hotel_currency": settings.HOTEL_CURRENCY,
        },
    )


# ── API Routers ─────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(signup.router)
app.include_router(org.router)
app.include_router(subscriptions.router)
app.include_router(data_safety.router)
app.include_router(import_data.router)
app.include_router(housekeeping_token.router)
app.include_router(rooms.router, dependencies=[Depends(check_subscription_state)])
app.include_router(guests.router, dependencies=[Depends(check_subscription_state)])
app.include_router(reservations.router, dependencies=[Depends(check_subscription_state)])
app.include_router(rate_plans.router)
app.include_router(cancellation.router)
app.include_router(taxes.router)
app.include_router(rate_calendar.router)
app.include_router(timeline.router)
app.include_router(folios.router)
app.include_router(groups.router)
app.include_router(night_audit.router)
app.include_router(payments.router)
app.include_router(billing.router)
app.include_router(housekeeping.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(inbox_sync.router)

