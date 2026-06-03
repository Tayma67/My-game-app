"""World simulation tick: NPC lives, economy, politics, events.

The world advances independently of the player.
"""
import random
from world_gen import (
    new_id, MALE_NAMES, FEMALE_NAMES, SURNAMES, GOODS, GOOD_BASE_PRICES,
    PROFESSIONS_COMMON, PERSONALITY_TRAITS,
)


def _push_event(state, day, etype, text):
    state["history"].append({
        "id": new_id(),
        "day": day,
        "type": etype,
        "text": text,
    })


def _random_name(gender):
    given = random.choice(MALE_NAMES if gender == "erkek" else FEMALE_NAMES)
    return f"{given} {random.choice(SURNAMES)}"


def _age_and_die(state, day):
    """Each tick, NPCs age by ~7 days/tick. Old/sick NPCs may die."""
    npcs_alive = [n for n in state["world"]["npcs"] if n["alive"]]
    for npc in npcs_alive:
        # Age in months — every tick increments slowly
        # 1 tick ~ 1 week of game time
        if random.random() < 0.02:  # ~1 in 50 ticks ages 1 year
            npc["age"] += 1
        # Health drain
        npc["health"] = max(0, npc["health"] - random.randint(0, 1))
        # Death roll
        death_chance = 0.0005 + max(0, (npc["age"] - 55)) * 0.0015
        if npc["health"] < 20:
            death_chance += 0.05
        if random.random() < death_chance:
            npc["alive"] = False
            _push_event(state, day, "ölüm",
                        f"{npc['name']} ({npc['age']}) {npc['location_name']}'de hayata gözlerini yumdu.")
            # If king dies, heir becomes king
            kingdom = next((k for k in state["world"]["kingdoms"] if k["king_id"] == npc["id"]), None)
            if kingdom:
                heir_id = kingdom["heir_id"]
                heir = next((n for n in state["world"]["npcs"] if n["id"] == heir_id and n["alive"]), None)
                if heir:
                    heir["profession"] = "kral"
                    kingdom["king_id"] = heir["id"]
                    _push_event(state, day, "tahta_çıkış",
                                f"{heir['name']}, {kingdom['name']} tahtına çıktı.")
                    # New heir: pick eldest child or random adult
                    child = next(
                        (n for n in state["world"]["npcs"]
                         if n["alive"] and heir["id"] in n["parent_ids"]),
                        None,
                    )
                    if not child:
                        candidates = [n for n in state["world"]["npcs"]
                                      if n["alive"] and n["kingdom_id"] == kingdom["id"]
                                      and 16 <= n["age"] <= 35 and n["profession"] != "kral"]
                        child = random.choice(candidates) if candidates else None
                    if child:
                        child["profession"] = "veliaht"
                        kingdom["heir_id"] = child["id"]


def _marry_and_birth(state, day):
    """Some single adults marry. Married couples may have children."""
    npcs = [n for n in state["world"]["npcs"] if n["alive"]]
    singles = [n for n in npcs if 20 <= n["age"] <= 45 and not n["spouse_id"]]
    random.shuffle(singles)
    used = set()
    for a in singles:
        if a["id"] in used:
            continue
        if random.random() > 0.04:
            continue
        for b in singles:
            if b["id"] == a["id"] or b["id"] in used:
                continue
            if b["gender"] == a["gender"]:
                continue
            if b["location_id"] != a["location_id"]:
                continue
            a["spouse_id"] = b["id"]
            b["spouse_id"] = a["id"]
            used.add(a["id"]); used.add(b["id"])
            _push_event(state, day, "evlilik",
                        f"{a['name']} ile {b['name']}, {a['location_name']}'de dünya evine girdi.")
            break

    # Births
    couples_seen = set()
    for a in npcs:
        if not a["spouse_id"]:
            continue
        if a["gender"] != "kadın":
            continue
        key = tuple(sorted([a["id"], a["spouse_id"]]))
        if key in couples_seen:
            continue
        couples_seen.add(key)
        if a["age"] > 42:
            continue
        if random.random() < 0.05:
            partner = next((p for p in npcs if p["id"] == a["spouse_id"]), None)
            if not partner:
                continue
            gender = random.choice(["erkek", "kadın"])
            child = {
                "id": new_id(),
                "name": _random_name(gender),
                "gender": gender,
                "age": 0,
                "profession": "çocuk",
                "personality": random.sample(PERSONALITY_TRAITS, 2),
                "wealth": 0,
                "health": 90,
                "kingdom_id": a["kingdom_id"],
                "kingdom_name": a["kingdom_name"],
                "religion": a["religion"],
                "location_id": a["location_id"],
                "location_name": a["location_name"],
                "spouse_id": None,
                "children_ids": [],
                "parent_ids": [a["id"], partner["id"]],
                "friend_ids": [],
                "rival_ids": [],
                "goal": "büyümek",
                "mood": "huzurlu",
                "alive": True,
            }
            a["children_ids"].append(child["id"])
            partner["children_ids"].append(child["id"])
            state["world"]["npcs"].append(child)
            _push_event(state, day, "doğum",
                        f"{a['name']} ve {partner['name']}'in çocuğu {child['name']} doğdu.")


def _economy_tick(state, day):
    """Adjust prices per location based on wealth, security, randomness."""
    for loc in state["world"]["locations"]:
        for good in GOODS:
            base = GOOD_BASE_PRICES[good]
            wealth_factor = 0.5 + (loc["wealth"] / 100)
            security_factor = 0.6 + (loc["security"] / 100) * 0.8
            noise = random.uniform(0.85, 1.15)
            target = base * wealth_factor * security_factor * noise
            current = loc["prices"].get(good, base)
            new_price = round(current * 0.7 + target * 0.3, 1)
            loc["prices"][good] = max(1.0, new_price)
        # Slow drift on wealth/security
        loc["wealth"] = max(5, min(100, loc["wealth"] + random.randint(-2, 2)))
        loc["security"] = max(5, min(100, loc["security"] + random.randint(-3, 3)))
        loc["prosperity"] = max(5, min(100, round((loc["wealth"] + loc["security"]) / 2)))


def _random_events(state, day):
    """Random world events: rebellions, wars, crises, festivals."""
    if random.random() < 0.08:
        loc = random.choice(state["world"]["locations"])
        loc["security"] = max(5, loc["security"] - random.randint(5, 20))
        _push_event(state, day, "haydut_baskını",
                    f"Haydutlar {loc['name']}'i bastı. Güvenlik düştü.")
    if random.random() < 0.05:
        loc = random.choice([l for l in state["world"]["locations"] if l["kind"] != "kale"])
        loc["wealth"] = max(5, loc["wealth"] - random.randint(5, 15))
        _push_event(state, day, "kıtlık",
                    f"{loc['name']}'de kötü hasat: refah düştü.")
    if random.random() < 0.04 and len(state["world"]["kingdoms"]) > 1:
        k1, k2 = random.sample(state["world"]["kingdoms"], 2)
        if k2["id"] not in k1["at_war_with"]:
            k1["at_war_with"].append(k2["id"])
            k2["at_war_with"].append(k1["id"])
            _push_event(state, day, "savaş_ilanı",
                        f"{k1['name']} ile {k2['name']} arasında savaş ilan edildi!")
    if random.random() < 0.03:
        wars = [(k1, k2_id) for k1 in state["world"]["kingdoms"] for k2_id in k1["at_war_with"]]
        if wars:
            k1, k2_id = random.choice(wars)
            k2 = next((k for k in state["world"]["kingdoms"] if k["id"] == k2_id), None)
            if k2:
                k1["at_war_with"] = [x for x in k1["at_war_with"] if x != k2_id]
                k2["at_war_with"] = [x for x in k2["at_war_with"] if x != k1["id"]]
                _push_event(state, day, "barış",
                            f"{k1['name']} ile {k2['name']} arasında barış imzalandı.")
    if random.random() < 0.02:
        k = random.choice(state["world"]["kingdoms"])
        k["stability"] = max(10, k["stability"] - random.randint(5, 20))
        _push_event(state, day, "isyan",
                    f"{k['name']}'de bir lord isyan etti. İstikrar sarsıldı.")
    if random.random() < 0.05:
        loc = random.choice(state["world"]["locations"])
        loc["prosperity"] = min(100, loc["prosperity"] + random.randint(2, 10))
        _push_event(state, day, "şenlik",
                    f"{loc['name']}'de bir şenlik düzenlendi. Halk neşelendi.")


def _generate_quest(state, day):
    """Add 1-2 dynamic quests if quest pool low."""
    active = [q for q in state.get("quests", []) if q["status"] == "açık"]
    if len(active) >= 5:
        return
    quest_templates = [
        ("kayıp_çocuk", "{loc}'de bir çocuk kayboldu. Aileye yardım et.", 50, 80),
        ("mektup", "{loc}'den {loc2}'ye acil bir mektup ulaştırılacak.", 30, 50),
        ("ticaret_fırsatı", "{loc}'de {good} fiyatı düşük. Başka şehirde sat.", 0, 100),
        ("haydut_yuvası", "{loc} yakınlarında bir haydut yuvası var. Temizle.", 100, 200),
        ("yardım", "{loc}'de hasta bir yaşlı şifalı ot bekliyor.", 20, 40),
        ("isyan_hazırlığı", "{loc}'de gizli bir isyan toplantısı var. Sızabilirsin.", 150, 300),
    ]
    n_new = random.randint(0, 2)
    for _ in range(n_new):
        tpl = random.choice(quest_templates)
        locs = state["world"]["locations"]
        loc = random.choice(locs)
        loc2 = random.choice([l for l in locs if l["id"] != loc["id"]])
        good = random.choice(GOODS)
        text = tpl[1].format(loc=loc["name"], loc2=loc2["name"], good=good)
        reward = random.randint(tpl[2], tpl[3]) if tpl[2] < tpl[3] else 50
        state.setdefault("quests", []).append({
            "id": new_id(),
            "type": tpl[0],
            "title": tpl[1].split(".")[0].format(loc=loc["name"], loc2=loc2["name"], good=good),
            "description": text,
            "location_id": loc["id"],
            "location_name": loc["name"],
            "reward": reward,
            "status": "açık",
            "created_day": day,
        })


def _player_tick(state):
    """Player ages slowly, health regen."""
    player = state["player"]
    if random.random() < 0.02:
        player["age"] += 1
    player["health"] = min(100, player["health"] + 1)


def advance_time(state, days=7):
    """Advance the world by `days` days. Default is one week per tick."""
    for _ in range(max(1, days // 7) if days >= 7 else 1):
        state["day"] = state.get("day", 0) + (7 if days >= 7 else days)
        day = state["day"]
        _age_and_die(state, day)
        _marry_and_birth(state, day)
        _economy_tick(state, day)
        _random_events(state, day)
        _generate_quest(state, day)
        _player_tick(state)
        # Trim history to last 200 entries to keep payload reasonable
        if len(state["history"]) > 200:
            state["history"] = state["history"][-200:]
    return state
