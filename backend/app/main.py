import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Any, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import Base
from app.db.session import async_engine, get_db, AsyncSessionLocal
from app.integrations.firefly import FireflyClient
from app.webhooks.receiver import router as webhook_router
from app.api import (
    auth_router,
    overview_router,
    transactions_router,
    flags_router,
    analytics_router,
    rules_router,
    models_router,
    alerts_router,
    claims_router,
)
from app.services.retrain import RetrainService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ExpenseGuard")

scheduler = AsyncIOScheduler()


async def scheduled_nightly_retrain():
    logger.info("Executing scheduled nightly anomaly model retraining...")
    async with AsyncSessionLocal() as session:
        retrain_svc = RetrainService(session)
        res = await retrain_svc.run_retrain(trigger_source="nightly_cron")
        logger.info(f"Nightly retraining finished: {res}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENVIRONMENT} mode...")

    # 1. Initialize DB tables (creates missing tables if not using Alembic)
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.error(f"Error initializing DB schema: {exc}")

    # 2. Register Webhook in Firefly III if configured
    if settings.FIREFLY_API_TOKEN:
        ff_client = FireflyClient()
        webhook_url = f"http://bridge:8000/webhooks/firefly"
        asyncio.create_task(ff_client.ensure_webhook_registered(webhook_url, settings.FIREFLY_WEBHOOK_SECRET))

    # 3. Start Retraining Scheduler (nightly at 02:00 AM)
    try:
        scheduler.add_job(scheduled_nightly_retrain, "cron", hour=2, minute=0, id="nightly_retrain", replace_existing=True)
        scheduler.start()
        logger.info("Retraining scheduler started (runs nightly at 02:00 AM).")
    except Exception as exc:
        logger.warning(f"Could not start scheduler: {exc}")

    yield

    # Teardown
    if scheduler.running:
        scheduler.shutdown()
    logger.info("ExpenseGuard shutting down.")


app = FastAPI(
    title="ExpenseGuard API",
    description="Intelligent Expense Management & Anomaly Detection Bridge for Firefly III and PyOD",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow dashboard and local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(overview_router)
app.include_router(transactions_router)
app.include_router(flags_router)
app.include_router(analytics_router)
app.include_router(rules_router)
app.include_router(models_router)
app.include_router(alerts_router)
app.include_router(claims_router)


@app.get("/healthz", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Liveness check for container orchestration and status dashboard."""
    settings = get_settings()

    # DB check
    db_ok = False
    try:
        res = await db.execute(text("SELECT 1"))
        db_ok = res.scalar() == 1
    except Exception as exc:
        logger.warning(f"Healthcheck DB failure: {exc}")

    # Firefly III check
    ff_client = FireflyClient()
    ff_health = await ff_client.check_health()

    overall = "healthy" if db_ok else "degraded"

    return {
        "status": overall,
        "database": "connected" if db_ok else "unreachable",
        "firefly_core": ff_health,
        "environment": settings.ENVIRONMENT,
        "currency": settings.DEFAULT_CURRENCY,
        "approval_limit": settings.APPROVAL_LIMIT
    }
