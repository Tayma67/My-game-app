"""Stats, jobs, and skill tree.

Stats: strength, intelligence, charisma, stamina (each 1-10)
Skill trees: combat, trade, crafting, social (each 0-10; unlock perks at thresholds)

Jobs require minimum stats and minimum age.
Each profession trains specific skills when /work is called.
"""

STAT_KEYS = ["strength", "intelligence", "charisma", "stamina"]
SKILL_KEYS = ["combat", "trade", "crafting", "social"]


JOB_REQUIREMENTS = {
    "işsiz":            {"age": 0,  "stats": {},                                              "skill": {}},
    "köylü":            {"age": 7,  "stats": {"strength": 2, "stamina": 2},                   "skill": {}},
    "çiftçi":           {"age": 10, "stats": {"strength": 3, "stamina": 3},                   "skill": {}},
    "avcı":             {"age": 12, "stats": {"stamina": 4, "intelligence": 3},               "skill": {}},
    "demirci çırağı":   {"age": 13, "stats": {"strength": 4, "stamina": 3},                   "skill": {}},
    "demirci":          {"age": 16, "stats": {"strength": 6, "stamina": 5},                   "skill": {"crafting": 3}},
    "tüccar":           {"age": 14, "stats": {"charisma": 5, "intelligence": 4},              "skill": {"trade": 2}},
    "asker":            {"age": 16, "stats": {"strength": 5, "stamina": 5},                   "skill": {"combat": 2}},
    "şövalye":          {"age": 18, "stats": {"strength": 7, "stamina": 6, "charisma": 4},    "skill": {"combat": 5}},
    "haydut":           {"age": 14, "stats": {"strength": 4, "stamina": 3},                   "skill": {}},
    "şifacı":           {"age": 16, "stats": {"intelligence": 6, "charisma": 4},              "skill": {"crafting": 3}},
    "zanaatkar":        {"age": 14, "stats": {"intelligence": 4, "strength": 3},              "skill": {"crafting": 2}},
    "katip":            {"age": 14, "stats": {"intelligence": 6},                             "skill": {"social": 2}},
    "rahip":            {"age": 18, "stats": {"intelligence": 5, "charisma": 6},              "skill": {"social": 4}},
    "lord":             {"age": 18, "stats": {"charisma": 6, "strength": 5, "intelligence": 5}, "skill": {"combat": 5, "social": 4}},
}


# Job → skill XP gained per /work tick (per turn)
JOB_SKILL_TRAINING = {
    "çiftçi":           {"crafting": 1, "stamina_xp": 1},
    "köylü":            {"stamina_xp": 1},
    "avcı":             {"combat": 1, "stamina_xp": 1},
    "demirci çırağı":   {"crafting": 2, "strength_xp": 1},
    "demirci":          {"crafting": 2, "strength_xp": 1},
    "tüccar":           {"trade": 2, "social": 1, "charisma_xp": 1},
    "asker":            {"combat": 2, "strength_xp": 1, "stamina_xp": 1},
    "şövalye":          {"combat": 3, "strength_xp": 1},
    "haydut":           {"combat": 1, "trade": 1},
    "şifacı":           {"crafting": 1, "social": 1, "intelligence_xp": 1},
    "zanaatkar":        {"crafting": 2, "intelligence_xp": 1},
    "katip":            {"social": 2, "intelligence_xp": 1},
    "rahip":            {"social": 2, "intelligence_xp": 1, "charisma_xp": 1},
    "lord":             {"social": 1, "combat": 1, "charisma_xp": 1},
    "işsiz":            {},
}


# Skill tree perks: skill level → unlocked perk key + description
SKILL_PERKS = {
    "combat": [
        (3, "iki_el", "İki elli saldırı — saldırı +%15"),
        (6, "ustaca_savunma", "Ustaca savunma — alınan hasar -%20"),
        (9, "katil", "Ölümcül vuruş — kritik şansı +%25"),
    ],
    "trade": [
        (3, "pazarlık", "Pazarlık — alışta %10 indirim, satışta %10 zam"),
        (6, "kervan", "Kervan rotası — uzun seyahatlerde para kazanırsın"),
        (9, "tüccar_lordu", "Tüccar Lordu — kentlerde özel fiyatlar"),
    ],
    "crafting": [
        (3, "tamir", "Tamir — silah/zırh dayanıklılığı artar"),
        (6, "kaliteli_üretim", "Kaliteli üretim — sattığın ürün %20 fazla para getirir"),
        (9, "usta_zanaatkar", "Usta zanaatkar — nadir eşyalar yapabilirsin"),
    ],
    "social": [
        (3, "ikna", "İkna — diyalog ilişki kazançları +1"),
        (6, "etki", "Etki — soyluların eşiği -1"),
        (9, "lider", "Lider — büyük gruplar seni dinler"),
    ],
}


def get_age_group(age):
    if age < 13:
        return "çocuk"
    if age < 18:
        return "ergen"
    if age < 50:
        return "yetişkin"
    if age < 65:
        return "olgun"
    return "yaşlı"


def check_job_eligible(player, job):
    """Returns (ok: bool, reasons: list[str])"""
    req = JOB_REQUIREMENTS.get(job)
    if not req:
        return False, [f"'{job}' geçerli bir meslek değil."]
    reasons = []
    if player.get("age", 0) < req["age"]:
        reasons.append(f"Yaş yetersiz ({req['age']}+ gerekli, sen {player.get('age')})")
    stats = player.get("stats", {})
    for s, v in req["stats"].items():
        if stats.get(s, 0) < v:
            reasons.append(f"{s}: {stats.get(s, 0)}/{v}")
    skills = player.get("skills", {})
    for s, v in req["skill"].items():
        if skills.get(s, 0) < v:
            reasons.append(f"{s} skill: {skills.get(s, 0)}/{v}")
    return len(reasons) == 0, reasons


def list_eligible_jobs(player):
    out = []
    for job in JOB_REQUIREMENTS.keys():
        ok, reasons = check_job_eligible(player, job)
        out.append({"job": job, "eligible": ok, "missing": reasons,
                    "requirements": JOB_REQUIREMENTS[job]})
    return out


# XP needed to gain a skill level
def xp_for_next_skill_level(current_level):
    return 10 + current_level * 5


def xp_for_next_stat_level(current_level):
    return 25 + current_level * 15


def add_skill_xp(player, skill, xp):
    """Apply xp to a skill; level up if threshold reached. Returns new level if leveled up else None."""
    skills = player.setdefault("skills", {})
    skill_xp = player.setdefault("skill_xp", {})
    if skill not in skills:
        skills[skill] = 0
    if skill not in skill_xp:
        skill_xp[skill] = 0
    skill_xp[skill] += xp
    leveled = None
    while skills[skill] < 10 and skill_xp[skill] >= xp_for_next_skill_level(skills[skill]):
        skill_xp[skill] -= xp_for_next_skill_level(skills[skill])
        skills[skill] += 1
        leveled = skills[skill]
    return leveled


def add_stat_xp(player, stat, xp):
    """Slower than skill XP. Stats cap at 10."""
    stats = player.setdefault("stats", {})
    stat_xp = player.setdefault("stat_xp", {})
    if stat not in stats:
        stats[stat] = 1
    if stat not in stat_xp:
        stat_xp[stat] = 0
    stat_xp[stat] += xp
    leveled = None
    while stats[stat] < 10 and stat_xp[stat] >= xp_for_next_stat_level(stats[stat]):
        stat_xp[stat] -= xp_for_next_stat_level(stats[stat])
        stats[stat] += 1
        leveled = stats[stat]
    return leveled


def apply_work_training(player, profession, multiplier=1):
    """When player works one turn, distribute XP gains."""
    training = JOB_SKILL_TRAINING.get(profession, {})
    leveled = []
    for key, xp in training.items():
        xp = xp * multiplier
        if key.endswith("_xp"):
            stat = key.replace("_xp", "")
            lvl = add_stat_xp(player, stat, xp)
            if lvl is not None:
                leveled.append(("stat", stat, lvl))
        else:
            lvl = add_skill_xp(player, key, xp)
            if lvl is not None:
                leveled.append(("skill", key, lvl))
    return leveled


def unlocked_perks(player):
    out = []
    skills = player.get("skills", {})
    for skill, perks in SKILL_PERKS.items():
        for threshold, key, desc in perks:
            if skills.get(skill, 0) >= threshold:
                out.append({"skill": skill, "level": threshold, "perk": key, "desc": desc})
    return out


def has_perk(player, perk_key):
    return any(p["perk"] == perk_key for p in unlocked_perks(player))
