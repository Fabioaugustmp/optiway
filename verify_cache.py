import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# App Context for DB Access
sys.path.append(os.getcwd())
try:
    from app.db.models import FlightOption
    from app.db.database import Base
    # Connect to DB locally to count rows
    engine = create_engine("sqlite:///./travel_app_v2.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except ImportError as e:
    print(f"DB Import Error: {e}")
    sys.exit(1)

def count_flight_options():
    db = SessionLocal()
    count = db.query(func.count(FlightOption.id)).scalar()
    db.close()
    return count

def get_auth_token():
    base_url = "http://localhost:8000"
    user_cred = {"email": "famp10@email.com", "password": "123456"}
    requests.post(f"{base_url}/auth/register", json={**user_cred, "full_name": "Fabio User"})
    res = requests.post(f"{base_url}/auth/login", data={"username": user_cred["email"], "password": user_cred["password"]})
    if res.status_code == 200:
        return res.json()["access_token"]
    return None

def run_search(token):
    url = "http://localhost:8000/api/solve"
    # Use fixed date so cache matches
    fixed_date = (datetime.now() + timedelta(days=40)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    
    payload = {
        "origin_cities": ["São Paulo"],
        "destination_cities": ["Salvador"], # Simple route
        "mandatory_cities": [],
        "pax_adults": 1,
        "pax_children": 0,
        "start_date": fixed_date,
        "weight_cost": 1.0,
        "weight_time": 0.0,
        "is_round_trip": False,
        "use_mock_data": True, # Use Mock to ensure we get results
        "search_hotels": False # Disable hotels to focus on flight cache
    }
    
    start = time.time()
    res = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    duration = time.time() - start
    return res.status_code, duration

def verify():
    print("--- Cache Verification ---")
    token = get_auth_token()
    if not token:
        print("Auth Failed")
        return

    # 1. Initial State
    c1 = count_flight_options()
    print(f"Initial Flight Options: {c1}")

    # 2. First Run (Cache Miss - Write to DB)
    print("\nRun 1 (Expect Cache Miss)...")
    code, d1 = run_search(token)
    print(f"Status: {code}, Time: {d1:.2f}s")
    
    c2 = count_flight_options()
    print(f"Flight Options after Run 1: {c2}")
    if c2 <= c1:
        print("WARNING: No flights saved? (Maybe Mock returned cached? or error?)")
    else:
        print(f"Saved {c2 - c1} new flights.")

    # 3. Second Run (Expect Cache Hit - No Write)
    print("\nRun 2 (Expect Cache Hit)...")
    code, d2 = run_search(token)
    print(f"Status: {code}, Time: {d2:.2f}s")
    
    c3 = count_flight_options()
    print(f"Flight Options after Run 2: {c3}")
    
    if c3 == c2:
        print("SUCCESS: Count remained same. Cache Hit used.")
    else:
        print(f"FAILURE: Count increased by {c3 - c2}. Cache Miss occurred.")

if __name__ == "__main__":
    verify()
