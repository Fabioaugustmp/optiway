import requests
import json
import os

def download_airports():
    url = "https://raw.githubusercontent.com/mwgg/Airports/master/airports.json"
    target_path = "app/data/airports.json"
    
    print(f"Downloading airports data from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Filter: Only keep airports with IATA codes and valid cities
        # This reduces size and ensures data quality for our system
        filtered = {}
        for iata, info in data.items():
            if info.get('iata') and info.get('city') and info.get('iata') != '0':
                filtered[info['iata']] = {
                    "name": info.get('name'),
                    "city": info.get('city'),
                    "country": info.get('country'),
                    "iata": info.get('iata'),
                    "lat": info.get('lat'),
                    "lon": info.get('lon')
                }
        
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully saved {len(filtered)} airports to {target_path}")
        return True
    except Exception as e:
        print(f"Failed to download airports: {e}")
        return False

if __name__ == "__main__":
    download_airports()
