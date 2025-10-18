"""
Subscriptions API endpoints - Placeholder
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/plans")
async def list_plans():
    """List available subscription plans"""
    return {"message": "Subscription plans endpoint - Coming soon"}

@router.post("/subscribe")
async def create_subscription():
    """Create a new subscription"""
    return {"message": "Create subscription endpoint - Coming soon"}

@router.get("/current")
async def get_current_subscription():
    """Get current user subscription"""
    return {"message": "Current subscription endpoint - Coming soon"}