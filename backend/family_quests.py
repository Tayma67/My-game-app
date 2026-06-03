"""Family-driven quest system for the child player (age 7-12).

The child is guided by their family (mother + father). These quests
gate early-game progression: completing them trains stats/skills and
teaches the player the systems. After age 13, free-play opens up.

Each quest has stages — completed by performing real actions
(visit a location, deliver an item, work, learn a skill).
"""
import random


# Quest catalog. Each quest is generated once per session.
# action_type: how the player progresses it (auto/use_item/work/travel/chat).
CHILD_QUESTS = [
    {
        "id": "ev_isleri",
        "title": "Annene Yardım Et",
        "giver_role": "anne",
        "min_age": 7,
        "description": ("Annen evi süpürmen ve odun toplamana ihtiyacı olduğunu söylüyor. "
                        "Köyde dolaşıp 3 odun topla."),
        "objective": {"type": "collect", "item": "odun", "qty": 3},
        "reward": {"money": 5, "stat_xp": {"stamina": 10},
                   "skill_xp": {"crafting": 5},
                   "flavor": "Annen başını okşuyor. \"Aferin yavrum, büyüyorsun.\""},
    },
    {
        "id": "ekmek_pisir",
        "title": "Fırından Ekmek Al",
        "giver_role": "anne",
        "min_age": 7,
        "description": "Annen sana üç ekmek alıp eve getirmeni istiyor. Pazardan al.",
        "objective": {"type": "collect", "item": "ekmek", "qty": 3},
        "reward": {"money": 3, "stat_xp": {"charisma": 8, "intelligence": 5},
                   "skill_xp": {"trade": 8},
                   "flavor": "Annen masaya ekmekleri koyarken gülümsüyor."},
    },
    {
        "id": "baba_isi",
        "title": "Babanın Yanında Çalış",
        "giver_role": "baba",
        "min_age": 8,
        "description": ("Baban seni iş başında görmek istiyor. \"İşsiz\" durumunu bırak, "
                        "köylü olarak iki kez çalış."),
        "objective": {"type": "work_count", "qty": 2},
        "reward": {"money": 12, "stat_xp": {"strength": 15, "stamina": 10},
                   "skill_xp": {"crafting": 8},
                   "flavor": "Baban omzuna vuruyor. \"İşte budur, kollarına kuvvet geliyor.\""},
    },
    {
        "id": "kardes_oyun",
        "title": "Komşu Çocukla Tanış",
        "giver_role": "anne",
        "min_age": 7,
        "description": ("Köyde başka bir çocuk var. Onunla konuşup arkadaş ol. "
                        "(Bir NPC ile en az 3 kez sohbet et)"),
        "objective": {"type": "chat_count", "qty": 3},
        "reward": {"money": 0, "stat_xp": {"charisma": 20, "intelligence": 5},
                   "skill_xp": {"social": 12},
                   "flavor": "Yeni bir arkadaşın oldu. Köy artık daha az yabancı."},
    },
    {
        "id": "ilk_silah",
        "title": "Babanın Eski Sopası",
        "giver_role": "baba",
        "min_age": 9,
        "description": ("Baban tavan arasındaki eski tahta sopasını veriyor. "
                        "Onu kuşan ve kendini koru. (Tahta sopayı eline al)"),
        "objective": {"type": "equip", "item": "tahta_sopa"},
        "reward": {"item": {"tahta_sopa": 1},
                   "stat_xp": {"strength": 12},
                   "skill_xp": {"combat": 10},
                   "flavor": "Sopayı hissediyorsun. Artık bir savunman var."},
    },
    {
        "id": "kasaba_gezi",
        "title": "Pazara Git",
        "giver_role": "anne",
        "min_age": 10,
        "description": ("Annen seni ilk kez pazara gönderiyor. Bir şehir veya köye seyahat et "
                        "ve geri dön."),
        "objective": {"type": "travel_count", "qty": 2},
        "reward": {"money": 15, "stat_xp": {"intelligence": 15, "charisma": 8},
                   "skill_xp": {"trade": 10, "social": 5},
                   "flavor": "Pazarı, insanları, kokuları gördün. Dünyan büyüyor."},
    },
    {
        "id": "kus_yakala",
        "title": "Tuzakla Kuş Yakala",
        "giver_role": "baba",
        "min_age": 8,
        "description": "Baban sana tuzak kurmayı öğretmek istiyor. Bir hafta avcılıkta dene (bir hafta tam çalış).",
        "objective": {"type": "work_count", "qty": 7},
        "reward": {"money": 8, "stat_xp": {"strength": 8, "stamina": 12},
                   "skill_xp": {"combat": 5, "crafting": 3},
                   "flavor": "Sabrı öğrendin. Tek bir kuş ele geçirmek bir günü değer."},
    },
    {
        "id": "su_tasi",
        "title": "Kuyudan Su Taşı",
        "giver_role": "anne",
        "min_age": 7,
        "description": "Eve günlük su gerekli. Kuyuya gidip gel (1 seyahat).",
        "objective": {"type": "travel_count", "qty": 1},
        "reward": {"money": 1, "stat_xp": {"stamina": 12, "strength": 5},
                   "skill_xp": {"crafting": 2},
                   "flavor": "Kolların yandı ama kuyudan eve eli boş dönmedin."},
    },
    {
        "id": "ihtiyara_yardim",
        "title": "İhtiyar Komşuya Yardım",
        "giver_role": "anne",
        "min_age": 8,
        "description": ("Sokakta bir ihtiyar yardım bekliyor. NPC'lerle konuşmaya devam et "
                        "(toplam 5 sohbet)."),
        "objective": {"type": "chat_count", "qty": 5},
        "reward": {"money": 4, "stat_xp": {"charisma": 15, "intelligence": 8},
                   "skill_xp": {"social": 10},
                   "flavor": "İhtiyar sana hikâyeler anlattı. Köy seni biraz daha tanıdı."},
    },
    {
        "id": "yagmur_oyunu",
        "title": "Yağmurda Oyun",
        "giver_role": "anne",
        "min_age": 7,
        "description": "Sokağa çık, başka çocuklarla oyna (2 sohbet).",
        "objective": {"type": "chat_count", "qty": 2},
        "reward": {"money": 0, "stat_xp": {"charisma": 8, "stamina": 6},
                   "skill_xp": {"social": 6},
                   "flavor": "Çocukluk anıları kıymetli, bir gün anılarda bunlar olacak."},
    },
    {
        "id": "hikaye_dinle",
        "title": "Babadan Hikâye Dinle",
        "giver_role": "baba",
        "min_age": 9,
        "description": "Baban gece sana eski savaşları anlatmak istiyor. Onunla iki kez konuş.",
        "objective": {"type": "chat_count", "qty": 2},
        "reward": {"money": 0, "stat_xp": {"intelligence": 14, "charisma": 4},
                   "skill_xp": {"social": 4, "combat": 4},
                   "flavor": "Babanın gözlerinde eski savaşlar parladı. Sen de bir parçası oldun."},
    },
    {
        "id": "balik_tut",
        "title": "Dereye İn, Balık Tut",
        "giver_role": "baba",
        "min_age": 10,
        "description": "Baban seni dereye gönderiyor. Sabırla çalış (4 iş günü).",
        "objective": {"type": "work_count", "qty": 4},
        "reward": {"money": 10, "stat_xp": {"stamina": 10, "intelligence": 8},
                   "skill_xp": {"crafting": 6},
                   "flavor": "Balıkları temizledin, akşam yemekte sofranızda."},
    },
    {
        "id": "yetiskinlige_hazirlik",
        "title": "Yetişkinliğe Hazırlık",
        "giver_role": "baba",
        "min_age": 12,
        "description": ("Baban diyor ki: '13'üne gelmek üzeresin. Bir silah seç ve bir hafta çalış.' "
                        "Tahta sopayı kuşan ve bir hafta tam çalış."),
        "objective": {"type": "work_count", "qty": 7},
        "reward": {"item": {"tahta_sopa": 1},
                   "stat_xp": {"strength": 20, "stamina": 15, "intelligence": 10},
                   "skill_xp": {"combat": 12, "crafting": 5},
                   "flavor": "Baban kafanı okşadı. \"Artık adam/kız oluyorsun.\""},
    },
]


def make_family_quests(state, mother_id, father_id):
    """Initialize all child quests in `pending` state for this player."""
    quests = []
    for q in CHILD_QUESTS:
        giver = mother_id if q["giver_role"] == "anne" else father_id
        quests.append({
            "id": q["id"],
            "title": q["title"],
            "description": q["description"],
            "giver_id": giver,
            "giver_role": q["giver_role"],
            "min_age": q["min_age"],
            "objective": q["objective"],
            "reward": q["reward"],
            "progress": 0,
            "status": "kilitli",  # kilitli | açık | tamamlandı
            "type": "family",
        })
    return quests


def unlock_age_appropriate(state):
    """Mark quests as 'açık' when player reaches min_age. Returns list of newly unlocked."""
    from calendar_tr import player_age
    age = player_age(state)
    newly = []
    for q in state.get("family_quests", []):
        if q["status"] == "kilitli" and age >= q["min_age"]:
            q["status"] = "açık"
            newly.append(q)
    return newly


def progress_quest(state, action_type, payload=None):
    """Advance any open quest whose objective matches the action.

    action_type: 'work' | 'chat' | 'travel' | 'equip' | 'inventory_changed'
    payload: dict — for chat: {npc_id}; for travel: {location_id}; for equip: {item}
    Returns list of completed quest ids.
    """
    payload = payload or {}
    completed = []
    inv = state.get("player", {}).get("inventory", {})
    equipment = state.get("player", {}).get("equipment", {})

    for q in state.get("family_quests", []):
        if q["status"] != "açık":
            continue
        obj = q["objective"]
        otype = obj["type"]
        done = False

        if otype == "collect" and action_type == "inventory_changed":
            qty = inv.get(obj["item"], 0)
            q["progress"] = min(qty, obj["qty"])
            if qty >= obj["qty"]:
                done = True
        elif otype == "work_count" and action_type == "work":
            q["progress"] = min(q.get("progress", 0) + 1, obj["qty"])
            if q["progress"] >= obj["qty"]:
                done = True
        elif otype == "chat_count" and action_type == "chat":
            q["progress"] = min(q.get("progress", 0) + 1, obj["qty"])
            if q["progress"] >= obj["qty"]:
                done = True
        elif otype == "travel_count" and action_type == "travel":
            q["progress"] = min(q.get("progress", 0) + 1, obj["qty"])
            if q["progress"] >= obj["qty"]:
                done = True
        elif otype == "equip" and action_type == "equip":
            if any(v == obj["item"] for v in equipment.values()):
                q["progress"] = 1
                done = True

        if done:
            q["status"] = "tamamlandı"
            _apply_reward(state, q)
            completed.append(q["id"])
    return completed


def _apply_reward(state, quest):
    """Apply quest reward to player."""
    from skills import add_stat_xp, add_skill_xp
    player = state["player"]
    reward = quest.get("reward", {})
    if reward.get("money"):
        player["money"] = round(player.get("money", 0) + reward["money"], 1)
    if reward.get("item"):
        inv = player.setdefault("inventory", {})
        for k, v in reward["item"].items():
            inv[k] = inv.get(k, 0) + v
    for stat, xp in (reward.get("stat_xp") or {}).items():
        add_stat_xp(player, stat, xp)
    for skill, xp in (reward.get("skill_xp") or {}).items():
        add_skill_xp(player, skill, xp)
    state.setdefault("history", []).append({
        "id": __import__("uuid").uuid4().hex[:16],
        "day": state.get("turn", 0),
        "type": "aile_görevi",
        "text": f"Aile görevi tamamlandı: {quest['title']}. {reward.get('flavor', '')}",
    })
