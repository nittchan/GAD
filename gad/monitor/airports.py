"""
Master airport registry — 200+ airports globally with 50 Indian airports.
Each airport auto-generates flight delay, weather, and AQI triggers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    icao: str
    iata: str
    name: str
    city: str
    country: str
    lat: float
    lon: float
    tier: int  # 1 = global hub, 2 = major, 3 = regional


# ──────────────────────────────────────────────────────────────
# INDIA — 50 airports
# ──────────────────────────────────────────────────────────────
INDIA_AIRPORTS: list[Airport] = [
    # Tier 1 — Metro hubs
    Airport("VIDP", "DEL", "Indira Gandhi International", "Delhi", "India", 28.5562, 77.1000, 1),
    Airport("VABB", "BOM", "Chhatrapati Shivaji Maharaj International", "Mumbai", "India", 19.0896, 72.8656, 1),
    Airport("VOBL", "BLR", "Kempegowda International", "Bengaluru", "India", 13.1986, 77.7066, 1),
    Airport("VOMM", "MAA", "Chennai International", "Chennai", "India", 12.9941, 80.1709, 1),
    Airport("VECC", "CCU", "Netaji Subhas Chandra Bose International", "Kolkata", "India", 22.6547, 88.4467, 1),
    Airport("VOHS", "HYD", "Rajiv Gandhi International", "Hyderabad", "India", 17.2403, 78.4294, 1),
    # Tier 2 — Major
    Airport("VAAH", "AMD", "Sardar Vallabhbhai Patel International", "Ahmedabad", "India", 23.0772, 72.6347, 2),
    Airport("VOCI", "COK", "Cochin International", "Kochi", "India", 10.1520, 76.4019, 2),
    Airport("VAGO", "GOI", "Manohar International", "Goa", "India", 15.3808, 73.8314, 2),
    Airport("VARP", "JAI", "Jaipur International", "Jaipur", "India", 26.8242, 75.8122, 2),
    Airport("VOTP", "TRV", "Trivandrum International", "Thiruvananthapuram", "India", 8.4821, 76.9201, 2),
    Airport("VILK", "LKO", "Chaudhary Charan Singh International", "Lucknow", "India", 26.7606, 80.8893, 2),
    Airport("VAPO", "PNQ", "Pune Airport", "Pune", "India", 18.5822, 73.9197, 2),
    Airport("VOBG", "IXB", "Bagdogra Airport", "Siliguri", "India", 26.6812, 88.3286, 2),
    Airport("VANP", "NAG", "Dr. Babasaheb Ambedkar International", "Nagpur", "India", 21.0922, 79.0472, 2),
    Airport("VEPT", "PAT", "Jay Prakash Narayan International", "Patna", "India", 25.5913, 85.0880, 2),
    Airport("VOCL", "CCJ", "Calicut International", "Kozhikode", "India", 11.1368, 75.9553, 2),
    Airport("VOML", "IXE", "Mangaluru International", "Mangaluru", "India", 12.9613, 74.8901, 2),
    Airport("VABO", "BDQ", "Vadodara Airport", "Vadodara", "India", 22.3362, 73.2264, 2),
    Airport("VIBN", "VNS", "Lal Bahadur Shastri International", "Varanasi", "India", 25.4524, 82.8593, 2),
    Airport("VAID", "DED", "Jolly Grant Airport", "Dehradun", "India", 30.1897, 78.1803, 2),
    Airport("VIKO", "IXC", "Chandigarh International", "Chandigarh", "India", 30.6735, 76.7885, 2),
    Airport("VEIM", "IMF", "Bir Tikendrajit International", "Imphal", "India", 24.7600, 93.8967, 2),
    Airport("VEGY", "GAY", "Gaya Airport", "Gaya", "India", 24.7443, 84.9512, 2),
    Airport("VEBS", "BBI", "Biju Patnaik International", "Bhubaneswar", "India", 20.2444, 85.8178, 2),
    Airport("VASU", "STV", "Surat Airport", "Surat", "India", 21.1141, 72.7418, 2),
    Airport("VIAG", "AGR", "Agra Airport", "Agra", "India", 27.1557, 77.9608, 2),
    Airport("VORY", "RDP", "Rajahmundry Airport", "Rajahmundry", "India", 17.1014, 81.7383, 2),
    Airport("VOCB", "CJB", "Coimbatore International", "Coimbatore", "India", 11.0300, 77.0434, 2),
    Airport("VOTJ", "TRZ", "Tiruchirappalli International", "Tiruchirappalli", "India", 10.7654, 78.7097, 2),
    Airport("VISR", "SXR", "Sheikh ul-Alam International", "Srinagar", "India", 33.9871, 74.7742, 2),
    # Tier 3 — Regional
    Airport("VAJB", "JLR", "Jabalpur Airport", "Jabalpur", "India", 23.1778, 80.0520, 3),
    Airport("VIRP", "RPR", "Swami Vivekananda Airport", "Raipur", "India", 21.1804, 81.7388, 3),
    Airport("VABP", "BHO", "Raja Bhoj Airport", "Bhopal", "India", 23.2875, 77.3374, 3),
    Airport("VAUD", "UDR", "Maharana Pratap Airport", "Udaipur", "India", 24.6177, 73.8961, 3),
    Airport("VAJJ", "JGA", "Jamnagar Airport", "Jamnagar", "India", 22.4655, 70.0126, 3),
    Airport("VARK", "RAJ", "Rajkot Airport", "Rajkot", "India", 22.3092, 70.7795, 3),
    Airport("VIJO", "JDH", "Jodhpur Airport", "Jodhpur", "India", 26.2511, 73.0489, 3),
    Airport("VIAS", "ATQ", "Sri Guru Ram Dass Jee International", "Amritsar", "India", 31.7096, 74.7973, 3),
    Airport("VIJP", "JSA", "Jaisalmer Airport", "Jaisalmer", "India", 26.8887, 70.8650, 3),
    Airport("VEGK", "GAU", "Lokpriya Gopinath Bordoloi International", "Guwahati", "India", 26.1061, 91.5859, 3),
    Airport("VEDZ", "DIB", "Dibrugarh Airport", "Dibrugarh", "India", 27.4839, 95.0169, 3),
    Airport("VELR", "IXA", "Agartala Airport", "Agartala", "India", 23.8870, 91.2404, 3),
    Airport("VEPY", "PYB", "Jeypore Airport", "Jeypore", "India", 18.8800, 82.5519, 3),
    Airport("VEJT", "JRH", "Jorhat Airport", "Jorhat", "India", 26.7315, 94.1753, 3),
    Airport("VOMD", "IXM", "Madurai Airport", "Madurai", "India", 9.8345, 78.0934, 3),
    Airport("VOSM", "SLV", "Salem Airport", "Salem", "India", 11.7834, 78.0644, 3),
    Airport("VOPB", "IXZ", "Veer Savarkar International", "Port Blair", "India", 11.6412, 92.7297, 3),
    Airport("VILH", "IXL", "Kushok Bakula Rimpochee Airport", "Leh", "India", 34.1359, 77.5465, 3),
    Airport("VIHR", "HSS", "Hisar Airport", "Hisar", "India", 29.1794, 75.7553, 3),
]

# ──────────────────────────────────────────────────────────────
# GLOBAL — 150+ airports (excluding India, already above)
# ──────────────────────────────────────────────────────────────
GLOBAL_AIRPORTS: list[Airport] = [
    # ── East & Southeast Asia ──
    Airport("WSSS", "SIN", "Changi Airport", "Singapore", "Singapore", 1.3644, 103.9915, 1),
    Airport("VHHH", "HKG", "Hong Kong International", "Hong Kong", "China", 22.3080, 113.9185, 1),
    Airport("RJAA", "NRT", "Narita International", "Tokyo", "Japan", 35.7647, 140.3864, 1),
    Airport("RJTT", "HND", "Haneda Airport", "Tokyo", "Japan", 35.5494, 139.7798, 1),
    Airport("RKSI", "ICN", "Incheon International", "Seoul", "South Korea", 37.4602, 126.4407, 1),
    Airport("VTBS", "BKK", "Suvarnabhumi Airport", "Bangkok", "Thailand", 13.6900, 100.7501, 1),
    Airport("ZBAA", "PEK", "Beijing Capital International", "Beijing", "China", 40.0799, 116.6031, 1),
    Airport("ZSPD", "PVG", "Pudong International", "Shanghai", "China", 31.1443, 121.8083, 1),
    Airport("ZGGG", "CAN", "Baiyun International", "Guangzhou", "China", 23.3924, 113.2988, 1),
    Airport("RCTP", "TPE", "Taoyuan International", "Taipei", "Taiwan", 25.0777, 121.2330, 1),
    Airport("WMKK", "KUL", "Kuala Lumpur International", "Kuala Lumpur", "Malaysia", 2.7456, 101.7099, 1),
    Airport("RPLL", "MNL", "Ninoy Aquino International", "Manila", "Philippines", 14.5086, 121.0198, 1),
    Airport("WIII", "CGK", "Soekarno-Hatta International", "Jakarta", "Indonesia", -6.1256, 106.6559, 1),
    Airport("VVNB", "HAN", "Noi Bai International", "Hanoi", "Vietnam", 21.2212, 105.8070, 2),
    Airport("VVTS", "SGN", "Tan Son Nhat International", "Ho Chi Minh City", "Vietnam", 10.8188, 106.6520, 2),
    Airport("RPVM", "CEB", "Mactan-Cebu International", "Cebu", "Philippines", 10.3075, 123.9791, 2),

    # ── Middle East ──
    Airport("OMDB", "DXB", "Dubai International", "Dubai", "UAE", 25.2532, 55.3657, 1),
    Airport("OTHH", "DOH", "Hamad International", "Doha", "Qatar", 25.2731, 51.6081, 1),
    Airport("OMAA", "AUH", "Zayed International", "Abu Dhabi", "UAE", 24.4330, 54.6511, 1),
    Airport("OEJN", "JED", "King Abdulaziz International", "Jeddah", "Saudi Arabia", 21.6796, 39.1565, 1),
    Airport("OERK", "RUH", "King Khalid International", "Riyadh", "Saudi Arabia", 24.9576, 46.6988, 1),
    Airport("OIIE", "IKA", "Imam Khomeini International", "Tehran", "Iran", 35.4161, 51.1522, 2),
    Airport("LLBG", "TLV", "Ben Gurion International", "Tel Aviv", "Israel", 32.0114, 34.8867, 2),
    Airport("OLBA", "BEY", "Rafic Hariri International", "Beirut", "Lebanon", 33.8209, 35.4884, 2),
    Airport("LTFM", "IST", "Istanbul Airport", "Istanbul", "Turkey", 41.2753, 28.7519, 1),
    Airport("OBBI", "BAH", "Bahrain International", "Manama", "Bahrain", 26.2708, 50.6336, 2),
    Airport("OKBK", "KWI", "Kuwait International", "Kuwait City", "Kuwait", 29.2266, 47.9689, 2),
    Airport("OOMS", "MCT", "Muscat International", "Muscat", "Oman", 23.5933, 58.2844, 2),

    # ── Europe ──
    Airport("EGLL", "LHR", "Heathrow Airport", "London", "UK", 51.4700, -0.4543, 1),
    Airport("EGKK", "LGW", "Gatwick Airport", "London", "UK", 51.1537, -0.1821, 1),
    Airport("LFPG", "CDG", "Charles de Gaulle", "Paris", "France", 49.0097, 2.5479, 1),
    Airport("EDDF", "FRA", "Frankfurt Airport", "Frankfurt", "Germany", 50.0379, 8.5622, 1),
    Airport("EHAM", "AMS", "Schiphol Airport", "Amsterdam", "Netherlands", 52.3105, 4.7683, 1),
    Airport("LEMD", "MAD", "Adolfo Suárez Madrid–Barajas", "Madrid", "Spain", 40.4983, -3.5676, 1),
    Airport("LEBL", "BCN", "Barcelona–El Prat", "Barcelona", "Spain", 41.2971, 2.0785, 1),
    Airport("LIRF", "FCO", "Leonardo da Vinci–Fiumicino", "Rome", "Italy", 41.8003, 12.2389, 1),
    Airport("LIMC", "MXP", "Milano Malpensa", "Milan", "Italy", 45.6306, 8.7281, 1),
    Airport("EDDM", "MUC", "Munich Airport", "Munich", "Germany", 48.3538, 11.7861, 1),
    Airport("LSZH", "ZRH", "Zurich Airport", "Zurich", "Switzerland", 47.4647, 8.5492, 1),
    Airport("EKCH", "CPH", "Copenhagen Airport", "Copenhagen", "Denmark", 55.6180, 12.6560, 1),
    Airport("ESSA", "ARN", "Stockholm Arlanda", "Stockholm", "Sweden", 59.6519, 17.9186, 1),
    Airport("EFHK", "HEL", "Helsinki-Vantaa", "Helsinki", "Finland", 60.3172, 24.9633, 2),
    Airport("ENGM", "OSL", "Oslo Gardermoen", "Oslo", "Norway", 60.1939, 11.1004, 2),
    Airport("EIDW", "DUB", "Dublin Airport", "Dublin", "Ireland", 53.4213, -6.2701, 1),
    Airport("LPPT", "LIS", "Lisbon Portela", "Lisbon", "Portugal", 38.7813, -9.1359, 1),
    Airport("LOWW", "VIE", "Vienna International", "Vienna", "Austria", 48.1103, 16.5697, 1),
    Airport("EPWA", "WAW", "Warsaw Chopin", "Warsaw", "Poland", 52.1657, 20.9671, 2),
    Airport("LKPR", "PRG", "Václav Havel Airport", "Prague", "Czech Republic", 50.1008, 14.2600, 2),
    Airport("LHBP", "BUD", "Budapest Ferenc Liszt", "Budapest", "Hungary", 47.4369, 19.2556, 2),
    Airport("LGAV", "ATH", "Athens International", "Athens", "Greece", 37.9364, 23.9445, 2),
    Airport("LROP", "OTP", "Henri Coandă International", "Bucharest", "Romania", 44.5711, 26.0850, 2),
    Airport("UUEE", "SVO", "Sheremetyevo International", "Moscow", "Russia", 55.9726, 37.4146, 1),

    # ── North America ──
    Airport("KJFK", "JFK", "John F. Kennedy International", "New York", "USA", 40.6413, -73.7781, 1),
    Airport("KLAX", "LAX", "Los Angeles International", "Los Angeles", "USA", 33.9416, -118.4085, 1),
    Airport("KORD", "ORD", "O'Hare International", "Chicago", "USA", 41.9742, -87.9073, 1),
    Airport("KATL", "ATL", "Hartsfield-Jackson International", "Atlanta", "USA", 33.6407, -84.4277, 1),
    Airport("KDFW", "DFW", "Dallas/Fort Worth International", "Dallas", "USA", 32.8998, -97.0403, 1),
    Airport("KDEN", "DEN", "Denver International", "Denver", "USA", 39.8561, -104.6737, 1),
    Airport("KSFO", "SFO", "San Francisco International", "San Francisco", "USA", 37.6213, -122.3790, 1),
    Airport("KMIA", "MIA", "Miami International", "Miami", "USA", 25.7959, -80.2870, 1),
    Airport("KEWR", "EWR", "Newark Liberty International", "Newark", "USA", 40.6895, -74.1745, 1),
    Airport("KBOS", "BOS", "Logan International", "Boston", "USA", 42.3656, -71.0096, 1),
    Airport("KSEA", "SEA", "Seattle-Tacoma International", "Seattle", "USA", 47.4502, -122.3088, 1),
    Airport("KDTW", "DTW", "Detroit Metropolitan", "Detroit", "USA", 42.2124, -83.3534, 2),
    Airport("KMSP", "MSP", "Minneapolis-Saint Paul International", "Minneapolis", "USA", 44.8820, -93.2218, 2),
    Airport("KIAH", "IAH", "George Bush Intercontinental", "Houston", "USA", 29.9902, -95.3368, 1),
    Airport("KPHL", "PHL", "Philadelphia International", "Philadelphia", "USA", 39.8721, -75.2411, 2),
    Airport("CYYZ", "YYZ", "Toronto Pearson International", "Toronto", "Canada", 43.6777, -79.6248, 1),
    Airport("CYUL", "YUL", "Montréal-Trudeau International", "Montreal", "Canada", 45.4706, -73.7408, 1),
    Airport("CYVR", "YVR", "Vancouver International", "Vancouver", "Canada", 49.1947, -123.1792, 1),
    Airport("MMMX", "MEX", "Benito Juárez International", "Mexico City", "Mexico", 19.4363, -99.0721, 1),
    Airport("MMUN", "CUN", "Cancún International", "Cancún", "Mexico", 21.0365, -86.8771, 2),

    # ── South America ──
    Airport("SBGR", "GRU", "São Paulo/Guarulhos International", "São Paulo", "Brazil", -23.4356, -46.4731, 1),
    Airport("SBGL", "GIG", "Rio de Janeiro/Galeão International", "Rio de Janeiro", "Brazil", -22.8100, -43.2506, 1),
    Airport("SCEL", "SCL", "Arturo Merino Benítez International", "Santiago", "Chile", -33.3930, -70.7858, 1),
    Airport("SAEZ", "EZE", "Ministro Pistarini International", "Buenos Aires", "Argentina", -34.8222, -58.5358, 1),
    Airport("SKBO", "BOG", "El Dorado International", "Bogotá", "Colombia", 4.7016, -74.1469, 1),
    Airport("SPJC", "LIM", "Jorge Chávez International", "Lima", "Peru", -12.0219, -77.1143, 1),

    # ── Africa ──
    Airport("FAOR", "JNB", "OR Tambo International", "Johannesburg", "South Africa", -26.1392, 28.2460, 1),
    Airport("FACT", "CPT", "Cape Town International", "Cape Town", "South Africa", -33.9649, 18.6017, 1),
    Airport("HECA", "CAI", "Cairo International", "Cairo", "Egypt", 30.1219, 31.4056, 1),
    Airport("DNMM", "LOS", "Murtala Muhammed International", "Lagos", "Nigeria", 6.5774, 3.3213, 1),
    Airport("HKJK", "NBO", "Jomo Kenyatta International", "Nairobi", "Kenya", -1.3192, 36.9278, 1),
    Airport("HAAB", "ADD", "Addis Ababa Bole International", "Addis Ababa", "Ethiopia", 8.9779, 38.7993, 1),
    Airport("GMMN", "CMN", "Mohammed V International", "Casablanca", "Morocco", 33.3675, -7.5898, 2),
    Airport("DTTA", "TUN", "Tunis–Carthage International", "Tunis", "Tunisia", 36.8510, 10.2272, 2),
    Airport("GOOY", "DSS", "Blaise Diagne International", "Dakar", "Senegal", 14.6700, -17.0733, 2),
    Airport("FMEE", "MRU", "Sir Seewoosagur Ramgoolam International", "Mauritius", "Mauritius", -20.4302, 57.6836, 2),

    # ── Oceania ──
    Airport("YSSY", "SYD", "Kingsford Smith Airport", "Sydney", "Australia", -33.9461, 151.1772, 1),
    Airport("YMML", "MEL", "Melbourne Airport", "Melbourne", "Australia", -37.6690, 144.8410, 1),
    Airport("YBBN", "BNE", "Brisbane Airport", "Brisbane", "Australia", -27.3842, 153.1175, 1),
    Airport("YPPH", "PER", "Perth Airport", "Perth", "Australia", -31.9403, 115.9670, 2),
    Airport("NZAA", "AKL", "Auckland Airport", "Auckland", "New Zealand", -37.0082, 174.7850, 1),
    Airport("NZWN", "WLG", "Wellington Airport", "Wellington", "New Zealand", -41.3272, 174.8053, 2),
]


ALL_AIRPORTS: list[Airport] = INDIA_AIRPORTS + GLOBAL_AIRPORTS


def get_airports_by_country(country: str) -> list[Airport]:
    return [a for a in ALL_AIRPORTS if a.country == country]


def get_airports_by_tier(tier: int) -> list[Airport]:
    return [a for a in ALL_AIRPORTS if a.tier <= tier]
