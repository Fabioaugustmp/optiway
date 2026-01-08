from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.security import get_current_user
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.db.models import User, SearchHistory, Itinerary

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    # Check if logged in (Cookie check handled by frontend mostly, but here for server rendering)
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login")

    # Verify token logic strictly or just pass to template to handle
    # We decode manually or use the dependency if we want to block at server level
    # For now, let's assume valid if present, otherwise JS handles 401

    # We can inject user info if we decode the token here
    # Using a soft dependency to get user without raising 401 immediately would be ideal for hybrid apps

    return templates.TemplateResponse("dashboard.html", {"request": request, "user": {"full_name": "Viajante"}})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response



@router.get("/dashboard/itineraries")
def frontend_itineraries(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return a short list of itineraries for the authenticated user (used by the dashboard JS)."""
    rows = db.query(Itinerary).join(SearchHistory).filter(SearchHistory.user_id == current_user.id).order_by(Itinerary.created_at.desc()).all()
    out = []
    for it in rows:
        out.append({
            "id": it.id,
            "search_id": it.search_id,
            "origin": it.search.origin if it.search else None,
            "destinations": it.search.destinations if it.search else None,
            "created_at": it.created_at.isoformat() if it.created_at else None,
            "total_cost": it.total_cost,
            "total_duration": it.total_duration
        })
    return out


@router.get("/itinerary/{itinerary_id}", response_class=HTMLResponse)
async def itinerary_page(request: Request, itinerary_id: int, db: Session = Depends(get_db)):
    """Render the itinerary detail page. Redirect to login if no access_token cookie present.

    The page itself will fetch full details via the authenticated API.
    """
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse("itinerary_detail.html", {"request": request, "itinerary_id": itinerary_id})
