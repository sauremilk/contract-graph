"""FastAPI routes — regression demo."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/users/{user_id}/profile", response_model="UserProfile")
async def get_user_profile(user_id: str):
    pass


@router.get("/orders/{order_id}", response_model="OrderResponse")
async def get_order(order_id: str):
    pass


@router.get("/settings/notifications", response_model="NotificationSettings")
async def get_notification_settings():
    pass
