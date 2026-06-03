"""Procedural world generation for Kronikler: Küllerin Mirası."""
import random
import uuid
from datetime import datetime, timezone

# --- Turkish name pools ---
MALE_NAMES = [
    "Alparslan", "Bayram", "Berk", "Cemal", "Demir", "Ertan", "Faruk", "Gökhan",
    "Hasan", "İlhan", "Kerem", "Kaya", "Mahmut", "Mehmet", "Mert", "Murat",
    "Mustafa", "Nazım", "Orhan", "Polat", "Recep", "Selim", "Şahin", "Tuğrul",
    "Umut", "Veli", "Yiğit", "Aslan", "Burak", "Doğan", "Emre", "Fatih",
    "Gazi", "Hamza", "İbrahim", "Kasım", "Levent", "Mansur", "Necati", "Onur",
    "Reşat", "Sefa", "Talip", "Uğur", "Yusuf", "Zeki", "Bora", "Cengiz",
]
FEMALE_NAMES = [
    "Asena", "Ayşe", "Berrin", "Ceren", "Defne", "Elif", "Fatma", "Gül",
    "Hayriye", "İclal", "Jale", "Kübra", "Leyla", "Melek", "Naciye", "Nilgün",
    "Özge", "Pelin", "Rabia", "Sevim", "Şükriye", "Tülay", "Ümmü", "Yasemin",
    "Zehra", "Aliye", "Bahar", "Cemile", "Duru", "Esma", "Feride", "Gülşen",
    "Hande", "İlknur", "Kader", "Lale", "Meryem", "Nesrin", "Oya", "Perihan",
]
SURNAMES = [
    "Demirhan", "Yıldız", "Karaoğlu", "Aslanbey", "Çelikbaş", "Kılıçdar",
    "Akkaya", "Karadağ", "Gümüştekin", "Bozkurt", "Şahinoğlu", "Yıldırım",
    "Tuna", "Korkmaz", "Çakır", "Polat", "Yağmur", "Boran", "Tepe", "Bey",
    "Han", "Pa​şa", "Ak", "Kara", "Demir", "Taş", "Ay", "Kurt",
]

KINGDOM_NAMES = [
    "Külhanlı Hanedanı", "Demirhan Krallığı", "Altınyay Beyliği",
    "Kuzgun İmparatorluğu", "Akpınar Eyaleti",
]
KINGDOM_CULTURES = ["Külhanlı", "Demirhan", "Altınyay", "Kuzgun", "Akpınar"]
KINGDOM_RELIGIONS = ["Ateş Yolu", "Eski Tanrılar", "Tek Tanrı", "Atalar Kültü"]

CITY_NAMES = [
    "Karşılkale", "Boranözü", "Akyaman", "Gümüşharç", "Demiryurt",
    "Külboğa", "Akkarsu", "Yıldıztepe", "Karadüğüm", "Bozhisar",
]
VILLAGE_NAMES = [
    "Kavaklıdere", "Söğütpınar", "Çayıraltı", "Karaçam", "Akçakaya",
    "Yağmurlu", "Taşköprü", "Kurttepe", "Yeniyurt", "Eskidere",
    "Karayel", "Boğazkesen", "Çamlıbel", "Akdoğan", "Karakuyu",
    "Yarımca", "Karagöl", "Akçapınar", "Boyalıca", "Ulukışla",
]
CASTLE_NAMES = [
    "Demir Kapı", "Kara Kule", "Yılan Kayası", "Ak Burç", "Külkale",
    "Sarp Geçit", "Kuzgun Pençesi", "Külperi Kulesi", "Gri Sur", "Boz Ocak",
]

PROFESSIONS_COMMON = [
    "çiftçi", "demirci", "tüccar", "avcı", "asker", "balıkçı",
    "çoban", "fırıncı", "marangoz", "şifacı", "rahip", "haydut",
    "değirmenci", "öğretmen", "han sahibi", "kunduracı", "katip",
]
PROFESSIONS_NOBLE = ["lord", "general", "veliaht", "kral", "şövalye"]

PERSONALITY_TRAITS = [
    "kibirli", "alçakgönüllü", "cömert", "cimri", "cesur", "korkak",
    "sadık", "vefasız", "sabırlı", "öfkeli", "neşeli", "asık suratlı",
    "kurnaz", "saf", "merhametli", "acımasız", "hırslı", "tembel",
    "konuşkan", "suskun",
]

GOODS = ["buğday", "ekmek", "et", "demir", "odun", "kumaş", "silah"]
GOOD_BASE_PRICES = {
    "buğday": 4, "ekmek": 6, "et": 12, "demir": 25,
    "odun": 5, "kumaş": 10, "silah": 60,
}

PLAYER_START_PROFESSIONS = [
    "köylü", "çiftçi", "asker", "tüccar", "avcı", "demirci çırağı",
]


def new_id() -> str:
    return uuid.uuid4().hex[:16]


def _pick_name(gender: str) -> str:
    given = random.choice(MALE_NAMES if gender == "erkek" else FEMALE_NAMES)
    return f"{given} {random.choice(SURNAMES)}"


def _make_location(kind: str, name: str, kingdom_id: str, kingdom_name: str):
    pop_map = {
        "şehir": (4000, 12000),
        "köy": (80, 600),
        "kale": (50, 400),
    }
    low, high = pop_map[kind]
    population = random.randint(low, high)
    wealth = random.randint(20, 90) if kind == "şehir" else random.randint(10, 70)
    security = random.randint(30, 95) if kind != "köy" else random.randint(10, 70)
    prosperity = random.randint(20, 90)
    prices = {g: max(1, round(GOOD_BASE_PRICES[g] * random.uniform(0.7, 1.4), 1))
              for g in GOODS}
    return {
        "id": new_id(),
        "kind": kind,
        "name": name,
        "kingdom_id": kingdom_id,
        "kingdom_name": kingdom_name,
        "population": population,
        "wealth": wealth,
        "security": security,
        "prosperity": prosperity,
        "prices": prices,
        "production": random.choice(GOODS),
        "ruler_id": None,
    }


def _make_npc(location, kingdom_id, kingdom_name, religion, profession=None):
    gender = random.choice(["erkek", "kadın"])
    age = random.randint(16, 72)
    prof = profession or random.choice(PROFESSIONS_COMMON)
    wealth = {
        "lord": random.randint(5000, 25000),
        "general": random.randint(2000, 8000),
        "kral": random.randint(20000, 80000),
        "veliaht": random.randint(8000, 25000),
        "tüccar": random.randint(500, 5000),
        "haydut": random.randint(20, 800),
    }.get(prof, random.randint(10, 500))
    return {
        "id": new_id(),
        "name": _pick_name(gender),
        "gender": gender,
        "age": age,
        "profession": prof,
        "personality": random.sample(PERSONALITY_TRAITS, 2),
        "wealth": wealth,
        "health": random.randint(60, 100),
        "kingdom_id": kingdom_id,
        "kingdom_name": kingdom_name,
        "religion": religion,
        "location_id": location["id"],
        "location_name": location["name"],
        "spouse_id": None,
        "children_ids": [],
        "parent_ids": [],
        "friend_ids": [],
        "rival_ids": [],
        "goal": random.choice([
            "servet kazanmak", "iyi bir eş bulmak", "ün kazanmak",
            "evini büyütmek", "intikam almak", "ailesini korumak",
            "lord olmak", "ticaret yolu kurmak", "huzurlu yaşamak",
        ]),
        "mood": random.choice(["neşeli", "yorgun", "umutsuz", "kararlı", "huzurlu", "öfkeli"]),
        "alive": True,
    }


def _link_family(npcs):
    """Pair off some adult NPCs as spouses and create children."""
    adults = [n for n in npcs if 22 <= n["age"] <= 55 and n["spouse_id"] is None]
    random.shuffle(adults)
    pairs_formed = 0
    i = 0
    while i < len(adults) - 1 and pairs_formed < len(adults) // 3:
        a = adults[i]
        partner = next(
            (b for b in adults[i+1:] if b["gender"] != a["gender"]
             and b["spouse_id"] is None and b["kingdom_id"] == a["kingdom_id"]),
            None,
        )
        if partner:
            a["spouse_id"] = partner["id"]
            partner["spouse_id"] = a["id"]
            # Children
            n_children = random.randint(0, 3)
            for _ in range(n_children):
                child = next(
                    (c for c in npcs if c["age"] < 18
                     and not c["parent_ids"]
                     and c["location_id"] == a["location_id"]),
                    None,
                )
                if child:
                    child["parent_ids"] = [a["id"], partner["id"]]
                    a["children_ids"].append(child["id"])
                    partner["children_ids"].append(child["id"])
            pairs_formed += 1
        i += 1


def generate_world(n_kingdoms=3, n_cities=3, n_villages=10, n_castles=5, n_npcs=100):
    kingdoms = []
    locations = []
    npcs = []

    kingdom_names = random.sample(KINGDOM_NAMES, n_kingdoms)
    cultures = random.sample(KINGDOM_CULTURES, n_kingdoms)
    for i in range(n_kingdoms):
        kid = new_id()
        kingdoms.append({
            "id": kid,
            "name": kingdom_names[i],
            "culture": cultures[i],
            "religion": random.choice(KINGDOM_RELIGIONS),
            "treasury": random.randint(5000, 30000),
            "stability": random.randint(40, 90),
            "king_id": None,
            "heir_id": None,
            "at_war_with": [],
            "allies": [],
        })

    # Distribute cities, villages, castles among kingdoms
    def distribute(n, kingdoms_list):
        out = []
        for idx in range(n):
            out.append(kingdoms_list[idx % len(kingdoms_list)])
        return out

    city_assign = distribute(n_cities, kingdoms)
    village_assign = distribute(n_villages, kingdoms)
    castle_assign = distribute(n_castles, kingdoms)

    used_city_names = random.sample(CITY_NAMES, min(n_cities, len(CITY_NAMES)))
    used_village_names = random.sample(VILLAGE_NAMES, min(n_villages, len(VILLAGE_NAMES)))
    used_castle_names = random.sample(CASTLE_NAMES, min(n_castles, len(CASTLE_NAMES)))

    for i in range(n_cities):
        k = city_assign[i]
        locations.append(_make_location("şehir", used_city_names[i], k["id"], k["name"]))
    for i in range(n_villages):
        k = village_assign[i]
        locations.append(_make_location("köy", used_village_names[i], k["id"], k["name"]))
    for i in range(n_castles):
        k = castle_assign[i]
        locations.append(_make_location("kale", used_castle_names[i], k["id"], k["name"]))

    # NPCs: distribute proportionally
    weights = []
    for loc in locations:
        w = {"şehir": 4, "kale": 2, "köy": 1}[loc["kind"]]
        weights.append(w)
    total_w = sum(weights)
    counts = [max(1, round(n_npcs * w / total_w)) for w in weights]
    # Adjust to n_npcs
    diff = n_npcs - sum(counts)
    while diff != 0:
        idx = random.randrange(len(counts))
        if diff > 0:
            counts[idx] += 1
            diff -= 1
        elif counts[idx] > 1:
            counts[idx] -= 1
            diff += 1

    # Create kings/heirs/lords for each kingdom
    for k in kingdoms:
        # Find a city in this kingdom for the king
        capital = next((l for l in locations if l["kingdom_id"] == k["id"] and l["kind"] == "şehir"), None)
        if not capital:
            capital = next(l for l in locations if l["kingdom_id"] == k["id"])
        king = _make_npc(capital, k["id"], k["name"], k["religion"], profession="kral")
        king["age"] = random.randint(40, 65)
        npcs.append(king)
        k["king_id"] = king["id"]
        heir = _make_npc(capital, k["id"], k["name"], k["religion"], profession="veliaht")
        heir["age"] = random.randint(18, 30)
        npcs.append(heir)
        k["heir_id"] = heir["id"]
        # Lord per castle in kingdom
        for castle in [l for l in locations if l["kingdom_id"] == k["id"] and l["kind"] == "kale"]:
            lord = _make_npc(castle, k["id"], k["name"], k["religion"], profession="lord")
            lord["age"] = random.randint(30, 60)
            npcs.append(lord)
            castle["ruler_id"] = lord["id"]

    remaining = n_npcs - len(npcs)
    # Distribute remaining across locations
    for i, loc in enumerate(locations):
        k = next(kk for kk in kingdoms if kk["id"] == loc["kingdom_id"])
        share = max(0, counts[i] - sum(1 for n in npcs if n["location_id"] == loc["id"]))
        for _ in range(share):
            if remaining <= 0:
                break
            npcs.append(_make_npc(loc, k["id"], k["name"], k["religion"]))
            remaining -= 1
        if remaining <= 0:
            break
    while remaining > 0:
        loc = random.choice(locations)
        k = next(kk for kk in kingdoms if kk["id"] == loc["kingdom_id"])
        npcs.append(_make_npc(loc, k["id"], k["name"], k["religion"]))
        remaining -= 1

    _link_family(npcs)

    return {
        "kingdoms": kingdoms,
        "locations": locations,
        "npcs": npcs,
    }


def generate_player(world):
    gender = random.choice(["erkek", "kadın"])
    age = random.randint(18, 30)
    location = random.choice([l for l in world["locations"] if l["kind"] != "kale"])
    kingdom = next(k for k in world["kingdoms"] if k["id"] == location["kingdom_id"])
    return {
        "name": _pick_name(gender),
        "gender": gender,
        "age": age,
        "culture": kingdom["culture"],
        "religion": kingdom["religion"],
        "kingdom_id": kingdom["id"],
        "kingdom_name": kingdom["name"],
        "money": random.randint(50, 250),
        "profession": random.choice(PLAYER_START_PROFESSIONS),
        "education": random.choice(["yok", "temel", "orta", "iyi"]),
        "reputation": 0,
        "health": 100,
        "crime": 0,
        "location_id": location["id"],
        "location_name": location["name"],
        "spouse_id": None,
        "children_ids": [],
        "inventory": {"ekmek": 3, "buğday": 5},
        "skills": {
            "savaş": random.randint(1, 5),
            "ticaret": random.randint(1, 5),
            "avcılık": random.randint(1, 5),
            "diplomasi": random.randint(1, 5),
        },
    }


def initial_history():
    return [
        {
            "id": new_id(),
            "day": 0,
            "type": "başlangıç",
            "text": "Küllerin Mirası: Yeni bir yolculuk başlıyor. Dünya kendi kaderini yazmaya devam ediyor.",
        }
    ]
