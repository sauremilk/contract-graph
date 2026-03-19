"""FastAPI routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/matches/{match_id}", response_model="MatchResponse")
async def get_match(match_id: str):
    pass


@router.get("/players/{player_id}/stats", response_model="PlayerStats")
async def get_player_stats(player_id: str):
    pass


@router.post("/sessions/config", response_model="SessionConfig")
async def update_session_config():
    pass
