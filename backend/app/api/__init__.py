from app.api.auth import router as auth_router
from app.api.overview import router as overview_router
from app.api.transactions import router as transactions_router
from app.api.flags import router as flags_router
from app.api.analytics import router as analytics_router
from app.api.rules import router as rules_router
from app.api.models import router as models_router
from app.api.alerts import router as alerts_router
from app.api.claims import router as claims_router

__all__ = [
    "auth_router",
    "overview_router",
    "transactions_router",
    "flags_router",
    "analytics_router",
    "rules_router",
    "models_router",
    "alerts_router",
    "claims_router",
]
