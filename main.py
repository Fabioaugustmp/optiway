from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import auth, flights, users, frontend
from app.db.init_db import init_db

# Initialize DB
init_db()

app = FastAPI(title="Viagem Otimizada Enterprise")

# Mount Static
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(flights.router, prefix="/api", tags=["Flights"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(frontend.router, tags=["Frontend"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
