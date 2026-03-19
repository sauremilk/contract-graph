"""Pydantic models — regression demo.

This fixture simulates real-world drift scenarios that mypy and tsc
both miss but contract-graph catches.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: UUID
    email: str
    premium_tier: bool  # Changed from str → bool; frontend still says string
    display_name: str
    login_count: int
    last_login: Optional[datetime]  # Optional — frontend says required
    bio: Optional[str]  # Optional — frontend says required


class OrderResponse(BaseModel):
    order_id: UUID
    total_amount: float
    currency: str
    status: str
    discount_code: str  # NEW field — frontend doesn't have it yet
    created_at: datetime


class NotificationSettings(BaseModel):
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    quiet_hours_start: int  # hour 0-23
    quiet_hours_end: int  # hour 0-23
