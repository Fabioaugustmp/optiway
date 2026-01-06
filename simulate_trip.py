import requests
import json
from datetime import datetime, timedelta

def get_auth_token():
    # 1. Try Register
    base_url = "http://localhost:8000"
    user_cred = {
        "email": "famp10@email.com",
        "password": "123456",
        "full_name": "Fabio User"
    }

    print(f"Attempting to register/login user: {user_cred['email']}")

    # Register
    reg_res = requests.post(f"{base_url}/auth/register", json=user_cred)
    if reg_res.status_code == 200:
        print("Registration successful.")
    elif reg_res.status_code == 400:
        print("User likely already exists. Proceeding to login.")
    else:
        print(f"Registration failed: {reg_res.text}")

    # Login
    login_data = {
        "username": user_cred["email"],
        "password": user_cred["password"]
    }
    res = requests.post(f"{base_url}/auth/login", data=login_data)
    
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        return None
    
    return res.json()["access_token"]

def simulate():
    print("\n🚀 Simulating Trip Request to http://localhost:8000/api/solve")
    
    url = "http://localhost:8000/api/solve"
    
    payload = {
        "origin_cities": ["São Paulo"],
        "destination_cities": ["Miami", "Orlando"],
        "mandatory_cities": ["New York"],
        "pax_adults": 2,
        "pax_children": 1,
        "start_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "weight_cost": 0.6,
        "weight_time": 0.4,
        "is_round_trip": True,
        "stay_days_per_city": 3,
        "daily_cost_per_person": 100.0,
        "allow_open_jaw": True,
        "use_mock_data": True
    }
    
    print(f"Params: 2 Adults, 1 Child. Route: SP -> NY (Mandatory) -> Miami/Orlando -> SP")
    
    token = get_auth_token()
    if not token:
        print("Cannot proceed without auth token.")
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers) # timeout removed to avoid early kill if startup is slow
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Simulation Successful!")
            print(f"Optimization Status: {data.get('status')}")
            print(f"Total Movement Cost: R$ {data.get('total_cost'):.2f}")
            print(f"Total Duration: {data.get('total_duration')} min")
            
            print("\n🗓️ Itinerary:")
            if 'itinerary' in data:
                steps = data['itinerary']
                for i, leg in enumerate(steps):
                    fl = leg.get('flight')
                    provider = fl.get('airline', 'Unknown') if fl else "Unknown"
                    print(f"{i+1}. {leg['origin']} ➡️ {leg['destination']}")
                    print(f"   Provider: {provider} | Price: {leg['price_formatted']}")
                    
        else:
            print(f"❌ Request Failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request Error: {e}")

if __name__ == "__main__":
    simulate()
