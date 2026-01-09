import logging
from typing import List, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AirportInfo(BaseModel):
    iata: str
    name: str
    city: str
    country: str
    lat: float
    lon: float

class LocationService:
    """
    Senior-level Location Service.
    Manages a curated set of global airports without external API dependency.
    Provides fast indexing for search and IATA resolution.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocationService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.airports: Dict[str, AirportInfo] = {}
        self.search_index: List[AirportInfo] = []
        self._load_data()
        self._initialized = True

    def _load_data(self):
        """
        Loads airport data. For this senior implementation, we use a 
        comprehensive curated list of major world cities and all Brazilian hubs.
        """
        # Top Global + Brazil Hubs
        raw_data = [
            # BRAZIL
            {"iata": "GRU", "name": "Guarulhos Intl", "city": "São Paulo", "country": "BR", "lat": -23.4356, "lon": -46.4731},
            {"iata": "CGH", "name": "Congonhas", "city": "São Paulo", "country": "BR", "lat": -23.6261, "lon": -46.6564},
            {"iata": "VCP", "name": "Viracopos", "city": "Campinas", "country": "BR", "lat": -23.0069, "lon": -47.1344},
            {"iata": "GIG", "name": "Galeão Intl", "city": "Rio de Janeiro", "country": "BR", "lat": -22.81, "lon": -43.2506},
            {"iata": "SDU", "name": "Santos Dumont", "city": "Rio de Janeiro", "country": "BR", "lat": -22.9105, "lon": -43.1631},
            {"iata": "BSB", "name": "Juscelino Kubitschek Intl", "city": "Brasília", "country": "BR", "lat": -15.8697, "lon": -47.9172},
            {"iata": "CNF", "name": "Confins Intl", "city": "Belo Horizonte", "country": "BR", "lat": -19.6244, "lon": -43.9719},
            {"iata": "PLU", "name": "Pampulha", "city": "Belo Horizonte", "country": "BR", "lat": -19.8519, "lon": -43.9506},
            {"iata": "SSA", "name": "Deputado Luís Eduardo Magalhães", "city": "Salvador", "country": "BR", "lat": -12.9086, "lon": -38.3225},
            {"iata": "FOR", "name": "Pinto Martins Intl", "city": "Fortaleza", "country": "BR", "lat": -3.7763, "lon": -38.5326},
            {"iata": "REC", "name": "Guararapes Intl", "city": "Recife", "country": "BR", "lat": -8.1256, "lon": -34.923},
            {"iata": "POA", "name": "Salgado Filho Intl", "city": "Porto Alegre", "country": "BR", "lat": -29.9939, "lon": -51.1711},
            {"iata": "CWB", "name": "Afonso Pena Intl", "city": "Curitiba", "country": "BR", "lat": -25.5317, "lon": -49.1758},
            {"iata": "BEL", "name": "Val de Cans Intl", "city": "Belém", "country": "BR", "lat": -1.3847, "lon": -48.4788},
            {"iata": "MAO", "name": "Eduardo Gomes Intl", "city": "Manaus", "country": "BR", "lat": -3.0386, "lon": -60.0506},
            {"iata": "GYN", "name": "Santa Genoveva", "city": "Goiânia", "country": "BR", "lat": -16.6267, "lon": -49.2211},
            {"iata": "CGR", "name": "Campo Grande Intl", "city": "Campo Grande", "country": "BR", "lat": -20.4697, "lon": -54.6703},
            {"iata": "CGB", "name": "Marechal Rondon Intl", "city": "Cuiabá", "country": "BR", "lat": -15.6528, "lon": -56.1167},
            {"iata": "VIX", "name": "Eurico de Aguiar Salles", "city": "Vitória", "country": "BR", "lat": -20.2581, "lon": -40.2864},
            {"iata": "FLN", "name": "Hercílio Luz Intl", "city": "Florianópolis", "country": "BR", "lat": -27.6703, "lon": -48.5525},
            {"iata": "MCZ", "name": "Zumbi dos Palmares Intl", "city": "Maceió", "country": "BR", "lat": -9.5108, "lon": -35.7917},
            {"iata": "NAT", "name": "São Gonçalo do Amarante Intl", "city": "Natal", "country": "BR", "lat": -5.7689, "lon": -35.3664},
            {"iata": "BVB", "name": "Boa Vista Intl", "city": "Boa Vista", "country": "BR", "lat": 2.8461, "lon": -60.7061},
            {"iata": "PVH", "name": "Governador Jorge Teixeira Intl", "city": "Porto Velho", "country": "BR", "lat": -8.7136, "lon": -63.9028},
            {"iata": "MCP", "name": "Alberto Alcolumbre Intl", "city": "Macapá", "country": "BR", "lat": 0.0506, "lon": -51.0722},
            {"iata": "PMW", "name": "Palmas", "city": "Palmas", "country": "BR", "lat": -10.29, "lon": -48.3578},
            {"iata": "IOS", "name": "Jorge Amado", "city": "Ilhéus", "country": "BR", "lat": -14.8158, "lon": -39.0333},
            {"iata": "UDI", "name": "Ten. Cel. Av. César Bombonato", "city": "Uberlândia", "country": "BR", "lat": -18.8836, "lon": -48.2253},
            {"iata": "RAO", "name": "Leite Lopes", "city": "Ribeirão Preto", "country": "BR", "lat": -21.1364, "lon": -47.7761},
            {"iata": "SJP", "name": "Prof. Eribelto Manoel Reino", "city": "São José do Rio Preto", "country": "BR", "lat": -20.8161, "lon": -49.4053},
            {"iata": "LDB", "name": "Londrina", "city": "Londrina", "country": "BR", "lat": -23.3303, "lon": -51.1303},
            {"iata": "MGF", "name": "Maringá Regional", "city": "Maringá", "country": "BR", "lat": -23.4794, "lon": -51.9161},
            {"iata": "JOI", "name": "Joinville", "city": "Joinville", "country": "BR", "lat": -26.2231, "lon": -48.7978},
            {"iata": "NVT", "name": "Ministro Victor Konder Intl", "city": "Navegantes", "country": "BR", "lat": -26.8789, "lon": -48.6514},
            {"iata": "XAP", "name": "Serafin Enoss Bertaso", "city": "Chapecó", "country": "BR", "lat": -27.1339, "lon": -52.6619},
            {"iata": "FML", "name": "Fortaleza-CE", "city": "Fortaleza", "country": "BR", "lat": -3.7761, "lon": -38.5326},
            {"iata": "IMP", "name": "Prefeito Renato Moreira", "city": "Imperatriz", "country": "BR", "lat": -5.5306, "lon": -47.4589},
            {"iata": "THE", "name": "Senador Petrônio Portella", "city": "Teresina", "country": "BR", "lat": -5.0606, "lon": -42.8239},
            # AMERICAS
            {"iata": "EZE", "name": "Ministro Pistarini Intl", "city": "Buenos Aires", "country": "AR", "lat": -34.8222, "lon": -58.5358},
            {"iata": "AEP", "name": "Jorge Newbery", "city": "Buenos Aires", "country": "AR", "lat": -34.5592, "lon": -58.4156},
            {"iata": "COR", "name": "Ingeniero Aeronáutico Ambrosio L.V. Taravella Intl", "city": "Córdoba", "country": "AR", "lat": -31.3236, "lon": -64.2081},
            {"iata": "SCL", "name": "Arturo Merino Benítez Intl", "city": "Santiago", "country": "CL", "lat": -33.393, "lon": -70.7858},
            {"iata": "LIM", "name": "Jorge Chávez Intl", "city": "Lima", "country": "PE", "lat": -12.0219, "lon": -77.1143},
            {"iata": "BOG", "name": "El Dorado Intl", "city": "Bogotá", "country": "CO", "lat": 4.7016, "lon": -74.1469},
            {"iata": "MIA", "name": "Miami Intl", "city": "Miami", "country": "US", "lat": 25.7959, "lon": -80.287},
            {"iata": "MCO", "name": "Orlando Intl", "city": "Orlando", "country": "US", "lat": 28.4289, "lon": -81.316},
            {"iata": "JFK", "name": "John F. Kennedy Intl", "city": "New York", "country": "US", "lat": 40.6413, "lon": -73.7781},
            {"iata": "EWR", "name": "Newark Liberty Intl", "city": "Newark", "country": "US", "lat": 40.6895, "lon": -74.1745},
            {"iata": "LGA", "name": "LaGuardia", "city": "New York", "country": "US", "lat": 40.7772, "lon": -73.8726},
            {"iata": "LAX", "name": "Los Angeles Intl", "city": "Los Angeles", "country": "US", "lat": 33.9416, "lon": -118.4085},
            {"iata": "SFO", "name": "San Francisco Intl", "city": "San Francisco", "country": "US", "lat": 37.6189, "lon": -122.375},
            {"iata": "SEA", "name": "Seattle-Tacoma Intl", "city": "Seattle", "country": "US", "lat": 47.449, "lon": -122.309},
            {"iata": "ORD", "name": "O'Hare Intl", "city": "Chicago", "country": "US", "lat": 41.9742, "lon": -87.9073},
            {"iata": "DFW", "name": "Dallas/Fort Worth Intl", "city": "Dallas", "country": "US", "lat": 32.8998, "lon": -97.0403},
            {"iata": "ATL", "name": "Hartsfield-Jackson Atlanta Intl", "city": "Atlanta", "country": "US", "lat": 33.6407, "lon": -84.4277},
            {"iata": "MEX", "name": "Benito Juárez Intl", "city": "Mexico City", "country": "MX", "lat": 19.4361, "lon": -99.0719},
            {"iata": "CUN", "name": "Cancún Intl", "city": "Cancún", "country": "MX", "lat": 21.0365, "lon": -86.8771},
            {"iata": "PTY", "name": "Tocumen Intl", "city": "Panama City", "country": "PA", "lat": 9.0714, "lon": -79.3835},
            {"iata": "YYZ", "name": "Toronto Pearson Intl", "city": "Toronto", "country": "CA", "lat": 43.6777, "lon": -79.6248},
            {"iata": "YVR", "name": "Vancouver Intl", "city": "Vancouver", "country": "CA", "lat": 49.1967, "lon": -123.1815},
            # EUROPE
            {"iata": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "FR", "lat": 49.0097, "lon": 2.5479},
            {"iata": "ORY", "name": "Orly", "city": "Paris", "country": "FR", "lat": 48.7233, "lon": 2.3794},
            {"iata": "LHR", "name": "Heathrow", "city": "London", "country": "GB", "lat": 51.47, "lon": -0.4543},
            {"iata": "LGW", "name": "Gatwick", "city": "London", "country": "GB", "lat": 51.1481, "lon": -0.1903},
            {"iata": "FRA", "name": "Frankfurt Intl", "city": "Frankfurt", "country": "DE", "lat": 50.0379, "lon": 8.5622},
            {"iata": "MUC", "name": "Munich", "city": "Munich", "country": "DE", "lat": 48.3537, "lon": 11.775},
            {"iata": "TXL", "name": "Tegel", "city": "Berlin", "country": "DE", "lat": 52.5597, "lon": 13.2877},
            {"iata": "BER", "name": "Berlin Brandenburg", "city": "Berlin", "country": "DE", "lat": 52.3514, "lon": 13.5133},
            {"iata": "MAD", "name": "Adolfo Suárez Madrid–Barajas", "city": "Madrid", "country": "ES", "lat": 40.4719, "lon": -3.5626},
            {"iata": "BCN", "name": "Josep Tarradellas Barcelona–El Prat", "city": "Barcelona", "country": "ES", "lat": 41.2974, "lon": 2.0833},
            {"iata": "FCO", "name": "Leonardo da Vinci–Fiumicino", "city": "Rome", "country": "IT", "lat": 41.8003, "lon": 12.2389},
            {"iata": "MXP", "name": "Malpensa", "city": "Milan", "country": "IT", "lat": 45.63, "lon": 8.7231},
            {"iata": "VCE", "name": "Venice Marco Polo", "city": "Venice", "country": "IT", "lat": 45.5053, "lon": 12.3519},
            {"iata": "LIS", "name": "Humberto Delgado", "city": "Lisbon", "country": "PT", "lat": 38.7742, "lon": -9.1342},
            {"iata": "OPO", "name": "Francisco Sá Carneiro", "city": "Porto", "country": "PT", "lat": 41.2424, "lon": -8.6786},
            {"iata": "AMS", "name": "Schiphol", "city": "Amsterdam", "country": "NL", "lat": 52.3105, "lon": 4.7683},
            {"iata": "ZRH", "name": "Zurich", "city": "Zurich", "country": "CH", "lat": 47.4581, "lon": 8.5481},
            {"iata": "GVA", "name": "Geneva", "city": "Geneva", "country": "CH", "lat": 46.2381, "lon": 6.1089},
            {"iata": "DUB", "name": "Dublin", "city": "Dublin", "country": "IE", "lat": 53.4214, "lon": -6.27},
            {"iata": "VIE", "name": "Vienna Intl", "city": "Vienna", "country": "AT", "lat": 48.1103, "lon": 16.5697},
            {"iata": "CPH", "name": "Copenhagen", "city": "Copenhagen", "country": "DK", "lat": 55.6179, "lon": 12.656},
            {"iata": "ARN", "name": "Stockholm Arlanda", "city": "Stockholm", "country": "SE", "lat": 59.6519, "lon": 17.9186},
            {"iata": "OSL", "name": "Oslo Gardermoen", "city": "Oslo", "country": "NO", "lat": 60.1939, "lon": 11.1006},
            {"iata": "HEL", "name": "Helsinki-Vantaa", "city": "Helsinki", "country": "FI", "lat": 60.3172, "lon": 24.9633},
            # ASIA / OCEANIA / AFRICA
            {"iata": "DXB", "name": "Dubai Intl", "city": "Dubai", "country": "AE", "lat": 25.2532, "lon": 55.3657},
            {"iata": "AUH", "name": "Abu Dhabi Intl", "city": "Abu Dhabi", "country": "AE", "lat": 24.4331, "lon": 54.6511},
            {"iata": "DOH", "name": "Hamad Intl", "city": "Doha", "country": "QA", "lat": 25.2731, "lon": 51.6081},
            {"iata": "HND", "name": "Haneda", "city": "Tokyo", "country": "JP", "lat": 35.5494, "lon": 139.7797},
            {"iata": "NRT", "name": "Narita Intl", "city": "Tokyo", "country": "JP", "lat": 35.7647, "lon": 140.3864},
            {"iata": "KIX", "name": "Kansai Intl", "city": "Osaka", "country": "JP", "lat": 34.4347, "lon": 135.2444},
            {"iata": "ICN", "name": "Incheon Intl", "city": "Seoul", "country": "KR", "lat": 37.4691, "lon": 126.4506},
            {"iata": "SIN", "name": "Changi", "city": "Singapore", "country": "SG", "lat": 1.3644, "lon": 103.9915},
            {"iata": "HKG", "name": "Hong Kong Intl", "city": "Hong Kong", "country": "HK", "lat": 22.3089, "lon": 113.9141},
            {"iata": "PEK", "name": "Beijing Capital Intl", "city": "Beijing", "country": "CN", "lat": 40.08, "lon": 116.5844},
            {"iata": "PVG", "name": "Shanghai Pudong Intl", "city": "Shanghai", "country": "CN", "lat": 31.1444, "lon": 121.8083},
            {"iata": "BKK", "name": "Suvarnabhumi", "city": "Bangkok", "country": "TH", "lat": 13.6925, "lon": 100.75},
            {"iata": "SYD", "name": "Sydney Kingsford Smith", "city": "Sydney", "country": "AU", "lat": -33.9461, "lon": 151.1772},
            {"iata": "MEL", "name": "Melbourne", "city": "Melbourne", "country": "AU", "lat": -37.6733, "lon": 144.8433},
            {"iata": "AKL", "name": "Auckland", "city": "Auckland", "country": "NZ", "lat": -37.0081, "lon": 174.7917},
            {"iata": "JNB", "name": "O. R. Tambo Intl", "city": "Johannesburg", "country": "ZA", "lat": -26.1392, "lon": 28.246},
            {"iata": "CPT", "name": "Cape Town Intl", "city": "Cape Town", "country": "ZA", "lat": -33.9715, "lon": 18.6021},
            {"iata": "DEL", "name": "Indira Gandhi Intl", "city": "Delhi", "country": "IN", "lat": 28.5665, "lon": 77.1031},
            {"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj Intl", "city": "Mumbai", "country": "IN", "lat": 19.0886, "lon": 72.8681},
        ]
        
        for item in raw_data:
            info = AirportInfo(**item)
            self.airports[info.iata] = info
            self.search_index.append(info)
            
        logger.info(f"LocationService initialized with {len(self.airports)} airports.")

    def search(self, query: str, limit: int = 10) -> List[AirportInfo]:
        """
        Performs a multi-criteria search (IATA, City, Name) with priority.
        """
        if not query:
            return []
            
        q = query.strip().upper()
        results = []
        
        # 1. Exact IATA match
        if q in self.airports:
            results.append(self.airports[q])
            
        # 2. Starts with IATA (if query is short)
        if len(q) < 3:
            for iata, info in self.airports.items():
                if info not in results and iata.startswith(q):
                    results.append(info)
        
        # 3. City or Name search
        # Using a simple but effective substring match for city and name
        q_lower = query.strip().lower()
        for info in self.search_index:
            if info in results:
                continue
                
            if q_lower in info.city.lower() or q_lower in info.name.lower():
                results.append(info)
                
            if len(results) >= limit:
                break
                
        return results[:limit]

    def resolve_iata(self, text: str) -> str:
        """
        Resolves string input to an IATA code. 
        Tries IATA lookup first, then city lookup, then defaults to upper(text).
        """
        t = text.strip()
        
        # Is it already an IATA in our DB?
        if t.upper() in self.airports:
            return t.upper()
            
        # Is it a city name in our DB?
        for info in self.search_index:
            if info.city.lower() == t.lower():
                return info.iata
                
        # Fallback to pure uppercase if it looks like an IATA
        if len(t) == 3 and t.isalpha():
            return t.upper()
            
        return t # Just return as is for downstream logic (e.g. ground segments)

    def get_coords(self, iata: str) -> Optional[tuple]:
        """Returns (lat, lon) for an IATA."""
        info = self.airports.get(iata.upper())
        if info:
            return (info.lat, info.lon)
        return None

def get_location_service() -> LocationService:
    return LocationService()
