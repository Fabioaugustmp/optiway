import os
import sys
from datetime import datetime, timedelta

# Mock App Context
sys.path.append(os.getcwd())
try:
    from app.services.crawler_service import AmadeusCrawler, get_crawler
    from app.core.config import settings
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_live():
    print("--- Debug Live API ---")
    
    # 1. Check Env
    key = settings.AMADEUS_API_KEY
    secret = settings.AMADEUS_API_SECRET
    print(f"Key Present: {bool(key)}")
    print(f"Secret Present: {bool(secret)}")
    
    if not key or not secret:
        print("MISSING KEYS. Logic should fallback to Mock.")
        # But if the user forced Amadeus, it might be an issue? 
        # Actually logic falls back only if 'mock' flag is True OR keys missing.
        # But if I unchecked 'mock' in UI, and keys are missing, endpoint sets provider="Mock Data".
        # So effectively it shouldn't crash.
        return

    # 2. Init Crawler
    print("Initializing AmadeusCrawler...")
    try:
        crawler = AmadeusCrawler(key, secret, production=False)
        print(f"Client Ready: {crawler.client_ready}")
    except Exception as e:
        print(f"CRASH in Init: {e}")
        return

    # 3. Test Hotels
    print("Testing fetch_hotels(['Miami'])...")
    try:
        hotels = crawler.fetch_hotels(["Miami"])
        print(f"Hotels Found: {len(hotels)}")
        if hotels:
            print(f"First Hotel: {hotels[0]}")
    except Exception as e:
        print(f"CRASH in fetch_hotels: {e}")
        import traceback
        traceback.print_exc()

    # 4. Test Flights (Lightweight)
    print("Testing fetch_flights...")
    try:
        d = datetime.now() + timedelta(days=30)
        flights = crawler.fetch_flights("GRU", ["MIA"], d)
        print(f"Flights Found: {len(flights)}")
    except Exception as e:
        print(f"CRASH in fetch_flights: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_live()
