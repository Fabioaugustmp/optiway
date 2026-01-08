import os
import sys

# Mock App Context
sys.path.append(os.getcwd())

# 1. Load .env manually
env_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(env_path):
    print(f"Loading {env_path}")
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val
else:
    print(".env NOT FOUND")

from app.services.crawler_service import AmadeusCrawler

def test_fetch_hotels():
    print("--- Debug Amadeus Hotels ---")
    key = os.getenv("AMADEUS_API_KEY")
    secret = os.getenv("AMADEUS_API_SECRET")
    
    if not key or not secret:
        print("Missing Credentials in .env")
        return

    print("Initializing Crawler...")
    try:
        # Use production=False unless user specifies otherwise? 
        # But 'hostname' param needs to match credentials. 
        # Usually keys are for Test (Sandbox) or Production.
        # Let's assume Test for now, or try both if one fails?
        # The code defaults to 'test' if production=False.
        crawler = AmadeusCrawler(key, secret, production=False)
        print(f"Ready: {crawler.client_ready}")
        
        print("Fetching Hotels for Miami...")
        hotels = crawler.fetch_hotels(["Miami"])
        print(f"Hotels Found: {len(hotels)}")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        if hasattr(e, 'response'):
            print(f"RESPONSE BODY: {e.response.body}")

if __name__ == "__main__":
    test_fetch_hotels()
