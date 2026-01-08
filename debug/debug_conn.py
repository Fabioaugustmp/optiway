import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test():
    print(f"Testing connectivity to {BASE_URL}...")
    # 1. Login
    try:
        # Check if server is up
        try:
            requests.get(BASE_URL, timeout=5)
        except Exception as e:
            print(f"Server is unreachable: {e}")
            return

        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "qa_final@example.com", "password": "password123"})
        if resp.status_code != 200:
            print(f"Login Failed: {resp.status_code} {resp.text}")
            # Try register if login fails (maybe DB was wiped)
            print("Attempting registration...")
            reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"email": "qa_final@example.com", "password": "password123", "full_name": "QA"})
            print(f"Register status: {reg_resp.status_code}")
            
            resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "qa_final@example.com", "password": "password123"})
        
        if resp.status_code != 200:
             print("Login still failed.")
             return

        token = resp.json()['access_token']
        print("Logged in successfully.")
        
        # 2. Call Solve
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "origin_cities": ["São Paulo"],
            "destination_cities": ["Rio de Janeiro"],
            "mandatory_cities": [],
            "pax_adults": 1,
            "pax_children": 0,
            "start_date": "2026-02-01T10:00:00",
            "weight_cost": 0.5,
            "weight_time": 0.5
        }
        print("Sending /api/solve request (Testing Car Search integration)...")
        resp = requests.post(f"{BASE_URL}/api/solve", json=payload, headers=headers, timeout=60) # High timeout for crawler
        print(f"Solve Status: {resp.status_code}")
        print(f"Solve Response: {resp.text[:500]}")
        
    except requests.exceptions.Timeout:
        print("TIMEOUT: The request took too long (>60s). This is likely the cause of 'Connection Error'.")
    except requests.exceptions.ConnectionError:
        print("CONNECTION ERROR: The server closed the connection or is down.")
    except Exception as e:
        print(f"CRASH TEST FAILED: {e}")

if __name__ == "__main__":
    test()
