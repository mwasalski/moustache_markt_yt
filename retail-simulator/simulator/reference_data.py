"""Static reference data for the simulator.

Polish diacritics are intentional: they surface encoding bugs (cp1250 vs UTF-8).
Brands and model names are illustrative; the retailer itself is fictional.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MALE_FIRST_NAMES = (
    "Jan", "Piotr", "Krzysztof", "Andrzej", "Tomasz", "Paweł", "Michał", "Marcin", "Jakub", "Mateusz",
    "Łukasz", "Adam", "Kamil", "Szymon", "Wojciech", "Grzegorz", "Dawid", "Bartosz", "Maciej", "Rafał",
)
FEMALE_FIRST_NAMES = (
    "Anna", "Maria", "Katarzyna", "Małgorzata", "Agnieszka", "Barbara", "Ewa", "Magdalena", "Joanna", "Aleksandra",
    "Zofia", "Natalia", "Julia", "Monika", "Karolina", "Dorota", "Paulina", "Weronika", "Justyna", "Beata",
)
SURNAMES = (  # (male form, female form)
    ("Nowak", "Nowak"), ("Kowalski", "Kowalska"), ("Wiśniewski", "Wiśniewska"), ("Wójcik", "Wójcik"),
    ("Kowalczyk", "Kowalczyk"), ("Kamiński", "Kamińska"), ("Lewandowski", "Lewandowska"), ("Zieliński", "Zielińska"),
    ("Szymański", "Szymańska"), ("Woźniak", "Woźniak"), ("Dąbrowski", "Dąbrowska"), ("Kozłowski", "Kozłowska"),
    ("Jankowski", "Jankowska"), ("Mazur", "Mazur"), ("Wojciechowski", "Wojciechowska"), ("Kwiatkowski", "Kwiatkowska"),
    ("Krawczyk", "Krawczyk"), ("Kaczmarek", "Kaczmarek"), ("Piotrowski", "Piotrowska"), ("Grabowski", "Grabowska"),
    ("Zając", "Zając"), ("Pawłowski", "Pawłowska"), ("Michalski", "Michalska"), ("Król", "Król"), ("Wieczorek", "Wieczorek"),
)
EMAIL_DOMAINS = (
    ("gmail.com", 0.35), ("wp.pl", 0.15), ("onet.pl", 0.12), ("o2.pl", 0.10),
    ("interia.pl", 0.10), ("outlook.com", 0.08), ("icloud.com", 0.05), ("op.pl", 0.05),
)
COMPANY_WORDS = ("Tech", "Komputery", "Systemy", "Serwis", "Logistyka", "Media", "Projekt", "Biuro")
COMPANY_FORMS = ("Sp. z o.o.", "S.A.", "s.c.", "Sp. j.", "")


@dataclass(frozen=True)
class City:
    name: str
    voivodeship: str
    postal_prefix: str  # first two digits of the postal code
    latitude: float
    longitude: float
    weight: float  # relative share of customers


CITIES = (
    City("Warszawa", "mazowieckie", "02", 52.2297, 21.0122, 1.86),
    City("Kraków", "małopolskie", "31", 50.0647, 19.9450, 0.80),
    City("Wrocław", "dolnośląskie", "53", 51.1079, 17.0385, 0.67),
    City("Łódź", "łódzkie", "91", 51.7592, 19.4560, 0.65),
    City("Poznań", "wielkopolskie", "61", 52.4064, 16.9252, 0.54),
    City("Gdańsk", "pomorskie", "80", 54.3520, 18.6466, 0.49),
    City("Szczecin", "zachodniopomorskie", "71", 53.4285, 14.5528, 0.39),
    City("Bydgoszcz", "kujawsko-pomorskie", "85", 53.1235, 18.0084, 0.33),
    City("Lublin", "lubelskie", "20", 51.2465, 22.5684, 0.33),
    City("Białystok", "podlaskie", "15", 53.1325, 23.1688, 0.29),
    City("Katowice", "śląskie", "40", 50.2649, 19.0238, 0.28),
    City("Gdynia", "pomorskie", "81", 54.5189, 18.5305, 0.24),
    City("Częstochowa", "śląskie", "42", 50.8118, 19.1203, 0.20),
    City("Radom", "mazowieckie", "26", 51.4027, 21.1471, 0.20),
    City("Rzeszów", "podkarpackie", "35", 50.0412, 21.9991, 0.20),
    City("Toruń", "kujawsko-pomorskie", "87", 53.0138, 18.5984, 0.19),
    City("Kielce", "świętokrzyskie", "25", 50.8661, 20.6286, 0.18),
    City("Olsztyn", "warmińsko-mazurskie", "10", 53.7784, 20.4801, 0.17),
    City("Zielona Góra", "lubuskie", "65", 51.9356, 15.5062, 0.14),
    City("Opole", "opolskie", "45", 50.6751, 17.9213, 0.13),
    City("Płock", "mazowieckie", "09", 52.5463, 19.7065, 0.12),
    City("Tarnów", "małopolskie", "33", 50.0121, 20.9858, 0.11),
    City("Elbląg", "warmińsko-mazurskie", "82", 54.1561, 19.4045, 0.11),
    City("Legnica", "dolnośląskie", "59", 51.2070, 16.1553, 0.10),
    City("Koszalin", "zachodniopomorskie", "75", 54.1944, 16.1722, 0.10),
    City("Siedlce", "mazowieckie", "08", 52.1676, 22.2902, 0.08),
)


@dataclass(frozen=True)
class StoreSpec:
    code: str
    name: str
    city: str
    store_format: str  # FLAGSHIP | STANDARD | OUTLET
    opened: date
    closed: date | None = None


STORES = (
    StoreSpec("WAW-01", "Salon Warszawa Centrum", "Warszawa", "FLAGSHIP", date(2014, 3, 15)),
    StoreSpec("WAW-02", "Salon Warszawa Mokotów", "Warszawa", "STANDARD", date(2017, 9, 2)),
    StoreSpec("WAW-03", "Outlet Warszawa Targówek", "Warszawa", "OUTLET", date(2021, 5, 8)),
    StoreSpec("KRK-01", "Salon Kraków Galeria", "Kraków", "FLAGSHIP", date(2015, 6, 20)),
    StoreSpec("KRK-02", "Salon Kraków Bronowice", "Kraków", "STANDARD", date(2019, 11, 16)),
    StoreSpec("WRO-01", "Salon Wrocław", "Wrocław", "FLAGSHIP", date(2015, 10, 10)),
    StoreSpec("POZ-01", "Salon Poznań", "Poznań", "STANDARD", date(2016, 4, 23)),
    StoreSpec("GDA-01", "Salon Gdańsk", "Gdańsk", "STANDARD", date(2016, 8, 27)),
    StoreSpec("LOD-01", "Salon Łódź", "Łódź", "STANDARD", date(2017, 3, 11)),
    StoreSpec("KAT-01", "Salon Katowice", "Katowice", "STANDARD", date(2017, 10, 14)),
    StoreSpec("LUB-01", "Salon Lublin", "Lublin", "STANDARD", date(2018, 5, 19)),
    StoreSpec("SZC-01", "Salon Szczecin", "Szczecin", "STANDARD", date(2018, 9, 22)),
    StoreSpec("BYD-01", "Salon Bydgoszcz", "Bydgoszcz", "STANDARD", date(2019, 2, 16)),
    StoreSpec("BIA-01", "Salon Białystok", "Białystok", "STANDARD", date(2019, 6, 29)),
    StoreSpec("RZE-01", "Salon Rzeszów", "Rzeszów", "STANDARD", date(2020, 9, 12)),
    StoreSpec("OLS-01", "Salon Olsztyn", "Olsztyn", "STANDARD", date(2021, 3, 20)),
    StoreSpec("KIE-01", "Salon Kielce", "Kielce", "STANDARD", date(2021, 10, 9), closed=date(2026, 1, 31)),
    StoreSpec("GDY-01", "Salon Gdynia", "Gdynia", "STANDARD", date(2022, 4, 23)),
    StoreSpec("TOR-01", "Salon Toruń", "Toruń", "STANDARD", date(2025, 5, 17)),
    StoreSpec("CZE-01", "Salon Częstochowa", "Częstochowa", "STANDARD", date(2026, 3, 14)),
)


@dataclass(frozen=True)
class SiteSpec:
    code: str
    name: str
    city: str
    voivodeship: str
    postal_code: str
    latitude: float
    longitude: float
    opened: date


DISTRIBUTION_CENTERS = (
    SiteSpec("DC-01", "Centrum dystrybucyjne Stryków", "Stryków", "łódzkie", "95-010", 51.9016, 19.6033, date(2016, 1, 4)),
    SiteSpec("DC-02", "Centrum dystrybucyjne Gliwice", "Gliwice", "śląskie", "44-100", 50.2945, 18.6714, date(2022, 6, 1)),
)
ONLINE_LOCATION_ID = 99  # the classic "store 99 = e-commerce" convention

# Planted truths: patterns the analytics layer (and Genie) should be able to find.
FRAUD_STORE, FRAUD_CASHIER = "LOD-01", "K7311"  # one cashier voids ~12x more lines
CANNIBALIZED_STORE, NEW_NEIGHBOUR_STORE = "BYD-01", "TOR-01"  # Toruń opening takes ~18% of Bydgoszcz traffic


@dataclass(frozen=True)
class Leaf:
    code: str
    name: str
    product_type: str  # first word of the product name
    models: tuple[tuple[str, tuple[str, ...]], ...]  # (brand, model lines)
    specs: tuple[str, ...]
    median_price: float  # gross PLN at launch
    weight_kg: tuple[float, float]
    warranty_months: int
    share: float  # share of the catalogue
    store_share: float  # probability that a product is in the store assortment
    return_factor: float = 1.0
    energy_label: bool = False


_LEAVES = (
    Leaf("LAP-NB-GAM", "Laptopy gamingowe", "Laptop",
         (("ASUS", ("TUF Gaming A15", "ROG Strix G16")), ("MSI", ("Katana 15", "Cyborg 15")),
          ("Lenovo", ("Legion 5", "LOQ 15")), ("Acer", ("Nitro V 15", "Predator Helios Neo 16")),
          ("HP", ("Victus 16", "Omen 16"))),
         ("R7-8845HS/16GB/1TB/RTX4060", "i7-13620H/16GB/512GB/RTX4050", "R5-7535HS/16GB/512GB/RTX3050",
          "i9-14900HX/32GB/1TB/RTX4070"),
         4999, (2.1, 2.9), 24, 0.045, 0.6, 1.1),
    Leaf("LAP-NB-BIZ", "Laptopy biznesowe", "Laptop",
         (("Lenovo", ("ThinkPad E14", "ThinkPad T14")), ("Dell", ("Latitude 5440", "Vostro 3530")),
          ("HP", ("ProBook 450", "EliteBook 840"))),
         ("i5-1335U/16GB/512GB/Win11Pro", "i7-1355U/32GB/1TB/Win11Pro", "R5-7530U/16GB/512GB/Win11Pro"),
         4299, (1.4, 1.9), 36, 0.035, 0.4, 0.8),
    Leaf("LAP-NB-ULT", "Ultrabooki", "Laptop",
         (("Apple", ("MacBook Air 13 M3", "MacBook Air 15 M3", "MacBook Pro 14 M4")),
          ("ASUS", ("Zenbook 14 OLED", "Vivobook S 15")), ("Lenovo", ("Yoga Slim 7",)), ("Dell", ("XPS 13",))),
         ("16GB/512GB", "8GB/256GB", "24GB/1TB", "32GB/1TB"),
         5499, (1.1, 1.6), 24, 0.03, 0.7, 0.9),
    Leaf("LAP-PC-GAM", "Komputery gamingowe", "Komputer",
         (("NovaPC", ("Hero", "Elite", "Ultra")),),
         ("R5-7600/32GB/1TB/RTX4060", "i5-14400F/16GB/1TB/RX7600", "R7-7800X3D/32GB/2TB/RTX4070S"),
         5999, (8.0, 14.0), 24, 0.012, 0.3, 0.9),
    Leaf("LAP-PC-MIN", "Mini PC", "Komputer",
         (("Lenovo", ("ThinkCentre M70q Tiny",)), ("Apple", ("Mac mini M4",)), ("ASUS", ("NUC 14 Pro",))),
         ("16GB/512GB", "8GB/256GB", "32GB/1TB"),
         2899, (0.6, 1.4), 24, 0.01, 0.3),
    Leaf("PDZ-KG-NV", "Karty graficzne NVIDIA", "Karta graficzna",
         (("ASUS", ("GeForce RTX 4060 Dual", "GeForce RTX 4070 SUPER TUF")),
          ("MSI", ("GeForce RTX 4060 Ventus 2X", "GeForce RTX 5070 Gaming Trio")),
          ("Gigabyte", ("GeForce RTX 4060 Ti Eagle", "GeForce RTX 5080 Aorus Master")),
          ("Palit", ("GeForce RTX 3050 StormX",))),
         ("8GB GDDR6", "12GB GDDR6X", "16GB GDDR7", "8GB GDDR6 OC"),
         2299, (0.6, 1.8), 36, 0.04, 0.35),
    Leaf("PDZ-KG-AMD", "Karty graficzne AMD", "Karta graficzna",
         (("Sapphire", ("Radeon RX 7600 Pulse", "Radeon RX 7800 XT Nitro+")),
          ("PowerColor", ("Radeon RX 7700 XT Hellhound",)), ("XFX", ("Radeon RX 9070 XT Quicksilver",))),
         ("8GB GDDR6", "12GB GDDR6", "16GB GDDR6"),
         2199, (0.7, 1.6), 24, 0.02, 0.3),
    Leaf("PDZ-PAM-SSD", "Dyski SSD", "Dysk SSD",
         (("Samsung", ("990 PRO", "990 EVO")), ("Kingston", ("NV2", "KC3000")), ("Goodram", ("PX600", "IRDM Pro")),
          ("Crucial", ("P3 Plus", "T500"))),
         ("500GB M.2 PCIe NVMe", "1TB M.2 PCIe NVMe", "2TB M.2 PCIe NVMe", "4TB M.2 PCIe NVMe"),
         349, (0.01, 0.05), 60, 0.05, 0.8),
    Leaf("PDZ-PAM-RAM", "Pamięci RAM", "Pamięć RAM",
         (("Kingston", ("FURY Beast",)), ("Corsair", ("Vengeance",)), ("Goodram", ("IRDM",)), ("G.Skill", ("Trident Z5",))),
         ("16GB (2x8GB) 3200MHz CL16", "32GB (2x16GB) 6000MHz CL30", "32GB (2x16GB) 3600MHz CL18",
          "64GB (2x32GB) 6000MHz CL30"),
         299, (0.03, 0.1), 120, 0.03, 0.7),
    Leaf("PDZ-CPU-DT", "Procesory", "Procesor",
         (("AMD", ("Ryzen 5 7600", "Ryzen 7 7800X3D", "Ryzen 7 9700X")),
          ("Intel", ("Core i5-14400F", "Core i7-14700K", "Core Ultra 7 265K"))),
         ("BOX", "Tray", "BOX z chłodzeniem"),
         1199, (0.05, 0.4), 36, 0.02, 0.5),
    Leaf("GSM-TEL-AND", "Smartfony z Androidem", "Smartfon",
         (("Samsung", ("Galaxy S25", "Galaxy A56 5G", "Galaxy A16")), ("Xiaomi", ("Redmi Note 14 Pro", "14T")),
          ("Motorola", ("moto g85 5G", "edge 50")), ("Google", ("Pixel 9a", "Pixel 9 Pro"))),
         ("8/256GB Czarny", "8/128GB Niebieski", "12/512GB Szary", "6/128GB Zielony"),
         1799, (0.18, 0.23), 24, 0.06, 0.7, 1.2),
    Leaf("GSM-TEL-IOS", "iPhone", "Smartfon",
         (("Apple", ("iPhone 16", "iPhone 16 Pro", "iPhone 16e", "iPhone 17")),),
         ("128GB Czarny", "256GB Biały", "512GB Tytan naturalny", "128GB Różowy"),
         4499, (0.17, 0.23), 24, 0.02, 0.8, 0.9),
    Leaf("GSM-SW-SW", "Smartwatche", "Smartwatch",
         (("Apple", ("Watch Series 10", "Watch SE")), ("Samsung", ("Galaxy Watch7", "Galaxy Watch Ultra")),
          ("Garmin", ("Forerunner 265", "Venu 3")), ("Xiaomi", ("Smart Band 9",))),
         ("42mm Czarny", "44mm Srebrny", "46mm GPS", "40mm Różowy"),
         1199, (0.03, 0.08), 24, 0.03, 0.6),
    Leaf("GSM-AKC-ETU", "Etui", "Etui",
         (("Spigen", ("Ultra Hybrid", "Rugged Armor")), ("Apple", ("Silicone Case MagSafe",)),
          ("Tech-Protect", ("Icon", "Kevlar"))),
         ("do iPhone 16", "do Galaxy S25", "do iPhone 16 Pro", "do Redmi Note 14 Pro"),
         69, (0.02, 0.06), 12, 0.08, 0.9, 1.3),
    Leaf("GSM-AKC-LAD", "Ładowarki", "Ładowarka",
         (("Baseus", ("GaN5 Pro",)), ("Anker", ("Nano",)), ("Samsung", ("Super Fast Charging",)), ("Ugreen", ("Nexode",))),
         ("65W USB-C", "20W USB-C", "100W 2x USB-C", "45W USB-C"),
         99, (0.05, 0.25), 24, 0.05, 0.9),
    Leaf("GSM-AKC-SZK", "Szkła hartowane", "Szkło hartowane",
         (("Spigen", ("Glas.tR",)), ("Tech-Protect", ("Supreme Glass",)), ("3mk", ("HardGlass",))),
         ("do iPhone 16", "do Galaxy S25", "do Pixel 9a"),
         49, (0.01, 0.03), 12, 0.05, 0.9, 1.2),
    Leaf("GAM-KON-KON", "Konsole", "Konsola",
         (("Sony", ("PlayStation 5 Slim", "PlayStation 5 Pro")), ("Microsoft", ("Xbox Series X", "Xbox Series S")),
          ("Nintendo", ("Switch OLED", "Switch 2"))),
         ("1TB", "512GB", "z napędem", "Digital Edition"),
         2299, (2.5, 4.5), 24, 0.012, 0.9, 0.8),
    Leaf("GAM-KON-GRY", "Gry", "Gra",
         (("CD Projekt", ("Cyberpunk 2077", "Wiedźmin 3: Dziki Gon")), ("EA", ("SPORTS FC 25", "SPORTS FC 26")),
          ("Nintendo", ("Mario Kart World", "Super Mario Odyssey"))),
         ("PS5", "Xbox Series X", "Nintendo Switch", "PC"),
         199, (0.08, 0.15), 12, 0.04, 0.8, 0.6),
    Leaf("GAM-AKC-PAD", "Pady", "Pad",
         (("Sony", ("DualSense", "DualSense Edge")), ("Microsoft", ("Xbox Wireless Controller",)),
          ("Genesis", ("Mangan 400",))),
         ("Czarny", "Biały", "Midnight Black", "Cosmic Red"),
         299, (0.25, 0.35), 24, 0.02, 0.9),
    Leaf("PER-MON-GAM", "Monitory gamingowe", "Monitor",
         (("LG", ("UltraGear 27GR75Q",)), ("Samsung", ("Odyssey G5",)), ("AOC", ("Q27G3XMN",)),
          ("MSI", ("MAG 274QRF",)), ("ASUS", ("TUF Gaming VG27AQ",))),
         ('27" IPS 165Hz', '27" VA 165Hz', '32" IPS 180Hz', '24" IPS 144Hz'),
         1199, (4.5, 7.5), 36, 0.03, 0.4, 1.0, True),
    Leaf("PER-MON-BIU", "Monitory biurowe", "Monitor",
         (("Dell", ("P2425H",)), ("Philips", ("241V8",)), ("iiyama", ("ProLite XU2493HS",)), ("LG", ("24MR400",))),
         ('24" IPS', '27" IPS', '24" VA'),
         599, (3.0, 5.5), 36, 0.025, 0.4, 1.0, True),
    Leaf("PER-WEJ-MYS", "Myszki", "Myszka",
         (("Logitech", ("G305 Lightspeed", "MX Master 3S", "G502 X")), ("Razer", ("DeathAdder V3",)),
          ("SteelSeries", ("Rival 3",)), ("Genesis", ("Krypton 290",))),
         ("Czarna", "Biała", "bezprzewodowa"),
         179, (0.06, 0.15), 24, 0.04, 0.9),
    Leaf("PER-WEJ-KLA", "Klawiatury", "Klawiatura",
         (("Logitech", ("MX Keys S", "G915 TKL")), ("Razer", ("BlackWidow V4",)), ("SteelSeries", ("Apex 3",)),
          ("Genesis", ("Thor 300",)), ("Natec", ("Moray",))),
         ("US", "PL", "TKL Brown Switch", "Red Switch"),
         299, (0.5, 1.2), 24, 0.03, 0.8),
    Leaf("PER-AUD-SLU", "Słuchawki", "Słuchawki",
         (("Sony", ("WH-1000XM5", "WH-CH720N")), ("JBL", ("Tune 520BT", "Tune 770NC")),
          ("Apple", ("AirPods 4", "AirPods Pro 2")), ("SteelSeries", ("Arctis Nova 7",)), ("Logitech", ("G435",))),
         ("Czarne", "Białe", "Niebieskie"),
         399, (0.05, 0.35), 24, 0.05, 0.9, 1.4),
    Leaf("RTV-TV-LED", "Telewizory LED", "Telewizor",
         (("Samsung", ("UE55DU7172", "QE65Q80D")), ("LG", ("55UT73006LA", "65QNED86")),
          ("TCL", ("55C655", "65P755")), ("Philips", ("50PUS8009",))),
         ('55" 4K', '65" 4K', '50" 4K', '43" 4K'),
         2499, (9.0, 22.0), 24, 0.03, 0.4, 1.0, True),
    Leaf("RTV-TV-OLED", "Telewizory OLED", "Telewizor",
         (("LG", ("OLED55C4", "OLED65B4")), ("Sony", ("Bravia 8",)), ("Samsung", ("QE55S90D",)),
          ("Philips", ("55OLED809",))),
         ('55" 4K 120Hz', '65" 4K 120Hz', '77" 4K'),
         5999, (14.0, 28.0), 24, 0.015, 0.4, 1.0, True),
    Leaf("RTV-GLO-BT", "Głośniki Bluetooth", "Głośnik",
         (("JBL", ("Flip 6", "Charge 5", "Go 4")), ("Sony", ("ULT Field 1",)), ("Marshall", ("Emberton III",))),
         ("Czarny", "Niebieski", "Czerwony"),
         449, (0.2, 1.0), 24, 0.025, 0.9),
    Leaf("SIE-ROU-WIFI", "Routery", "Router",
         (("TP-Link", ("Archer AX55", "Deco X50 (2-pack)")), ("ASUS", ("RT-AX58U", "ZenWiFi XD5")),
          ("Netgear", ("Nighthawk RAX30",))),
         ("Wi-Fi 6", "Wi-Fi 6E", "Wi-Fi 7"),
         399, (0.4, 1.0), 36, 0.025, 0.7),
    Leaf("SIE-AKC-KAB", "Kable", "Kabel",
         (("Unitek", ("USB-C - USB-C",)), ("Baseus", ("Superior USB-C - Lightning",)), ("Goobay", ("HDMI 2.1",)),
          ("Natec", ("Extreme Media",))),
         ("1m", "2m", "3m", "0,5m"),
         39, (0.03, 0.12), 24, 0.06, 0.95, 0.6),
    Leaf("SIE-AKC-PEN", "Pendrive'y", "Pendrive",
         (("SanDisk", ("Ultra Flair",)), ("Kingston", ("DataTraveler Exodia",)), ("Goodram", ("UME3",)),
          ("Samsung", ("BAR Plus",))),
         ("64GB USB 3.2", "128GB USB 3.2", "256GB USB 3.2", "32GB USB 3.0"),
         49, (0.01, 0.03), 60, 0.04, 0.95),
)
LEAVES = {leaf.code: leaf for leaf in _LEAVES}

CATEGORY_TREE = (  # (code, name, children); level-3 names come from LEAVES
    ("LAP", "Laptopy i komputery", (
        ("LAP-NB", "Laptopy", ("LAP-NB-GAM", "LAP-NB-BIZ", "LAP-NB-ULT")),
        ("LAP-PC", "Komputery stacjonarne", ("LAP-PC-GAM", "LAP-PC-MIN")),
    )),
    ("PDZ", "Podzespoły komputerowe", (
        ("PDZ-KG", "Karty graficzne", ("PDZ-KG-NV", "PDZ-KG-AMD")),
        ("PDZ-PAM", "Pamięci i dyski", ("PDZ-PAM-SSD", "PDZ-PAM-RAM")),
        ("PDZ-CPU", "Procesory", ("PDZ-CPU-DT",)),
    )),
    ("GSM", "Smartfony i smartwatche", (
        ("GSM-TEL", "Smartfony", ("GSM-TEL-AND", "GSM-TEL-IOS")),
        ("GSM-SW", "Smartwatche", ("GSM-SW-SW",)),
        ("GSM-AKC", "Akcesoria GSM", ("GSM-AKC-ETU", "GSM-AKC-LAD", "GSM-AKC-SZK")),
    )),
    ("GAM", "Gaming", (
        ("GAM-KON", "Konsole i gry", ("GAM-KON-KON", "GAM-KON-GRY")),
        ("GAM-AKC", "Akcesoria gamingowe", ("GAM-AKC-PAD",)),
    )),
    ("PER", "Peryferia", (
        ("PER-MON", "Monitory", ("PER-MON-GAM", "PER-MON-BIU")),
        ("PER-WEJ", "Myszki i klawiatury", ("PER-WEJ-MYS", "PER-WEJ-KLA")),
        ("PER-AUD", "Słuchawki i mikrofony", ("PER-AUD-SLU",)),
    )),
    ("RTV", "TV i audio", (
        ("RTV-TV", "Telewizory", ("RTV-TV-LED", "RTV-TV-OLED")),
        ("RTV-GLO", "Głośniki", ("RTV-GLO-BT",)),
    )),
    ("SIE", "Sieć i akcesoria", (
        ("SIE-ROU", "Sieć", ("SIE-ROU-WIFI",)),
        ("SIE-AKC", "Akcesoria komputerowe", ("SIE-AKC-KAB", "SIE-AKC-PEN")),
    )),
)
CATEGORY_RENAMES = {"GSM-SW": (date(2025, 6, 1), "Urządzenia ubieralne")}  # SCD2 material

BRAND_VARIANTS = {  # how the same brand gets typed into an ERP over the years
    "ASUS": ("Asus", "ASUSTeK"), "Samsung": ("SAMSUNG", "Samsung Electronics"), "Apple": ("APPLE", "Apple Inc."),
    "Lenovo": ("LENOVO",), "Logitech": ("LOGITECH", "Logitech G"), "Xiaomi": ("XIAOMI", "Mi"), "Sony": ("SONY",),
    "HP": ("Hewlett-Packard", "HP Inc."), "MSI": ("Micro-Star", "msi"), "LG": ("LG Electronics",),
    "TP-Link": ("TPLINK", "Tp-link"), "Gigabyte": ("GIGABYTE",), "JBL": ("Jbl",), "Kingston": ("KINGSTON",),
}

EAN_PREFIXES = {  # GS1-style prefixes; the US ones start with 0 -> leading-zero traps in CSV inference
    "ASUS": "471", "MSI": "471", "Acer": "471", "Gigabyte": "471", "PowerColor": "471", "G.Skill": "471",
    "Unitek": "471", "Palit": "489", "Sapphire": "489",
    "Apple": "019", "Dell": "088", "HP": "019", "Intel": "073", "AMD": "073", "Microsoft": "088", "Razer": "081",
    "Corsair": "084", "Crucial": "064", "SanDisk": "061", "Kingston": "074", "Google": "081", "Motorola": "084",
    "Netgear": "060", "Garmin": "075", "JBL": "050", "EA": "014", "Nintendo": "045", "XFX": "079",
    "Lenovo": "019", "Anker": "019",
    "Samsung": "880", "LG": "880", "Spigen": "880",
    "Xiaomi": "695", "TCL": "693", "Baseus": "695", "Ugreen": "695", "AOC": "693",
    "Sony": "454", "iiyama": "494",
    "Goodram": "590", "Genesis": "590", "Natec": "590", "NovaPC": "590", "CD Projekt": "590",
    "Tech-Protect": "590", "3mk": "590",
    "Goobay": "405", "Philips": "871", "SteelSeries": "570", "Logitech": "509", "Marshall": "735",
}
