from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.db.database import get_db
from app.db.models import User, SearchHistory
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
