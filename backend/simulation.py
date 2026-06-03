"""World simulation: weekly tick (1 turn = 1 week). Ages NPCs/player, marriages,
births, deaths, real economy, hunger, seasons, NPC profiles & rumors.
"""
import random
from world_gen import (
    new_id, MALE_NAMES, FEMALE_NAMES, SURNAMES, GOODS, GOOD_BASE_PRICES,
    PROFESSIONS_COMMON, PERSONALITY_TRAITS,
)
from calendar_tr import (
    WEEKS_PER_YEAR, SEASON_EFFECTS, season_for_turn, current_calendar, player_age,
)
from npc_profile import (
    ensure_profile, push_recent_event, npc_weekly_tick, recompute_mood,
)
from rumors import auto_rumors_from_events, seasonal_rumors


PRODUCTION = {
    "çiftçi": ("buğday", 10),
    "fırıncı": ("ekmek", 8),
    "avcı": ("et", 6),
    "balıkçı": ("et", 5),
    "çoban": ("et", 3),
    "demirci": ("demir", 3),
    "marangoz": ("odun", 7),
    "değirmenci": ("buğday", 5),
    "tüccar": (None, 0),  # they move goods but don't produce
    "kunduracı": ("kumaş", 3),
}

PROFESSION_NEEDS = {
    "asker": ("silah", 1),
    "şövalye": ("silah", 1),
}


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


def _ensure_market(loc):
    """Migrate old loc.prices to loc.market{good: {price, supply, demand, base}}"""
    if "market" in loc and loc["market"]:
        return
    market = {}
    pop = loc.get("population", 100)
    for g in GOODS:
        base = GOOD_BASE_PRICES[g]
        current_price = loc.get("prices", {}).get(g, base)
        # Initial supply ~ population fraction; demand similar.
        market[g] = {
            "price": current_price,
            "base": base,
            "supply": max(5, int(pop * random.uniform(0.05, 0.15))),
            "demand": max(5, int(pop * random.uniform(0.05, 0.15))),
        }
    loc["market"] = market
    loc["prices"] = {g: market[g]["price"] for g in GOODS}


def _recompute_prices(loc):
    """Price formula: base * (demand / max(1, supply))^0.4 * wealth_factor."""
    wealth_factor = 0.6 + (loc["wealth"] / 100)
    security_factor = 0.7 + (loc["security"] / 100) * 0.6
    for g, m in loc["market"].items():
        ratio = m["demand"] / max(1, m["supply"])
        target = m["base"] * (ratio ** 0.45) * wealth_factor * security_factor
        # Smooth toward target
        m["price"] = round(max(0.5, m["price"] * 0.65 + target * 0.35), 2)
    loc["prices"] = {g: loc["market"][g]["price"] for g in GOODS}


def _ensure_npc_fields(npc):
    npc.setdefault("interactions", {})
    npc.setdefault("memory", [])
    npc.setdefault("personal_events", [])
    npc.setdefault("bounty", 0)
    npc.setdefault("turn_counter", 0)
    ensure_profile(npc)


def _ensure_state_fields(state):
    state.setdefault("relationships", {})
    state.setdefault("quests", [])
    state.setdefault("day", 0)
    state.setdefault("turn", state.get("day", 0))  # legacy: day = turn (weeks)
    state.setdefault("history", [])
    state.setdefault("family_quests", [])
    state.setdefault("rumors", [])
    p = state["player"]
    p.setdefault("crime", 0)
    p.setdefault("reputation", 0)
    p.setdefault("wanted_in", [])
    p.setdefault("interaction_counts", {})
    p.setdefault("dead", False)
    p.setdefault("hunger", 100)
    p.setdefault("base_age", p.get("age", 7))
    p.setdefault("stats", {"strength": 1, "intelligence": 1, "charisma": 1, "stamina": 2})
    p.setdefault("stat_xp", {"strength": 0, "intelligence": 0, "charisma": 0, "stamina": 0})
    p.setdefault("skills", {"combat": 0, "trade": 0, "crafting": 0, "social": 0})
    p.setdefault("skill_xp", {"combat": 0, "trade": 0, "crafting": 0, "social": 0})
    p.setdefault("buffs", {})
    p.setdefault("equipment", {"weapon": None, "head": None, "body": None,
                               "hands": None, "legs": None, "feet": None})
    p.setdefault("work_units", 0)  # 7 units = 1 week of work
    p.setdefault("stat_points", 0)
    p["age"] = player_age(state)
    for loc in state["world"]["locations"]:
        _ensure_market(loc)
    for npc in state["world"]["npcs"]:
        _ensure_npc_fields(npc)


# ---------- NPC life events ----------
def _age_and_die(state, day):
    """Weekly tick: 1/WEEKS_PER_YEAR chance to age per week (so ~1yr per cycle)."""
    age_chance = 1.0 / WEEKS_PER_YEAR
    for npc in [n for n in state["world"]["npcs"] if n["alive"]]:
        if random.random() < age_chance:
            npc["age"] += 1
        # Slow health drift
        if random.random() < 0.08:
            npc["health"] = max(0, npc["health"] - random.randint(0, 1))
        death_chance = 0.0002 + max(0, (npc["age"] - 55)) * 0.0006
        if npc["health"] < 20:
            death_chance += 0.02
        if random.random() < death_chance:
            npc["alive"] = False
            # Notify family
            for nid in (npc.get("children_ids") or []) + ([npc.get("spouse_id")] if npc.get("spouse_id") else []):
                fam = next((x for x in state["world"]["npcs"] if x["id"] == nid and x["alive"]), None)
                if fam:
                    push_recent_event(fam, "spouse_lost" if fam.get("spouse_id") == npc["id"] else "friend_died", day)
            _push_event(state, day, "ölüm",
                        f"{npc['name']} ({npc['age']}) {npc['location_name']}'de hayata gözlerini yumdu.")
            # Mark relatives' personal events
            for rid in [npc["spouse_id"]] + list(npc["children_ids"]) + list(npc["parent_ids"]):
                if not rid or rid == "PLAYER":
                    continue
                rel = next((n for n in state["world"]["npcs"] if n["id"] == rid and n["alive"]), None)
                if rel:
                    kind = "eş_kaybı" if rid == npc["spouse_id"] else ("çocuk_kaybı" if rid in npc["children_ids"] else "ata_kaybı")
                    rel.setdefault("personal_events", []).append({
                        "type": kind, "day": day, "of": npc["name"],
                    })
                    # Mood drops
                    if rel["mood"] not in ("öfkeli",):
                        rel["mood"] = "umutsuz"
            # If npc was player's spouse
            if npc.get("spouse_id") == "PLAYER":
                state["player"]["spouse_id"] = None
            # Royal succession
            kingdom = next((k for k in state["world"]["kingdoms"] if k["king_id"] == npc["id"]), None)
            if kingdom:
                heir = next((n for n in state["world"]["npcs"] if n["id"] == kingdom["heir_id"] and n["alive"]), None)
                if heir:
                    heir["profession"] = "kral"
                    kingdom["king_id"] = heir["id"]
                    _push_event(state, day, "tahta_çıkış",
                                f"{heir['name']}, {kingdom['name']} tahtına çıktı.")
                    # new heir
                    new_heir = next(
                        (c for c in state["world"]["npcs"]
                         if c["alive"] and heir["id"] in c["parent_ids"]),
                        None,
                    )
                    if not new_heir:
                        candidates = [n for n in state["world"]["npcs"]
                                      if n["alive"] and n["kingdom_id"] == kingdom["id"]
                                      and 16 <= n["age"] <= 35 and n["profession"] != "kral"]
                        new_heir = random.choice(candidates) if candidates else None
                    if new_heir:
                        new_heir["profession"] = "veliaht"
                        kingdom["heir_id"] = new_heir["id"]


def _marry_and_birth(state, day):
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
            a.setdefault("personal_events", []).append({"type": "evlilik", "day": day, "of": b["name"]})
            b.setdefault("personal_events", []).append({"type": "evlilik", "day": day, "of": a["name"]})
            push_recent_event(a, "spouse_married", day, b["name"])
            push_recent_event(b, "spouse_married", day, a["name"])
            used.add(a["id"]); used.add(b["id"])
            _push_event(state, day, "evlilik",
                        f"{a['name']} ile {b['name']}, {a['location_name']}'de dünya evine girdi.")
            break

    couples_seen = set()
    for a in npcs:
        if not a["spouse_id"] or a["gender"] != "kadın":
            continue
        if a["spouse_id"] == "PLAYER":
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
                "gender": gender, "age": 0, "profession": "çocuk",
                "personality": random.sample(PERSONALITY_TRAITS, 2),
                "wealth": 0, "health": 90,
                "kingdom_id": a["kingdom_id"], "kingdom_name": a["kingdom_name"],
                "religion": a["religion"], "location_id": a["location_id"],
                "location_name": a["location_name"],
                "spouse_id": None, "children_ids": [],
                "parent_ids": [a["id"], partner["id"]],
                "friend_ids": [], "rival_ids": [],
                "goal": "büyümek", "mood": "huzurlu", "alive": True,
                "interactions": {}, "memory": [], "personal_events": [],
                "bounty": 0, "turn_counter": 0,
            }
            a["children_ids"].append(child["id"])
            partner["children_ids"].append(child["id"])
            a["personal_events"].append({"type": "doğum", "day": day, "of": child["name"]})
            partner.setdefault("personal_events", []).append({"type": "doğum", "day": day, "of": child["name"]})
            push_recent_event(a, "child_born", day, child["name"])
            push_recent_event(partner, "child_born", day, child["name"])
            state["world"]["npcs"].append(child)
            _push_event(state, day, "doğum",
                        f"{a['name']} ve {partner['name']}'in çocuğu {child['name']} doğdu.")


# ---------- Economy ----------
def _economy_tick(state, day):
    season = season_for_turn(state.get("turn", 0))
    prod_mult = SEASON_EFFECTS[season]["production_mult"]
    npcs_by_loc = {}
    for n in state["world"]["npcs"]:
        if not n["alive"]:
            continue
        npcs_by_loc.setdefault(n["location_id"], []).append(n)

    for loc in state["world"]["locations"]:
        _ensure_market(loc)
        local_npcs = npcs_by_loc.get(loc["id"], [])
        pop = max(10, loc.get("population", 50))

        # Production from NPC professions (seasonal multiplier)
        for n in local_npcs:
            prod = PRODUCTION.get(n["profession"])
            if prod and prod[0]:
                good, amt = prod
                noise = random.uniform(0.7, 1.3)
                loc["market"][good]["supply"] += max(1, int(amt * noise * prod_mult))

        # Background production scaled to population (so cities don't starve when only a few NPCs are here)
        bg = max(2, pop // 25)
        for good in ("buğday", "ekmek", "et", "odun"):
            loc["market"][good]["supply"] += int(bg * prod_mult * random.uniform(0.6, 1.2))

        # NPC consumption drives demand
        for good, frac in [("ekmek", 0.012), ("buğday", 0.010), ("et", 0.006),
                           ("odun", 0.004), ("kumaş", 0.002), ("demir", 0.002),
                           ("silah", 0.001)]:
            consume = max(1, int(pop * frac))
            # Demand grows
            loc["market"][good]["demand"] += consume
            # Supply is depleted by consumption (but can't go negative)
            loc["market"][good]["supply"] = max(0, loc["market"][good]["supply"] - consume)

        # NPC needs (soldiers want weapons)
        for n in local_npcs:
            need = PROFESSION_NEEDS.get(n["profession"])
            if need:
                good, amt = need
                loc["market"][good]["demand"] += amt

        # Decay demand & supply slightly (memory effect)
        for good in GOODS:
            m = loc["market"][good]
            m["demand"] = int(m["demand"] * 0.85)
            m["supply"] = int(m["supply"] * 0.90)
            # Floors
            m["demand"] = max(1, m["demand"])
            m["supply"] = max(0, m["supply"])

        _recompute_prices(loc)

        # Slow drift on wealth/security
        loc["wealth"] = max(5, min(100, loc["wealth"] + random.randint(-2, 2)))
        loc["security"] = max(5, min(100, loc["security"] + random.randint(-3, 3)))
        loc["prosperity"] = max(5, min(100, round((loc["wealth"] + loc["security"]) / 2)))

    # NPC merchant arbitrage: pick a few merchants, move 1 unit from cheap loc to expensive loc
    merchants = [n for n in state["world"]["npcs"] if n["alive"] and n["profession"] == "tüccar"]
    random.shuffle(merchants)
    for m in merchants[:min(8, len(merchants))]:
        good = random.choice(GOODS)
        # Find cheapest and most expensive locations for this good
        priced = [(l, l["market"][good]["price"]) for l in state["world"]["locations"]]
        cheap = min(priced, key=lambda x: x[1])
        expensive = max(priced, key=lambda x: x[1])
        if expensive[1] > cheap[1] * 1.2 and cheap[0]["market"][good]["supply"] > 5:
            qty = random.randint(1, 5)
            cheap[0]["market"][good]["supply"] = max(0, cheap[0]["market"][good]["supply"] - qty)
            expensive[0]["market"][good]["supply"] += qty
            expensive[0]["market"][good]["demand"] = max(1, expensive[0]["market"][good]["demand"] - qty // 2)
            _recompute_prices(cheap[0])
            _recompute_prices(expensive[0])


# ---------- World events ----------
def _random_events(state, day):
    if random.random() < 0.08:
        loc = random.choice(state["world"]["locations"])
        loc["security"] = max(5, loc["security"] - random.randint(5, 20))
        _push_event(state, day, "haydut_baskını",
                    f"Haydutlar {loc['name']}'i bastı. Güvenlik düştü.")
    if random.random() < 0.05:
        loc = random.choice([l for l in state["world"]["locations"] if l["kind"] != "kale"])
        loc["wealth"] = max(5, loc["wealth"] - random.randint(5, 15))
        # Crop failure: drop wheat supply
        loc["market"]["buğday"]["supply"] = max(0, loc["market"]["buğday"]["supply"] - 20)
        _recompute_prices(loc)
        _push_event(state, day, "kıtlık",
                    f"{loc['name']}'de kötü hasat: buğday arzı düştü, fiyatlar yükseldi.")
    if random.random() < 0.04 and len(state["world"]["kingdoms"]) > 1:
        k1, k2 = random.sample(state["world"]["kingdoms"], 2)
        if k2["id"] not in k1["at_war_with"]:
            k1["at_war_with"].append(k2["id"])
            k2["at_war_with"].append(k1["id"])
            _push_event(state, day, "savaş_ilanı",
                        f"{k1['name']} ile {k2['name']} arasında savaş ilan edildi!")
            # War drives weapon demand
            for loc in state["world"]["locations"]:
                if loc["kingdom_id"] in (k1["id"], k2["id"]):
                    loc["market"]["silah"]["demand"] += 30
                    _recompute_prices(loc)
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
            "id": new_id(), "type": tpl[0],
            "title": tpl[1].split(".")[0].format(loc=loc["name"], loc2=loc2["name"], good=good),
            "description": text,
            "location_id": loc["id"], "location_name": loc["name"],
            "reward": reward, "status": "açık", "created_day": day,
        })


def _npc_profile_tick(state, day):
    """Each living NPC gets a daily_life activity + small mood drift + maybe a recent_event."""
    rng = random.Random(day * 7919)
    for n in state["world"]["npcs"]:
        if not n["alive"]:
            continue
        ensure_profile(n)
        npc_weekly_tick(n, state, rng)


def _family_support_tick(state, day):
    """Child player (< 13) gets weekly support from living parents."""
    player = state["player"]
    if player["age"] >= 13:
        return
    parent_ids = player.get("parent_ids") or []
    living_parents = [n for n in state["world"]["npcs"] if n["id"] in parent_ids and n["alive"]]
    if not living_parents:
        return
    bread = 0
    coin = 0
    for parent in living_parents:
        # Each parent contributes based on their wealth
        if random.random() < 0.85:
            bread += 1
        if parent.get("savings", 0) > 10:
            give = random.randint(1, 3)
            coin += give
            parent["savings"] = max(0, parent.get("savings", 0) - give)
    if bread > 0:
        inv = player.setdefault("inventory", {})
        inv["ekmek"] = inv.get("ekmek", 0) + bread
    if coin > 0:
        player["money"] = round(player["money"] + coin, 1)
    if bread > 0 or coin > 0:
        _push_event(state, day, "aile_destek",
                    f"Ailen sana baktı: +{bread} ekmek, +{coin} altın.")


def _player_tick(state):
    """Weekly tick for player: hunger, age, buffs decay."""
    player = state["player"]
    season = season_for_turn(state.get("turn", 0))
    hunger_mult = SEASON_EFFECTS[season]["hunger_mult"]
    # Hunger -5 per week (modified by season). Stamina passive lowers loss slightly.
    sta = player.get("stats", {}).get("stamina", 1)
    loss = max(2, int(round(5 * hunger_mult - sta * 0.15)))
    player["hunger"] = max(0, player.get("hunger", 100) - loss)
    # Starvation damage
    if player["hunger"] <= 0:
        player["health"] = max(0, player["health"] - 2)
    else:
        # Slow regen
        player["health"] = min(100, player["health"] + 1)
    # Update derived age
    player["age"] = player_age(state)
    # Decay temporary buffs
    buffs = player.get("buffs") or {}
    for k in list(buffs.keys()):
        buffs[k] = max(0, buffs[k] - 1) if buffs[k] > 0 else min(0, buffs[k] + 1)
        if buffs[k] == 0:
            buffs.pop(k, None)
    # Death by old age
    if player["age"] > 70 and random.random() < 0.02:
        player["dead"] = True
    if player["health"] <= 0:
        player["dead"] = True


def advance_time(state, weeks=1, days=None):
    """Advance the world by N weeks. `days` kept for backwards compatibility (1 day = 1/7 week)."""
    _ensure_state_fields(state)
    if days is not None and weeks == 1:
        # Legacy days input
        weeks = max(1, int(round(days / 7)))
    weeks = max(1, int(weeks))
    for _ in range(weeks):
        state["turn"] = state.get("turn", 0) + 1
        state["day"] = state["turn"]
        day = state["turn"]
        prev_history_len = len(state.get("history", []))
        _age_and_die(state, day)
        _marry_and_birth(state, day)
        _economy_tick(state, day)
        _random_events(state, day)
        _generate_quest(state, day)
        _npc_profile_tick(state, day)
        _family_support_tick(state, day)
        _player_tick(state)
        # Generate rumors from new history events this tick
        new_events = state["history"][prev_history_len:]
        if new_events:
            auto_rumors_from_events(state, new_events)
        seasonal_rumors(state)
        if len(state["history"]) > 250:
            state["history"] = state["history"][-250:]
    # Auto-unlock family quests at the end of advancement
    try:
        from family_quests import unlock_age_appropriate
        newly = unlock_age_appropriate(state)
        for q in newly:
            _push_event(state, state["turn"], "aile_görevi_açıldı",
                        f"Yeni aile görevi: {q['title']}")
    except Exception:
        pass
    return state


# ---------- Soldier enforcement ----------
def soldier_check(state):
    """Check if player crime is high and there are soldiers nearby — apply consequence.

    Returns: dict or None
    """
    player = state["player"]
    if player.get("crime", 0) < 30:
        return None
    loc = next((l for l in state["world"]["locations"] if l["id"] == player["location_id"]), None)
    if not loc:
        return None
    # Find living soldiers/lords in this location
    enforcers = [n for n in state["world"]["npcs"]
                 if n["alive"] and n["location_id"] == loc["id"]
                 and n["profession"] in ("asker", "lord", "şövalye", "general")]
    if not enforcers:
        return None
    chance = min(0.85, (player["crime"] - 20) / 100 + (loc["security"] / 200))
    if random.random() > chance:
        return None
    # Apply punishment
    fine = min(player.get("money", 0), 50 + player["crime"] * 2)
    player["money"] = round(player.get("money", 0) - fine, 1)
    player["reputation"] -= 3
    enforcer = random.choice(enforcers)
    if player["crime"] >= 80:
        # Imprisonment: skip several weeks, reset crime partially
        weeks_in_jail = random.randint(2, 6)
        player["crime"] = max(0, player["crime"] - 50)
        _push_event(state, state["day"], "hapis",
                    f"{player['name']} {loc['name']}'de tutuklandı, {weeks_in_jail} hafta zindanda kaldı.")
        # advance silently
        advance_time(state, weeks=weeks_in_jail)
        return {"type": "hapis", "by": enforcer["name"], "fine": fine, "weeks": weeks_in_jail}
    else:
        player["crime"] = max(0, player["crime"] - 10)
        _push_event(state, state["day"], "yakalandı",
                    f"{player['name']}, {enforcer['name']} tarafından yakalandı, {fine} altın ceza ödedi.")
        return {"type": "ceza", "by": enforcer["name"], "fine": fine}
