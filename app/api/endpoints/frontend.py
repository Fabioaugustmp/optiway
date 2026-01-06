from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.security import get_current_user
from app.db.database import get_db
from sqlalchemy.orm import Session

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
