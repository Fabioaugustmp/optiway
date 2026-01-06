from fastapi.testclient import TestClient
from main import app
from app.db.database import get_db, Base, engine
from app.db.models import User
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, StaticPool
import uuid

# Setup In-Memory DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

Base.metadata.create_all(bind=engine_test)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def get_unique_email():
    return f"test_{uuid.uuid4()}@example.com"

def test_register_and_login():
    email = get_unique_email()
    # 1. Register
    reg_res = client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "full_name": "Test User"
    })
    assert reg_res.status_code == 200
    assert reg_res.json()["email"] == email

    # 2. Login
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": "password123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    return token

def test_flight_search_flow():
    token = test_register_and_login()

    # 3. Solve (Search + Optimize)
    solve_res = client.post("/api/solve",
        json={
            "origin_cities": ["São Paulo"],
            "destination_cities": ["Rio de Janeiro"],
            "mandatory_cities": [],
            "pax_adults": 1,
            "pax_children": 0,
            "start_date": "2024-12-01T00:00:00",
            "weight_cost": 0.5,
            "weight_time": 0.5,
            "allow_open_jaw": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert solve_res.status_code == 200
    data = solve_res.json()
    assert data["status"] == "Optimal"
    assert len(data["itinerary"]) > 0
    assert data["total_cost"] > 0
