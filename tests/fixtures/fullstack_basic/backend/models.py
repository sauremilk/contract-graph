"""Pydantic models for API."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class MatchResponse(BaseModel):
    id: UUID
    player_name: str
    score: int
    duration_seconds: float
    map_name: str
    is_ranked: bool
    created_at: datetime
    kills: int
    deaths: int
    assists: int
    placement: int
    match_mode: str


class PlayerStats(BaseModel):
    player_id: UUID
    display_name: str
    total_matches: int
    win_rate: float
    average_kills: float
    kd_ratio: float
    last_played: Optional[datetime]
    rank: str
    level: int


class SessionConfig(BaseModel):
    theme: str
    language: str
    auto_record: bool
    overlay_opacity: float
    notification_sound: bool
    keybind_toggle: str
