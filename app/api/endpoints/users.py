from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.db.database import get_db
from app.db.models import User, SearchHistory, Itinerary
from fastapi import HTTPException
import json
from app.core.security import get_current_user

router = APIRouter()

class SearchHistoryResponse(BaseModel):
    id: int
    origin: str
    destinations: str
    start_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/history", response_model=List[SearchHistoryResponse])
def get_user_history(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = db.query(SearchHistory)\
        .filter(SearchHistory.user_id == current_user.id)\
        .order_by(SearchHistory.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return history


@router.get("/history/{search_id}")
def get_history_detail(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return saved itinerary detail for a given search (owner or admin only)."""
    search = db.query(SearchHistory).filter(SearchHistory.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    if search.user_id != current_user.id and getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    it = db.query(Itinerary).filter(Itinerary.search_id == search_id).first()
    if not it:
        raise HTTPException(status_code=404, detail="Itinerary not found for this search")

    try:
        itinerary_list = json.loads(it.details_json)
    except Exception:
        itinerary_list = it.details_json

    # Parse alternatives if available
    alternatives = None
    if it.alternatives_json:
        try:
            alternatives = json.loads(it.alternatives_json)
        except Exception:
            alternatives = it.alternatives_json
    
    # Parse cost breakdown if available
    cost_breakdown = None
    if it.cost_breakdown_json:
        try:
            cost_breakdown = json.loads(it.cost_breakdown_json)
        except Exception:
            pass

    # Parse hotels if available
    hotels_found = []
    if it.hotels_json:
        try:
            hotels_found = json.loads(it.hotels_json)
        except Exception:
            pass

    resp = {
        "status": "Saved",
        "itinerary": itinerary_list,
        "total_cost": it.total_cost,
        "total_duration": it.total_duration,
        "warning_message": None,
        "alternatives": alternatives,
        "cost_breakdown": cost_breakdown,
        "hotels_found": hotels_found
    }
    return resp
