"""Static reference data for the simulator.

Accented names (José, Zoë) and the é/™ in some product names are intentional: they surface
encoding bugs (cp1252 vs UTF-8). Brands and model names are illustrative; the retailer itself is fictional.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MALE_FIRST_NAMES = (
    "James", "Michael", "Robert", "John", "David", "William", "Richard", "Joseph", "Thomas", "Christopher",
    "Daniel", "Matthew", "Anthony", "Mark", "Steven", "Andrew", "Kevin", "Brian", "José", "Andrés",
)
FEMALE_FIRST_NAMES = (
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Emily", "Ashley", "Michelle", "Amanda", "Megan", "Rachel", "María", "Sofía", "Zoë", "Renée",
)
SURNAMES = (
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernández", "López", "González", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Pérez", "Thompson", "White", "Sullivan", "O'Brien", "Murphy", "Nguyen", "Peña", "Muñoz",
)
EMAIL_DOMAINS = (
    ("gmail.com", 0.40), ("yahoo.com", 0.14), ("icloud.com", 0.10), ("outlook.com", 0.10),
    ("hotmail.com", 0.08), ("comcast.net", 0.08), ("aol.com", 0.04), ("verizon.net", 0.03), ("me.com", 0.03),
)
COMPANY_WORDS = ("Tech", "Computers", "Systems", "Services", "Logistics", "Media", "Design", "Office")
COMPANY_FORMS = ("LLC", "Inc.", "Corp.", "Co.", "LLP", "")
AREA_CODES = ("617", "508", "781", "978", "413", "401", "860", "203", "475", "603", "207", "802")

SALES_TAX_RATES = {  # statewide rates (none of these states has local sales taxes)
    "MA": 0.0625, "CT": 0.0635, "RI": 0.07, "NH": 0.0, "ME": 0.055, "VT": 0.06,
}
HOME_STATE = "MA"


@dataclass(frozen=True)
class City:
    name: str
    state: str
    zip_prefix: str  # first three digits of the ZIP code - New England ZIPs start with 0
    latitude: float
    longitude: float
    weight: float  # relative share of customers


CITIES = (
    City("Boston", "MA", "021", 42.3601, -71.0589, 1.86),
    City("Worcester", "MA", "016", 42.2626, -71.8023, 0.60),
    City("Providence", "RI", "029", 41.8240, -71.4128, 0.55),
    City("Hartford", "CT", "061", 41.7658, -72.6734, 0.50),
    City("Springfield", "MA", "011", 42.1015, -72.5898, 0.45),
    City("New Haven", "CT", "065", 41.3083, -72.9279, 0.45),
    City("Bridgeport", "CT", "066", 41.1792, -73.1894, 0.42),
    City("Stamford", "CT", "069", 41.0534, -73.5387, 0.40),
    City("Manchester", "NH", "031", 42.9956, -71.4548, 0.35),
    City("Cambridge", "MA", "021", 42.3736, -71.1097, 0.33),
    City("Lowell", "MA", "018", 42.6334, -71.3162, 0.32),
    City("Brockton", "MA", "023", 42.0834, -71.0184, 0.30),
    City("Nashua", "NH", "030", 42.7654, -71.4676, 0.30),
    City("Quincy", "MA", "021", 42.2529, -71.0023, 0.28),
    City("New Bedford", "MA", "027", 41.6362, -70.9342, 0.28),
    City("Portland", "ME", "041", 43.6591, -70.2568, 0.25),
    City("Waterbury", "CT", "067", 41.5582, -73.0515, 0.25),
    City("Framingham", "MA", "017", 42.2793, -71.4162, 0.22),
    City("Warwick", "RI", "028", 41.7001, -71.4162, 0.22),
    City("Norwalk", "CT", "068", 41.1177, -73.4082, 0.20),
    City("Portsmouth", "NH", "038", 43.0718, -70.7626, 0.15),
    City("Burlington", "VT", "054", 44.4759, -73.2121, 0.15),
    City("Concord", "NH", "033", 43.2081, -71.5376, 0.13),
    City("Pittsfield", "MA", "012", 42.4501, -73.2454, 0.10),
    City("Hyannis", "MA", "026", 41.6525, -70.2881, 0.10),
    City("Bangor", "ME", "044", 44.8012, -68.7778, 0.10),
)
CITY_BY_NAME = {city.name: city for city in CITIES}


@dataclass(frozen=True)
class StoreSpec:
    code: str
    name: str
    city: str
    store_format: str  # FLAGSHIP | STANDARD | OUTLET
    opened: date
    closed: date | None = None


STORES = (
    StoreSpec("BOS-01", "Boston Downtown", "Boston", "FLAGSHIP", date(2014, 3, 15)),
    StoreSpec("BOS-02", "Boston Back Bay", "Boston", "STANDARD", date(2017, 9, 2)),
    StoreSpec("BOS-03", "Boston Dorchester Outlet", "Boston", "OUTLET", date(2021, 5, 8)),
    StoreSpec("HFD-01", "Hartford West Farms", "Hartford", "FLAGSHIP", date(2015, 6, 20)),
    StoreSpec("HFD-02", "Hartford Downtown", "Hartford", "STANDARD", date(2019, 11, 16)),
    StoreSpec("PVD-01", "Providence Place", "Providence", "FLAGSHIP", date(2015, 10, 10)),
    StoreSpec("WOR-01", "Worcester Store", "Worcester", "STANDARD", date(2016, 4, 23)),
    StoreSpec("NHV-01", "New Haven Store", "New Haven", "STANDARD", date(2016, 8, 27)),
    StoreSpec("SPR-01", "Springfield Store", "Springfield", "STANDARD", date(2017, 3, 11)),
    StoreSpec("BDR-01", "Bridgeport Store", "Bridgeport", "STANDARD", date(2017, 10, 14)),
    StoreSpec("STM-01", "Stamford Store", "Stamford", "STANDARD", date(2018, 5, 19)),
    StoreSpec("MHT-01", "Manchester Store", "Manchester", "STANDARD", date(2018, 9, 22)),
    StoreSpec("LOW-01", "Lowell Store", "Lowell", "STANDARD", date(2019, 2, 16)),
    StoreSpec("PWM-01", "Portland Store", "Portland", "STANDARD", date(2019, 6, 29)),
    StoreSpec("BTV-01", "Burlington Store", "Burlington", "STANDARD", date(2020, 9, 12)),
    StoreSpec("NBD-01", "New Bedford Store", "New Bedford", "STANDARD", date(2021, 3, 20)),
    StoreSpec("PSF-01", "Pittsfield Store", "Pittsfield", "STANDARD", date(2021, 10, 9), closed=date(2026, 1, 31)),
    StoreSpec("WWK-01", "Warwick Store", "Warwick", "STANDARD", date(2022, 4, 23)),
    StoreSpec("NSH-01", "Nashua Store", "Nashua", "STANDARD", date(2025, 5, 17)),
    StoreSpec("WTB-01", "Waterbury Store", "Waterbury", "STANDARD", date(2026, 3, 14)),
)


@dataclass(frozen=True)
class SiteSpec:
    code: str
    name: str
    city: str
    state: str
    postal_code: str
    latitude: float
    longitude: float
    opened: date


DISTRIBUTION_CENTERS = (
    SiteSpec("DC-01", "Distribution Center Westborough", "Westborough", "MA", "01581", 42.2695, -71.6162,
             date(2016, 1, 4)),
    SiteSpec("DC-02", "Distribution Center Windsor", "Windsor", "CT", "06095", 41.8526, -72.6437, date(2022, 6, 1)),
)
ONLINE_LOCATION_ID = 99  # the classic "store 99 = e-commerce" convention

# Planted truths: patterns the analytics layer (and Genie) should be able to find.
FRAUD_STORE, FRAUD_CASHIER = "SPR-01", "C7311"  # one cashier voids ~12x more lines
CANNIBALIZED_STORE, NEW_NEIGHBOUR_STORE = "LOW-01", "NSH-01"  # Nashua opening takes ~18% of Lowell traffic


@dataclass(frozen=True)
class Leaf:
    code: str
    name: str
    product_type: str  # the noun in the product name
    models: tuple[tuple[str, tuple[str, ...]], ...]  # (brand, model lines)
    specs: tuple[str, ...]
    median_price: float  # USD at launch, before sales tax
    weight_lb: tuple[float, float]
    warranty_months: int
    share: float  # share of the catalogue
    store_share: float  # probability that a product is in the store assortment
    return_factor: float = 1.0
    energy_label: bool = False  # eligible for ENERGY STAR


_LEAVES = (
    Leaf("CMP-NB-GAM", "Gaming Laptops", "Laptop",
         (("ASUS", ("TUF Gaming A15", "ROG Strix G16")), ("MSI", ("Katana 15", "Cyborg 15")),
          ("Lenovo", ("Legion 5", "LOQ 15")), ("Acer", ("Nitro V 15", "Predator Helios Neo 16")),
          ("HP", ("Victus 16", "Omen 16"))),
         ("R7-8845HS/16GB/1TB/RTX4060", "i7-13620H/16GB/512GB/RTX4050", "R5-7535HS/16GB/512GB/RTX3050",
          "i9-14900HX/32GB/1TB/RTX4070"),
         1249, (4.6, 6.4), 12, 0.045, 0.6, 1.1),
    Leaf("CMP-NB-BUS", "Business Laptops", "Laptop",
         (("Lenovo", ("ThinkPad E14", "ThinkPad T14")), ("Dell", ("Latitude 5440", "Vostro 3530")),
          ("HP", ("ProBook 450", "EliteBook 840"))),
         ("i5-1335U/16GB/512GB/Win11Pro", "i7-1355U/32GB/1TB/Win11Pro", "R5-7530U/16GB/512GB/Win11Pro"),
         1099, (3.1, 4.2), 36, 0.035, 0.4, 0.8),
    Leaf("CMP-NB-ULT", "Ultrabooks", "Laptop",
         (("Apple", ("MacBook Air 13 M3", "MacBook Air 15 M3", "MacBook Pro 14 M4")),
          ("ASUS", ("Zenbook 14 OLED", "Vivobook S 15")), ("Lenovo", ("Yoga Slim 7",)), ("Dell", ("XPS 13",))),
         ("16GB/512GB", "8GB/256GB", "24GB/1TB", "32GB/1TB"),
         1349, (2.4, 3.5), 12, 0.03, 0.7, 0.9),
    Leaf("CMP-PC-GAM", "Gaming Desktops", "Desktop",
         (("NovaPC", ("Hero", "Elite", "Ultra")),),
         ("R5-7600/32GB/1TB/RTX4060", "i5-14400F/16GB/1TB/RX7600", "R7-7800X3D/32GB/2TB/RTX4070S"),
         1499, (17.6, 30.9), 12, 0.012, 0.3, 0.9),
    Leaf("CMP-PC-MIN", "Mini PCs", "Mini PC",
         (("Lenovo", ("ThinkCentre M70q Tiny",)), ("Apple", ("Mac mini M4",)), ("ASUS", ("NUC 14 Pro",))),
         ("16GB/512GB", "8GB/256GB", "32GB/1TB"),
         699, (1.3, 3.1), 12, 0.01, 0.3),
    Leaf("PRT-GPU-NV", "NVIDIA Graphics Cards", "Graphics Card",
         (("ASUS", ("GeForce RTX 4060 Dual", "GeForce RTX 4070 SUPER TUF")),
          ("MSI", ("GeForce RTX 4060 Ventus 2X", "GeForce RTX 5070 Gaming Trio")),
          ("Gigabyte", ("GeForce RTX 4060 Ti Eagle", "GeForce RTX 5080 Aorus Master")),
          ("Palit", ("GeForce RTX 3050 StormX",))),
         ("8GB GDDR6", "12GB GDDR6X", "16GB GDDR7", "8GB GDDR6 OC"),
         549, (1.3, 4.0), 36, 0.04, 0.35),
    Leaf("PRT-GPU-AMD", "AMD Graphics Cards", "Graphics Card",
         (("Sapphire", ("Radeon RX 7600 Pulse", "Radeon RX 7800 XT Nitro+")),
          ("PowerColor", ("Radeon RX 7700 XT Hellhound",)), ("XFX", ("Radeon RX 9070 XT Quicksilver",))),
         ("8GB GDDR6", "12GB GDDR6", "16GB GDDR6"),
         499, (1.5, 3.5), 24, 0.02, 0.3),
    Leaf("PRT-STO-SSD", "SSDs", "SSD",
         (("Samsung", ("990 PRO", "990 EVO")), ("Kingston", ("NV2", "KC3000")), ("WD", ("Black SN850X", "Blue SN580")),
          ("Crucial", ("P3 Plus", "T500"))),
         ("500GB M.2 PCIe NVMe", "1TB M.2 PCIe NVMe", "2TB M.2 PCIe NVMe", "4TB M.2 PCIe NVMe"),
         89, (0.02, 0.11), 60, 0.05, 0.8),
    Leaf("PRT-STO-RAM", "Memory (RAM)", "RAM",
         (("Kingston", ("FURY Beast",)), ("Corsair", ("Vengeance",)), ("TeamGroup", ("T-Force Delta",)),
          ("G.Skill", ("Trident Z5",))),
         ("16GB (2x8GB) 3200MHz CL16", "32GB (2x16GB) 6000MHz CL30", "32GB (2x16GB) 3600MHz CL18",
          "64GB (2x32GB) 6000MHz CL30"),
         79, (0.07, 0.22), 120, 0.03, 0.7),
    Leaf("PRT-CPU-DT", "Desktop Processors", "Processor",
         (("AMD", ("Ryzen 5 7600", "Ryzen 7 7800X3D", "Ryzen 7 9700X")),
          ("Intel", ("Core™ i5-14400F", "Core™ i7-14700K", "Core™ Ultra 7 265K"))),
         ("Boxed", "Tray", "Boxed with Cooler"),
         299, (0.11, 0.88), 36, 0.02, 0.5),
    Leaf("MOB-PHN-AND", "Android Smartphones", "Smartphone",
         (("Samsung", ("Galaxy S25", "Galaxy A56 5G", "Galaxy A16")), ("OnePlus", ("13", "Nord N30 5G")),
          ("Motorola", ("moto g 5G", "edge 2024")), ("Google", ("Pixel 9a", "Pixel 9 Pro"))),
         ("8/256GB Black", "8/128GB Blue", "12/512GB Gray", "6/128GB Green"),
         499, (0.40, 0.51), 12, 0.06, 0.7, 1.2),
    Leaf("MOB-PHN-IOS", "iPhones", "Smartphone",
         (("Apple", ("iPhone 16", "iPhone 16 Pro", "iPhone 16e", "iPhone 17")),),
         ("128GB Black", "256GB White", "512GB Natural Titanium", "128GB Pink"),
         999, (0.37, 0.51), 12, 0.02, 0.8, 0.9),
    Leaf("MOB-SW-SW", "Smartwatches", "Smartwatch",
         (("Apple", ("Watch Series 10", "Watch SE")), ("Samsung", ("Galaxy Watch7", "Galaxy Watch Ultra")),
          ("Garmin", ("Forerunner 265", "Venu 3")), ("Fitbit", ("Charge 6",))),
         ("42mm Black", "44mm Silver", "46mm GPS", "40mm Pink"),
         299, (0.07, 0.18), 12, 0.03, 0.6),
    Leaf("MOB-ACC-CAS", "Phone Cases", "Case",
         (("Spigen", ("Ultra Hybrid", "Rugged Armor")), ("Apple", ("Silicone Case MagSafe",)),
          ("OtterBox", ("Symmetry", "Defender"))),
         ("for iPhone 16", "for Galaxy S25", "for iPhone 16 Pro", "for Pixel 9 Pro"),
         25, (0.04, 0.13), 12, 0.08, 0.9, 1.3),
    Leaf("MOB-ACC-CHG", "Chargers", "Charger",
         (("Baseus", ("GaN5 Pro",)), ("Anker", ("Nano",)), ("Samsung", ("Super Fast Charging",)), ("Ugreen", ("Nexode",))),
         ("65W USB-C", "20W USB-C", "100W 2x USB-C", "45W USB-C"),
         29, (0.11, 0.55), 24, 0.05, 0.9),
    Leaf("MOB-ACC-SCR", "Screen Protectors", "Screen Protector",
         (("Spigen", ("Glas.tR",)), ("OtterBox", ("Glass",)), ("ZAGG", ("InvisibleShield",))),
         ("for iPhone 16", "for Galaxy S25", "for Pixel 9a"),
         15, (0.02, 0.07), 12, 0.05, 0.9, 1.2),
    Leaf("GAM-CON-CON", "Consoles", "Console",
         (("Sony", ("PlayStation 5 Slim", "PlayStation 5 Pro")), ("Microsoft", ("Xbox Series X", "Xbox Series S")),
          ("Nintendo", ("Switch OLED", "Switch 2"))),
         ("1TB", "512GB", "Disc Edition", "Digital Edition"),
         499, (5.5, 9.9), 12, 0.012, 0.9, 0.8),
    Leaf("GAM-CON-GAM", "Video Games", "Video Game",
         (("CD Projekt", ("Cyberpunk 2077", "The Witcher 3: Wild Hunt")), ("EA", ("SPORTS FC 25", "SPORTS FC 26")),
          ("Nintendo", ("Mario Kart World", "Pokémon Legends: Z-A"))),
         ("PS5", "Xbox Series X", "Nintendo Switch", "PC"),
         59, (0.18, 0.33), 12, 0.04, 0.8, 0.6),
    Leaf("GAM-ACC-CTL", "Controllers", "Controller",
         (("Sony", ("DualSense", "DualSense Edge")), ("Microsoft", ("Xbox Wireless Controller",)),
          ("PowerA", ("Enhanced Wired Controller",))),
         ("Black", "White", "Midnight Black", "Cosmic Red"),
         69, (0.55, 0.77), 12, 0.02, 0.9),
    Leaf("PER-MON-GAM", "Gaming Monitors", "Monitor",
         (("LG", ("UltraGear 27GR75Q",)), ("Samsung", ("Odyssey G5",)), ("AOC", ("Q27G3XMN",)),
          ("MSI", ("MAG 274QRF",)), ("ASUS", ("TUF Gaming VG27AQ",))),
         ('27" IPS 165Hz', '27" VA 165Hz', '32" IPS 180Hz', '24" IPS 144Hz'),
         299, (9.9, 16.5), 36, 0.03, 0.4, 1.0, True),
    Leaf("PER-MON-OFF", "Office Monitors", "Monitor",
         (("Dell", ("P2425H",)), ("Philips", ("241V8",)), ("iiyama", ("ProLite XU2493HS",)), ("LG", ("24MR400",))),
         ('24" IPS', '27" IPS', '24" VA'),
         159, (6.6, 12.1), 36, 0.025, 0.4, 1.0, True),
    Leaf("PER-INP-MOU", "Mice", "Mouse",
         (("Logitech", ("G305 Lightspeed", "MX Master 3S", "G502 X")), ("Razer", ("DeathAdder V3",)),
          ("SteelSeries", ("Rival 3",)), ("HyperX", ("Pulsefire Haste",))),
         ("Black", "White", "Wireless"),
         49, (0.13, 0.33), 24, 0.04, 0.9),
    Leaf("PER-INP-KEY", "Keyboards", "Keyboard",
         (("Logitech", ("MX Keys S", "G915 TKL")), ("Razer", ("BlackWidow V4",)), ("SteelSeries", ("Apex 3",)),
          ("HyperX", ("Alloy Origins",)), ("Corsair", ("K70 RGB",))),
         ("US", "US International", "TKL Brown Switch", "Red Switch"),
         89, (1.1, 2.6), 24, 0.03, 0.8),
    Leaf("PER-AUD-HP", "Headphones", "Headphones",
         (("Sony", ("WH-1000XM5", "WH-CH720N")), ("JBL", ("Tune 520BT", "Tune 770NC")),
          ("Apple", ("AirPods 4", "AirPods Pro 2")), ("SteelSeries", ("Arctis Nova 7",)), ("Logitech", ("G435",))),
         ("Black", "White", "Blue"),
         129, (0.11, 0.77), 12, 0.05, 0.9, 1.4),
    Leaf("TVA-TV-LED", "LED TVs", "TV",
         (("Samsung", ("UN55DU7200", "QN65Q80D")), ("LG", ("55UT7000", "65QNED85")),
          ("TCL", ("55Q651G", "65QM751G")), ("Vizio", ("V50M-K04",))),
         ('55" 4K', '65" 4K', '50" 4K', '43" 4K'),
         599, (19.8, 48.5), 12, 0.03, 0.4, 1.0, True),
    Leaf("TVA-TV-OLED", "OLED TVs", "TV",
         (("LG", ("OLED55C4", "OLED65B4")), ("Sony", ("Bravia 8",)), ("Samsung", ("QN55S90D",))),
         ('55" 4K 120Hz', '65" 4K 120Hz', '77" 4K'),
         1599, (30.9, 61.7), 12, 0.015, 0.4, 1.0, True),
    Leaf("TVA-SPK-BT", "Bluetooth Speakers", "Speaker",
         (("JBL", ("Flip 6", "Charge 5", "Go 4")), ("Sony", ("ULT Field 1",)), ("Marshall", ("Emberton III",))),
         ("Black", "Blue", "Red"),
         119, (0.44, 2.2), 12, 0.025, 0.9),
    Leaf("NET-RTR-WIFI", "Routers", "Router",
         (("TP-Link", ("Archer AX55", "Deco X50 (2-pack)")), ("ASUS", ("RT-AX58U", "ZenWiFi XD5")),
          ("Netgear", ("Nighthawk RAX30",))),
         ("Wi-Fi 6", "Wi-Fi 6E", "Wi-Fi 7"),
         129, (0.88, 2.2), 24, 0.025, 0.7),
    Leaf("NET-ACC-CBL", "Cables", "Cable",
         (("Unitek", ("USB-C to USB-C",)), ("Belkin", ("BoostCharge USB-C to Lightning",)),
          ("Cable Matters", ("HDMI 2.1",)), ("Anker", ("PowerLine III",))),
         ("3ft", "6ft", "10ft", "1.5ft"),
         15, (0.07, 0.26), 12, 0.06, 0.95, 0.6),
    Leaf("NET-ACC-USB", "USB Flash Drives", "USB Flash Drive",
         (("SanDisk", ("Ultra Flair",)), ("Kingston", ("DataTraveler Exodia",)), ("PNY", ("Turbo Attaché",)),
          ("Samsung", ("BAR Plus",))),
         ("64GB USB 3.2", "128GB USB 3.2", "256GB USB 3.2", "32GB USB 3.0"),
         15, (0.02, 0.07), 60, 0.04, 0.95),
)
LEAVES = {leaf.code: leaf for leaf in _LEAVES}

CATEGORY_TREE = (  # (code, name, children); level-3 names come from LEAVES
    ("CMP", "Computers & Laptops", (
        ("CMP-NB", "Laptops", ("CMP-NB-GAM", "CMP-NB-BUS", "CMP-NB-ULT")),
        ("CMP-PC", "Desktop Computers", ("CMP-PC-GAM", "CMP-PC-MIN")),
    )),
    ("PRT", "Computer Components", (
        ("PRT-GPU", "Graphics Cards", ("PRT-GPU-NV", "PRT-GPU-AMD")),
        ("PRT-STO", "Memory & Storage", ("PRT-STO-SSD", "PRT-STO-RAM")),
        ("PRT-CPU", "Processors", ("PRT-CPU-DT",)),
    )),
    ("MOB", "Phones & Smartwatches", (
        ("MOB-PHN", "Smartphones", ("MOB-PHN-AND", "MOB-PHN-IOS")),
        ("MOB-SW", "Smartwatches", ("MOB-SW-SW",)),
        ("MOB-ACC", "Phone Accessories", ("MOB-ACC-CAS", "MOB-ACC-CHG", "MOB-ACC-SCR")),
    )),
    ("GAM", "Gaming", (
        ("GAM-CON", "Consoles & Games", ("GAM-CON-CON", "GAM-CON-GAM")),
        ("GAM-ACC", "Gaming Accessories", ("GAM-ACC-CTL",)),
    )),
    ("PER", "Peripherals", (
        ("PER-MON", "Monitors", ("PER-MON-GAM", "PER-MON-OFF")),
        ("PER-INP", "Mice & Keyboards", ("PER-INP-MOU", "PER-INP-KEY")),
        ("PER-AUD", "Headphones & Microphones", ("PER-AUD-HP",)),
    )),
    ("TVA", "TV & Audio", (
        ("TVA-TV", "TVs", ("TVA-TV-LED", "TVA-TV-OLED")),
        ("TVA-SPK", "Speakers", ("TVA-SPK-BT",)),
    )),
    ("NET", "Networking & Accessories", (
        ("NET-RTR", "Networking", ("NET-RTR-WIFI",)),
        ("NET-ACC", "Computer Accessories", ("NET-ACC-CBL", "NET-ACC-USB")),
    )),
)
CATEGORY_RENAMES = {"MOB-SW": (date(2025, 6, 1), "Wearables")}  # SCD2 material

BRAND_VARIANTS = {  # how the same brand gets typed into an ERP over the years
    "ASUS": ("Asus", "ASUSTeK"), "Samsung": ("SAMSUNG", "Samsung Electronics"), "Apple": ("APPLE", "Apple Inc."),
    "Lenovo": ("LENOVO",), "Logitech": ("LOGITECH", "Logitech G"), "WD": ("Western Digital", "WDC"), "Sony": ("SONY",),
    "HP": ("Hewlett-Packard", "HP Inc."), "MSI": ("Micro-Star", "msi"), "LG": ("LG Electronics",),
    "TP-Link": ("TPLINK", "Tp-link"), "Gigabyte": ("GIGABYTE",), "JBL": ("Jbl",), "Kingston": ("KINGSTON",),
}

EAN_PREFIXES = {  # GS1-style prefixes; the US/Canada ones start with 0 -> leading-zero traps in CSV inference
    "ASUS": "471", "MSI": "471", "Acer": "471", "Gigabyte": "471", "PowerColor": "471", "G.Skill": "471",
    "Unitek": "471", "TeamGroup": "471", "Palit": "489", "Sapphire": "489",
    "Apple": "019", "Dell": "088", "HP": "019", "Intel": "073", "AMD": "073", "Microsoft": "088", "Razer": "081",
    "Corsair": "084", "Crucial": "064", "SanDisk": "061", "Kingston": "074", "Google": "081", "Motorola": "084",
    "Netgear": "060", "Garmin": "075", "JBL": "050", "EA": "014", "Nintendo": "045", "XFX": "079",
    "Lenovo": "019", "Anker": "019", "WD": "071", "Fitbit": "081", "OtterBox": "066", "ZAGG": "084",
    "PowerA": "061", "HyperX": "019", "Belkin": "074", "Cable Matters": "085", "PNY": "075", "Vizio": "084",
    "NovaPC": "086", "CD Projekt": "081",
    "Samsung": "880", "LG": "880", "Spigen": "880",
    "OnePlus": "692", "TCL": "693", "Baseus": "695", "Ugreen": "695", "AOC": "693",
    "Sony": "454", "iiyama": "494",
    "Philips": "871", "SteelSeries": "570", "Logitech": "509", "Marshall": "735",
}
