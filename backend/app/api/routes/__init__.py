"""
API Routes for Texas PIA Automation System
"""
from fastapi import APIRouter

from app.api.routes.requests import router as requests_router
from app.api.routes.documents import router as documents_router
from app.api.routes.emails import router as emails_router
from app.api.routes.workflow import router as workflow_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.auth import router as auth_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(requests_router, prefix="/requests", tags=["PIA Requests"])
router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(emails_router, prefix="/emails", tags=["Emails"])
router.include_router(workflow_router, prefix="/workflow", tags=["Workflow"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
