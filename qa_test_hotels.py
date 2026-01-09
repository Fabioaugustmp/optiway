import requests
import json
from datetime import datetime, timedelta

def test_hotel_search():
    url = "http://localhost:8000/api/solve"
    
    # Login first to get token (if needed, but assuming endpoints might be open or we check auth)
    # Actually, the user flow uses a token. Let's try to hit the endpoint.
    # Wait, the endpoint requires auth. I need to get a token.
    
    # Assuming standard test user credential or creating one? 
    # Let's try to register a temp user first to be safe
    auth_url = "http://localhost:8000/auth/register"
    email = f"qa_{int(datetime.now().timestamp())}@test.com"
    qp = {"email": email, "password": "password123", "full_name": "QA Tester"}
    
    try:
        requests.post(auth_url, json=qp)
    except:
        pass # Might already exist

    login_url = "http://localhost:8000/auth/login"
    resp = requests.post(login_url, data={"username": email, "password": "password123"})
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        # Try to just print root to see if server is up
        try:
            print(requests.get("http://localhost:8000/").json())
            print(requests.get("http://localhost:8000/openapi.json").status_code)
        except:
             pass
        return

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # payload
    start_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    payload = {
        "origin_cities": ["GRU"],
        "destination_cities": ["GIG"], # Rio usually has hotels
        "mandatory_cities": [],
        "start_date": start_date,
        "is_round_trip": False,
        "pax_adults": 1,
        "pax_children": 0,
        "provider": "Kayak",
        "search_hotels": True, # CRITICAL FLAG
        "stay_days_per_city": 2,
        "weight_cost": 0.5,
        "weight_time": 0.5
    }

    print(f"Sending request with search_hotels=True to {url}...")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
        
        hotels = data.get("hotels_found", [])
        print(f"Status: {data.get('status')}")
        print(f"Hotels Found: {len(hotels)}")
        
        if hotels:
            print("First hotel:", hotels[0])
        else:
            print("WARNING: No hotels found in response.")
            # Check debug info if possible
            
    except Exception as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    test_hotel_search()
