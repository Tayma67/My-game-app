"""NPC Deepening Package V1 — goals, moods, recent events, personal memory, daily life.

This module ADDS new behavioural layers on top of existing NPCs without
replacing any current fields.

Backwards compatible: every accessor calls `ensure_profile(npc)` first to
lazily migrate old NPCs.
"""
import random


# ---------------- Life goals ----------------
GOALS = [
    {"key": "zengin_olmak",     "label": "Zengin olmak",       "domain": "wealth"},
    {"key": "evlenmek",         "label": "Evlenmek",           "domain": "family"},
    {"key": "cocuk_sahibi",     "label": "Çocuk sahibi olmak", "domain": "family"},
    {"key": "aileyi_buyutmek",  "label": "Aileyi büyütmek",    "domain": "family"},
    {"key": "lord_olmak",       "label": "Lord olmak",         "domain": "power"},
    {"key": "tuccar_olmak",     "label": "Tüccar olmak",       "domain": "career"},
    {"key": "asker_olmak",      "label": "Asker olmak",        "domain": "career"},
    {"key": "intikam_almak",    "label": "İntikam almak",      "domain": "vengeance"},
    {"key": "borc_odemek",      "label": "Borçlarından kurtulmak", "domain": "wealth"},
    {"key": "saygi_kazanmak",   "label": "Saygı kazanmak",     "domain": "social"},
    {"key": "evine_donmek",     "label": "Evine dönmek",       "domain": "personal"},
    {"key": "usta_olmak",       "label": "Sanatında usta olmak", "domain": "career"},
]

GOAL_BY_KEY = {g["key"]: g for g in GOALS}

GOAL_TALK = {
    "zengin_olmak": [
        "Bir gün cebim altın dolu olacak, herkesin yüzüne bakacağım.",
        "Para her şeyi çözer, bunu öğrendim.",
        "Köyün en zengini olmadan ölmeyeceğim.",
    ],
    "evlenmek": [
        "İyi bir eş bulsam, hayatım yerine otururdu.",
        "Yalnızlık insanı kemiriyor, bilsen.",
        "Belki sana uygun biri vardır gözünde?",
    ],
    "cocuk_sahibi": [
        "Bir çocuğum olsa, gece uyuyabilirim sanırım.",
        "Soyumun devam etmesi lazım, başka ne var ki?",
    ],
    "aileyi_buyutmek": [
        "Bir oğlumun daha olmasını isterim, kollarım için.",
        "Aile dediğin kalabalık olmalı.",
    ],
    "lord_olmak": [
        "Bu eller bir kale tutacak günü görür inşallah.",
        "Lordluğa giden yol kanlı, ama benim için açık.",
    ],
    "tuccar_olmak": [
        "Bir gün kendi kervanım olacak.",
        "Şimdilik ufak alıp satıyorum, hesabım büyük.",
    ],
    "asker_olmak": [
        "Bir gün lordun sancağı altında savaşacağım.",
        "Bu kollar saban için fazla, kılıç için biçilmiş kaftan.",
    ],
    "intikam_almak": [
        "Bir kişi var, onun ölümünü bekliyorum.",
        "İntikam soğuk yenirse daha tatlı derler, doğru.",
    ],
    "borc_odemek": [
        "Boğazımda bir borç düğümü var, çözemiyorum.",
        "Tefeci kapımı aşındırıyor, bir an önce ödesem...",
    ],
    "saygi_kazanmak": [
        "Adımın anılmasını istiyorum, kötülükle değil.",
        "İnsanların selam vermesi yeter bana.",
    ],
    "evine_donmek": [
        "Doğduğum kasaba uzakta kaldı, bir gün döneceğim.",
        "Bu topraklar yabancı, kalbim hep oraya bakıyor.",
    ],
    "usta_olmak": [
        "Sanatımda usta olmadan rahat yüzü göremem.",
        "Eski ustalar gibi anılmak istiyorum.",
    ],
}


# ---------------- Moods ----------------
MOODS = ["mutlu", "üzgün", "öfkeli", "korkmuş", "umutlu", "stresli", "heyecanlı", "huzurlu"]

MOOD_GREETING = {
    "mutlu":     ["Bugün keyfim yerinde, sözünü esirgeme.", "İçim açık, ne istersen sor."],
    "üzgün":     ["Pek konuşacak halde değilim.", "İçim daralıyor son zamanlarda."],
    "öfkeli":    ["Bugün canımı sıkma.", "Yanlış zamanda geldin."],
    "korkmuş":   ["Sessizce konuş, biri duyabilir.", "Etrafıma bakıyorum, sen de bak."],
    "umutlu":    ["İşler düzelecek gibi, hissediyorum.", "Bu hafta iyi bir habere gebe."],
    "stresli":   ["Aklım bin yerde, kısa kes.", "Üstümde çok yük var şu sıra."],
    "heyecanlı": ["Söyleyecek çok şeyim var aslında!", "Aklımda bir fikir döner."],
    "huzurlu":   ["Sakin sakin konuşalım.", "İyiyim, şükür."],
}


# ---------------- Recent events (per NPC) ----------------
EVENT_LABELS = {
    "child_born":        "Yeni bir çocuğu oldu",
    "child_lost":        "Çocuğunu kaybetti",
    "spouse_lost":       "Eşini kaybetti",
    "spouse_married":    "Evlendi",
    "lost_money":        "Büyük para kaybetti",
    "earned_money":      "Bol kazanç sağladı",
    "friend_died":       "Yakın bir dostu öldü",
    "moved_house":       "Taşındı",
    "fell_ill":          "Hastalandı",
    "recovered":         "İyileşti",
    "promoted":          "Yükseldi (terfi)",
    "demoted":           "Düştü",
    "robbed":            "Soyuldu",
    "argument":          "Bir komşuyla kavga etti",
    "good_harvest":      "İyi bir hasat kaldırdı",
    "bad_harvest":       "Mahsulü mahvoldu",
    "festival":          "Köyde bir şölen var",
    "rumor_heard":       "Bir söylenti duydu",
}

EVENT_MOOD_DELTA = {
    "child_born":     ("mutlu",     +2),
    "child_lost":     ("üzgün",     -4),
    "spouse_lost":    ("üzgün",     -5),
    "spouse_married": ("mutlu",     +3),
    "lost_money":     ("stresli",   -2),
    "earned_money":   ("mutlu",     +2),
    "friend_died":    ("üzgün",     -3),
    "moved_house":    ("stresli",   -1),
    "fell_ill":       ("üzgün",     -2),
    "recovered":      ("umutlu",    +2),
    "promoted":       ("heyecanlı", +3),
    "demoted":        ("öfkeli",    -2),
    "robbed":         ("öfkeli",    -3),
    "argument":       ("öfkeli",    -1),
    "good_harvest":   ("mutlu",     +2),
    "bad_harvest":    ("stresli",   -2),
    "festival":       ("heyecanlı", +2),
    "rumor_heard":    (None, 0),
}


def ensure_profile(npc):
    """Lazily attach deep profile fields to a stock NPC."""
    if npc.get("_profile_v1"):
        return
    rng = random.Random(hash(npc["id"]) & 0xFFFFFFFF)
    if "goal" not in npc or npc["goal"] not in GOAL_BY_KEY:
        # Legacy NPCs had a free-text "goal" string; we replace it with a key.
        # Preserve the old text into _legacy_goal for display.
        if isinstance(npc.get("goal"), str) and npc["goal"] not in GOAL_BY_KEY:
            npc["_legacy_goal"] = npc["goal"]
        # Pick a goal weighted by NPC's role
        npc["goal"] = _pick_goal_for_npc(npc, rng)
    npc.setdefault("goal_progress", rng.randint(5, 60))
    npc.setdefault("goal_history", [])

    if "current_mood" not in npc:
        # Try to migrate from old `mood` field if present
        existing = npc.get("mood")
        if existing in MOODS:
            npc["current_mood"] = existing
        else:
            mapping = {"huzurlu": "huzurlu", "kararlı": "umutlu", "öfkeli": "öfkeli",
                       "umutsuz": "üzgün", "yorgun": "stresli", "şüpheci": "stresli",
                       "kibirli": "mutlu", "neşeli": "mutlu", "korkak": "korkmuş",
                       "merhametli": "huzurlu"}
            npc["current_mood"] = mapping.get(existing, rng.choice(MOODS))
    npc.setdefault("mood_score", 0)  # -10..+10 buffer affecting current_mood

    npc.setdefault("recent_events", [])
    npc.setdefault("personal_memory", [])  # per-player observations
    npc.setdefault("daily_log", [])  # weekly activities log
    npc.setdefault("debt", rng.choice([0, 0, 0, rng.randint(20, 200)]))
    npc.setdefault("savings", rng.randint(5, 60))
    npc["_profile_v1"] = True


def _pick_goal_for_npc(npc, rng):
    prof = npc.get("profession", "köylü")
    if prof in ("haydut",):
        return rng.choices(["intikam_almak", "zengin_olmak", "evine_donmek"],
                           weights=[3, 4, 1])[0]
    if prof in ("kral", "lord"):
        return rng.choices(["aileyi_buyutmek", "saygi_kazanmak", "lord_olmak"],
                           weights=[3, 3, 1])[0]
    if prof in ("asker", "şövalye"):
        return rng.choices(["asker_olmak", "saygi_kazanmak", "evlenmek"],
                           weights=[1, 3, 3])[0]
    if prof in ("tüccar",):
        return rng.choices(["zengin_olmak", "tuccar_olmak", "borc_odemek"],
                           weights=[4, 3, 2])[0]
    if prof in ("demirci", "marangoz", "kunduracı"):
        return rng.choices(["usta_olmak", "zengin_olmak", "evlenmek"],
                           weights=[4, 2, 2])[0]
    if npc.get("age", 25) < 22:
        return rng.choice(["evlenmek", "zengin_olmak", "asker_olmak", "tuccar_olmak"])
    if not npc.get("spouse_id"):
        return rng.choice(["evlenmek", "zengin_olmak", "saygi_kazanmak"])
    if not npc.get("children_ids"):
        return "cocuk_sahibi"
    return rng.choice(["aileyi_buyutmek", "saygi_kazanmak", "zengin_olmak", "borc_odemek"])


def push_recent_event(npc, etype, day, extra=""):
    ensure_profile(npc)
    label = EVENT_LABELS.get(etype, etype)
    text = f"{label}{(' — ' + extra) if extra else ''}"
    npc["recent_events"].append({"day": day, "type": etype, "text": text})
    if len(npc["recent_events"]) > 10:
        npc["recent_events"] = npc["recent_events"][-10:]
    mood, delta = EVENT_MOOD_DELTA.get(etype, (None, 0))
    if mood:
        npc["mood_score"] = max(-10, min(10, npc.get("mood_score", 0) + delta))
        # Strong events shift current_mood toward that mood
        if abs(delta) >= 3 or random.random() < 0.5:
            npc["current_mood"] = mood


def push_personal_memory(npc, line):
    ensure_profile(npc)
    npc["personal_memory"].append(line)
    if len(npc["personal_memory"]) > 12:
        npc["personal_memory"] = npc["personal_memory"][-12:]


def recompute_mood(npc):
    """Adjust current_mood based on mood_score and circumstances."""
    ensure_profile(npc)
    score = npc.get("mood_score", 0)
    if npc["health"] < 25:
        npc["current_mood"] = "üzgün"; return
    if score >= 5:
        npc["current_mood"] = "mutlu"
    elif score <= -5:
        npc["current_mood"] = "üzgün"
    elif score <= -2:
        # Pick stress vs. anger by personality
        if "öfkeli" in npc.get("personality", []):
            npc["current_mood"] = "öfkeli"
        else:
            npc["current_mood"] = "stresli"
    elif score >= 2:
        npc["current_mood"] = "umutlu"
    # Slowly decay toward 0
    if score > 0:
        npc["mood_score"] = score - 1
    elif score < 0:
        npc["mood_score"] = score + 1


# ---------------- Daily life / activities ----------------
ACTIVITIES_BY_PROFESSION = {
    "çiftçi":   ["tarlada çalıştı", "saban onardı", "sebze dikti", "değirmene gitti"],
    "fırıncı":  ["ekmek pişirdi", "un aldı", "fırını tamir etti"],
    "demirci":  ["nal dövdü", "kılıç biledi", "kömür biriktirdi"],
    "marangoz": ["odun yarmaya gitti", "sandık yaptı", "kapı tamir etti"],
    "avcı":     ["ormanda dolaştı", "tuzak kurdu", "geyik avladı"],
    "balıkçı":  ["ağ attı", "tekneyi onardı", "balık tuzlamaya başladı"],
    "tüccar":   ["pazara gitti", "kervan sahibiyle pazarlık etti", "yeni ürün getirdi"],
    "asker":    ["nöbet tuttu", "antrenman yaptı", "lordun adına yola çıktı"],
    "haydut":   ["yol kesti", "saklandı", "ganimet sayışı yaptı"],
    "kral":     ["kabul gününe katıldı", "lordlarla görüştü", "vergiyi denetledi"],
    "lord":     ["şölen verdi", "köylüleri dinledi", "askerlerini denetledi"],
    "rahip":    ["dua etti", "vaaz hazırladı", "fakire yardım etti"],
    "şifacı":   ["hastaları gezdi", "ot topladı", "merhem hazırladı"],
}

GENERIC_ACTIVITIES = [
    "komşusuyla konuştu", "dinlendi", "ailesiyle vakit geçirdi",
    "pazara çıktı", "hava aldı", "iş aletini onardı",
]

LIFE_EVENTS_WEEKLY = [
    "festival", "argument", "good_harvest", "bad_harvest",
    "earned_money", "lost_money", "rumor_heard", "fell_ill", "recovered",
]


def npc_weekly_tick(npc, state, rng):
    """Each week: pick an activity; small chance of a recent_event; mood drifts."""
    ensure_profile(npc)
    if not npc["alive"]:
        return
    pool = ACTIVITIES_BY_PROFESSION.get(npc["profession"], GENERIC_ACTIVITIES) + GENERIC_ACTIVITIES
    act = rng.choice(pool)
    npc["daily_log"].append({"day": state["turn"], "text": act})
    if len(npc["daily_log"]) > 8:
        npc["daily_log"] = npc["daily_log"][-8:]

    # Small chance of life event (~10%)
    if rng.random() < 0.10:
        et = rng.choice(LIFE_EVENTS_WEEKLY)
        # Domain-specific events
        if et == "good_harvest" and npc["profession"] != "çiftçi":
            et = "earned_money"
        if et == "bad_harvest" and npc["profession"] != "çiftçi":
            et = "lost_money"
        if et == "earned_money":
            gain = rng.randint(5, 50)
            npc["savings"] = npc.get("savings", 0) + gain
            push_recent_event(npc, et, state["turn"], f"+{gain} altın")
        elif et == "lost_money":
            loss = rng.randint(5, 50)
            npc["savings"] = max(0, npc.get("savings", 0) - loss)
            push_recent_event(npc, et, state["turn"], f"-{loss} altın")
        else:
            push_recent_event(npc, et, state["turn"])

    # Goal progress
    if rng.random() < 0.18:
        npc["goal_progress"] = min(100, npc.get("goal_progress", 0) + rng.randint(1, 4))
        if npc["goal_progress"] >= 100:
            # achieve goal: small mood boost; pick new goal
            push_recent_event(npc, "promoted", state["turn"], "Hedefe ulaştı")
            npc["goal_history"].append(npc["goal"])
            npc["goal"] = _pick_goal_for_npc(npc, rng)
            npc["goal_progress"] = 0

    recompute_mood(npc)


# ---------------- Dialogue helpers ----------------
def latest_event_line(npc):
    """Return a sentence about the most recent significant event, or empty."""
    ensure_profile(npc)
    if not npc["recent_events"]:
        return ""
    e = npc["recent_events"][-1]
    et = e["type"]
    lines = {
        "child_born":     "Geçenlerde bir çocuğum oldu, gözümün bebeği.",
        "child_lost":     "Çocuğumu kaybettim, içim kor.",
        "spouse_lost":    "Eşim öldü, ben de yarım kaldım.",
        "spouse_married": "Yeni evlendim, hayatım baştan başladı.",
        "lost_money":     "Cebim yandı bu hafta, deme gitsin.",
        "earned_money":   "Bu hafta ekstra kazandım, biraz nefes aldım.",
        "friend_died":    "Bir dostumu daha toprağa verdik.",
        "moved_house":    "Taşındım, eşyalar hâlâ yerli yerinde değil.",
        "fell_ill":       "Hastalandım, ayağa kalkmam zor oldu.",
        "recovered":      "İyileştim çok şükür, ölümü gördüm.",
        "promoted":       "Bir yükseliş aldım, kıymetimi anladılar.",
        "demoted":        "İşimde geri düştüm, içim acı.",
        "robbed":         "Soyuldum geçen hafta, hâlâ aklımda.",
        "good_harvest":   "Bu yıl tarlam güldü, neşeliyim.",
        "bad_harvest":    "Bu yıl tarlam yandı, kara kara düşünüyorum.",
        "festival":       "Köyde şölen var, mutlu insanlar görmek iyi geliyor.",
        "argument":       "Komşuyla kapıştık, ağzımda hâlâ acı.",
        "rumor_heard":    "Garip söylentiler dolaşıyor, duydun mu?",
    }
    return lines.get(et, e.get("text", ""))


def goal_line(npc):
    ensure_profile(npc)
    pool = GOAL_TALK.get(npc["goal"], [])
    if not pool:
        return ""
    rng = random.Random(npc["id"][:6] + npc["goal"])
    return rng.choice(pool)


def mood_greeting(npc):
    ensure_profile(npc)
    pool = MOOD_GREETING.get(npc["current_mood"], [])
    if not pool:
        return ""
    return random.choice(pool)


def personal_memory_line(npc, player_name):
    """Return a line referencing the player from NPC's personal memory."""
    ensure_profile(npc)
    mem = npc["personal_memory"]
    if not mem:
        return ""
    last = mem[-1]
    return f"({last})"
