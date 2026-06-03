"""Memory-aware, role-sensitive, varied dialogue generator.

Each response is computed from:
- NPC personality + mood + role + social_status
- Per-NPC interaction memory (counts per topic, last-interacted-day)
- Player reputation + crime
- NPC's own recent personal events (deaths in family, marriages, etc.)
- Recent world events
- Pseudo-random variation seeded by NPC id and turn count so repeats differ
"""
import random
import hashlib
from npc_profile import (
    ensure_profile, latest_event_line, goal_line, mood_greeting,
    MOOD_GREETING, GOAL_TALK, GOAL_BY_KEY,
)
from rumors import rumor_for_npc


REL_BANDS = [
    (-101, -50, "düşman"),
    (-50, -20, "rakip"),
    (-20, 20, "nötr"),
    (20, 50, "arkadaş"),
    (50, 101, "dost"),
]


def relation_band(score: int) -> str:
    for lo, hi, name in REL_BANDS:
        if lo <= score < hi:
            return name
    return "nötr"


SOCIAL_STATUS = {
    "kral": 5, "veliaht": 5, "lord": 4, "general": 4,
    "şövalye": 3, "asker": 3,
    "tüccar": 2, "şifacı": 2, "rahip": 2, "katip": 2, "öğretmen": 2,
    "demirci": 2, "marangoz": 2, "kunduracı": 2, "han sahibi": 2,
    "çiftçi": 1, "çoban": 1, "fırıncı": 1, "balıkçı": 1,
    "avcı": 1, "değirmenci": 1, "köylü": 1, "haydut": 0,
    "çocuk": 1,
}


def player_status(player):
    return SOCIAL_STATUS.get(player.get("profession", "köylü"), 1)


def npc_status(npc):
    return SOCIAL_STATUS.get(npc["profession"], 1)


# ---------- Greeting fragments by relationship band ----------
GREETING_BY_BAND = {
    "dost": [
        "Yine yollarımız kesişti, {pname}!",
        "Seni gördüğüme sevindim dostum.",
        "İçim ferahladı seninle, otur otur.",
        "{pname}! Tam da senden bahsediyordum.",
        "Hoş geldin, sofram da sözüm de açık.",
    ],
    "arkadaş": [
        "Selam {pname}, vakit ayırdığın iyi oldu.",
        "Ah, senmişsin. Nasılsın bakalım?",
        "Yine merhaba. İşler nasıl?",
        "Geldiğin iyi oldu, kafam dağınıktı.",
    ],
    "nötr": [
        "Ne istersin?",
        "Selam yabancı. Lafa tutma uzun, işim var.",
        "Bir derdin mi var?",
        "Konuş bakalım.",
        "Acelen yoksa konuşalım.",
    ],
    "rakip": [
        "Yine sen mi? Hayrola.",
        "Acele et, vaktim sana ayrılmaz.",
        "Konuş ve git.",
        "Ne arıyorsun burada hâlâ?",
    ],
    "düşman": [
        "Defol gözümün önünden!",
        "Seninle bir lafım olamaz.",
        "Bir adım daha at, göreceğin var.",
        "Yüzünü görmek bile öfke veriyor bana.",
    ],
}


# ---------- Status-based reactions ----------
KING_REJECT = [
    "Sen kim oluyorsun da huzuruma çıkıyorsun? Geri çekil.",
    "Bir köylüyle laflanmaz. Muhafızlar nerede?",
    "İtibarın yetersiz. Saraya yakışmıyorsun.",
    "Sana kelam edecek değilim.",
]

SOLDIER_THREAT = [
    "Suç defterin kabarık. Bir yanlış adımda demir vururum.",
    "Seni izliyorum. Lordumun emrindeyim, sakın kayıpta görünme.",
    "Yarım altın bile çalsan, kelle uçar duymadım deme.",
]

MERCHANT_PRICE_TALK = {
    "scarce": [
        "Mal kalmadı dostum, hepsini krallık aldı götürdü.",
        "Ne istersen pahalı bu sıralar, gelen yok giden çok.",
        "Sandığım bomboş, fırsatçı değilim ama yüksek satarım.",
    ],
    "abundant": [
        "Bol bol var şimdilik, indirim yaparım sana.",
        "Sandıklar dolu, alıcı bulamıyorum bir türlü.",
        "Bu fiyatlar düşmeden alırsan bana iyilik edersin.",
    ],
    "normal": [
        "Fiyatlar şu sıralar oturmuş gibi.",
        "Pazarlığa açığım, gel görüşelim.",
    ],
}

LORD_FORMAL = [
    "{pname}, ne meselen var? Kısa kes, lordun başka işleri de var.",
    "Sözünü tart, ben buranın efendisiyim.",
    "Vergini ödedin mi? Önce o sonra muhabbet.",
]


# ---------- Profession-flavored work talk (multiple pools) ----------
PROFESSION_TALK = {
    "çiftçi": [
        "Bu mevsim hasat zor, yağmur ya çok ya az.",
        "Buğday yine ucuza gidiyor.",
        "Tarladan tarlaya koşturmaktan belim ağrıyor.",
        "Bir öküzüm var, ondan başka dostum yok.",
    ],
    "demirci": [
        "Demir pahalı, ocak söndüyse iş bitti.",
        "Bir kılıç dövüyorum, savaş yakındır derler.",
        "Çekiç sesinden başka müzik duymadım hayatımda.",
    ],
    "tüccar": [
        "Yollar tehlikeli ama kar var. Dikkatli olmak lazım.",
        "Doğuda kumaş ucuz, batıda altın gibi.",
        "Birkaç at daha alsam kervanım büyür.",
    ],
    "asker": [
        "Lordumuz ne derse o, biz emir kuluyuz.",
        "Sınırda hareketlilik var, hazır olun derler.",
        "Çadır yatıyoruz haftalardır, kemiklerim sızlıyor.",
    ],
    "avcı": [
        "Ormanlar tekin değil, kurtlar arttı.",
        "Bir ayı izi sürüyorum, eşlik eder misin?",
        "Geyik etini iyi tütsülerim, satayım istersen.",
    ],
    "haydut": [
        "Keseni bırak, gitmene izin vereyim. Şaka şaka.",
        "Doğru kaleyi bilirsen sığınak hazır.",
        "Yol kesmek kolay, paylaşmak zor.",
    ],
    "rahip": [
        "Tanrılar bizi sınıyor, sabır gerek.",
        "Bu kül kokusu bir alâmet, dikkat et.",
        "Dua etmediğin gün heba olmuş gündür.",
    ],
    "lord": [
        "Buranın efendisiyim, adabınla konuş.",
        "Vergiler ödenmeli, yoksa ekmek bulamayız.",
        "Halkı korumak da kollamak da bana düşer.",
    ],
    "kral": [
        "Krallığım dimdik durduğu sürece sözüm fermandır.",
        "İhanetin cezası ölümdür, aklında bulunsun.",
        "Bu taht kanla kazanıldı, kanla korunur.",
    ],
    "veliaht": [
        "Tahta çıktığımda işler değişecek.",
        "Babamın yöntemleri eskidi.",
        "Bekliyorum, sıram gelecek.",
    ],
    "şifacı": [
        "Yaranı görmem mi? Ot kalmadı pek.",
        "Hastalar arttı bu sıralar.",
    ],
    "fırıncı": [
        "Un pahalandı, ekmek nasıl ucuz olsun?",
        "Sabah erken kalkmaktan başım dönüyor.",
    ],
}


MOOD_LINE_POOL = {
    "neşeli": [
        "Bugün içim ferah, dünya başka.",
        "Bir şarkı söylesem mi diyorum.",
        "Hayat zor ama gün güzel.",
    ],
    "yorgun": [
        "Yorgunum dostum, dinlemem lazım.",
        "Bu sırtım belim ağrıyor.",
        "Uykusuzum, hatalı konuşabilirim.",
    ],
    "umutsuz": [
        "Bazen her şey boşuna geliyor.",
        "Yıldızlar bile bizi unutmuş.",
        "İçimde bir kuyu var, dipsiz.",
    ],
    "kararlı": [
        "Bir karara vardım, geri dönüş yok.",
        "İçimde bir ateş var, sonuna kadar gideceğim.",
    ],
    "huzurlu": [
        "Sessizliği seviyorum.",
        "Şu an her şey yerli yerinde.",
    ],
    "öfkeli": [
        "İçimde bir ateş var, dokunma.",
        "Konuşma açma şu konuyu, taşarım.",
    ],
}


REPEAT_LINES = {
    1: "",
    2: "Hmm... bunu az önce sormuş gibisin. Belki yanılıyorum.",  # confusion
    3: "Yine mi aynı soru? Cevabım değişmedi.",  # irritation
    4: "Sabrımı sınama. Başka derdin yok mu?",  # near-hostility
    5: "Yeter artık! Çek git buradan.",  # hostility
}


# 4-stage emotional escalation for repeated questioning:
# 1 = merak (curiosity/normal)
# 2 = kafa karışıklığı (confusion)
# 3 = sinirlilik (irritation)
# 4+ = düşmanlık (hostility)
def emotional_stage(repeat_count: int) -> str:
    if repeat_count <= 1:
        return "merak"
    if repeat_count == 2:
        return "kafa_karışıklığı"
    if repeat_count == 3:
        return "sinirlilik"
    return "düşmanlık"


# Child-specific reactions from adult NPCs (player.age < 13)
CHILD_REACTIONS = {
    "kral": [
        "Çocuk! Sarayda işin ne? Annenle babanı bul, geri dön.",
        "Krallar çocuklarla muhatap olmaz. Çık dışarı.",
    ],
    "lord": [
        "Burası bir çocuğa göre yer değil küçük. Git evine.",
        "Sana laf etmem yavrum, lordun başka işleri var.",
    ],
    "asker": [
        "Hey küçük, sokakta ne dolaşıyorsun? Evine git.",
        "Çocuk, kılıçlar tehlikelidir. Uzak dur.",
    ],
    "haydut": [
        "Hee, küçük olan. Cebinde ne var bakalım?",
        "Çocuksun ama doğru zamanda yanlış yerdesin.",
    ],
    "tüccar": [
        "Ne almak istiyorsun küçüğüm? Paran yetiyor mu?",
        "Çocuklara şeker veriyorum bazen, ama bugün yok.",
    ],
    "şifacı": [
        "Yaranı göster yavrum, ot sürerim.",
        "Çocukları severim, gel bakayım.",
    ],
    "rahip": [
        "Tanrılar çocukları korur. Dua etmeyi unutma.",
        "Küçüksün ama ruhun büyüsün yavrum.",
    ],
    "default_friendly": [
        "Ne haber küçük? Annen biliyor mu burada olduğunu?",
        "Sen kimin çocuğusun bakalım?",
        "Yavrum, koş oyna; büyüklerin işine karışma.",
    ],
    "default_neutral": [
        "Çocuk, başka işim var. Sonra konuşuruz.",
        "Ne istiyorsun yavrum?",
    ],
}


CRIME_REACTION = [
    "Senin namın kötü duyuluyor. Konuşurken kelimelerini seç.",
    "Yakanın peşinde olduğunu biliyorum. Dikkatli ol.",
    "Suçlu biriyle konuştuğum duyulmasın.",
]


HIGH_REP = [
    "Adın iyi anılıyor, bunu kaybetmemen lazım.",
    "Saygıyla yaklaşıyorum, hak ettin.",
]


def _seed_rng(npc_id, topic, day, turn):
    h = hashlib.md5(f"{npc_id}|{topic}|{day}|{turn}".encode()).hexdigest()
    return random.Random(int(h[:8], 16))


def _pick(rng, pool):
    if not pool:
        return ""
    return pool[rng.randrange(len(pool))]


def _personality_flavor(rng, npc, band):
    out = []
    if "kibirli" in npc["personality"] and band != "dost":
        out.append(_pick(rng, [
            "Tabii sen anlamazsın, sıradan biri için fazla derin.",
            "Senin gibilerle konuşmak bana yakışmıyor aslında.",
        ]))
    if "cömert" in npc["personality"] and band in ("dost", "arkadaş"):
        out.append(_pick(rng, [
            "İstersen bir kupa bal şarabı ısmarlayayım.",
            "Açsan paylaşırım, kuralım böyle.",
        ]))
    if "öfkeli" in npc["personality"] and band in ("rakip", "düşman"):
        out.append("Sabrımı zorlama.")
    if "neşeli" in npc["personality"]:
        out.append("Hayat ne kadar kötü olsa da gülmek lazım.")
    if "korkak" in npc["personality"] and band in ("rakip", "düşman"):
        out.append("Sesini alçalt, biri duyabilir.")
    if "kurnaz" in npc["personality"]:
        out.append(_pick(rng, [
            "Hakkımda her duyduğuna inanma.",
            "Önemli olan kimin söylediği değil, niye söylediği.",
        ]))
    return " ".join(p for p in out if p)


def _personal_event_line(npc, recent_world):
    """Surface personal events from NPC's own memory of world."""
    personal = [e for e in (npc.get("personal_events") or [])[-3:]]
    if not personal:
        return ""
    e = personal[-1]
    kind = e.get("type")
    if kind == "eş_kaybı":
        return "Eşimi yakın zamanda kaybettim, içim hâlâ yanıyor."
    if kind == "evlilik":
        return "Geçenlerde evlendim, hayatım değişti."
    if kind == "doğum":
        return "Bir çocuğum daha oldu, yorgun ama mutluyum."
    if kind == "çocuk_kaybı":
        return "Çocuğumu yitirdim. Bunu unutamayacağım."
    return ""


def _refuse_audience(npc, player):
    """Kings/Lords refuse low-status, low-reputation visitors."""
    if npc["profession"] == "kral":
        if player.get("reputation", 0) < 50 and player_status(player) < 4:
            return True
    if npc["profession"] == "lord":
        if player.get("reputation", 0) < -10 and player_status(player) < 3:
            return True
    return False


def _is_child(player):
    return (player.get("age") or 0) < 13


def generate_response(npc, relationship_score, topic, player, recent_world_events, day, turn, state=None):
    """Returns a freshly varied response string.

    `turn` is the global interaction count with this NPC (drives repeat lines).
    """
    ensure_profile(npc)
    rng = _seed_rng(npc["id"], topic, day, turn)
    band = relation_band(relationship_score)
    parts = []

    # Helper: read mood lines from new profile system
    mood = npc.get("current_mood", "huzurlu")

    # --- Child player special path: adult NPCs treat the player as a kid ---
    if _is_child(player):
        # Parent reactions are warm and specific
        if npc.get("id") in (player.get("parent_ids") or []):
            is_mother = npc.get("gender") == "kadın"
            mom_lines = [
                f"Yavrum {player['name']}, gel buraya.",
                "Geldin demek, sofrada ekmek var.",
                "Sıcak çorba pişiriyordum, koş gel.",
                "Yine bir tarafın çamur olmuş, gel temizleyeyim.",
                "Anlat bakalım, gün nasıl geçti?",
            ]
            dad_lines = [
                f"{player['name']}, durma boş, bir iş tutmaya bak.",
                "Gel buraya oğul/kız, sana bir şey göstereyim.",
                "İş bitti mi yine? Beni öyle bakarak yorma.",
                "Hadi yardım eder misin? Kollarım yoruldu.",
                "Aklında ne var, anlat bakayım.",
            ]
            parts = [_pick(rng, mom_lines if is_mother else dad_lines)]
            # Surface a parent's recent event for variety
            ev = latest_event_line(npc)
            if ev and rng.random() < 0.5:
                parts.append(ev)
            interactions = npc.get("interactions", {})
            repeat_count = interactions.get(topic, 0)
            if repeat_count >= 2:
                line = REPEAT_LINES.get(min(repeat_count, 5), REPEAT_LINES[5])
                if line:
                    parts.insert(0, line)
            return " ".join(p for p in parts if p)

        child_pool = CHILD_REACTIONS.get(
            npc["profession"],
            CHILD_REACTIONS["default_friendly"] if band in ("dost", "arkadaş")
            else CHILD_REACTIONS["default_neutral"],
        )
        parts.append(_pick(rng, child_pool))
        # Topic-flavored short note for child
        if topic == "iş":
            parts.append("Sen daha küçüksün, iş zamanı gelmedi.")
        elif topic == "dünya":
            # Even kids hear rumors!
            if state is not None:
                r = rumor_for_npc(npc, state)
                if r:
                    parts.append(f"Söylenti diyorlar: {r['text']}")
                else:
                    parts.append("Dünya senin için fazla büyük yavrum.")
            else:
                parts.append("Dünya senin için fazla büyük yavrum.")
        elif topic == "aile":
            if npc.get("spouse_id"):
                parts.append("Ailem var çok şükür.")
            else:
                parts.append("Bekarım, niye sorarsın küçük?")
        elif topic == "hedef":
            goal_meta = GOAL_BY_KEY.get(npc["goal"])
            if goal_meta:
                parts.append(f"Ben mi? {goal_meta['label'].lower()} istiyorum bir gün.")
            else:
                parts.append("Büyüyünce öğrenirsin yavrum.")
        elif topic == "veda":
            parts = [_pick(rng, [
                "Hadi git oyna küçük.",
                "Eve git, annen merak eder.",
                "Yolun açık olsun yavrum.",
                "Eyvallah küçük, dikkatli ol.",
            ])]

        # Repeat escalation still applies (curiosity → hostility)
        interactions = npc.get("interactions", {})
        repeat_count = interactions.get(topic, 0)
        if repeat_count >= 2:
            line = REPEAT_LINES.get(min(repeat_count, 5), REPEAT_LINES[5])
            if line:
                parts.insert(0, line)
        return " ".join(p for p in parts if p)

    # Refuse audience for nobility if unworthy
    if topic == "selam" and _refuse_audience(npc, player):
        if npc["profession"] == "kral":
            return _pick(rng, KING_REJECT)
        if npc["profession"] == "lord":
            return _pick(rng, LORD_FORMAL).format(pname=player["name"])

    # Repeat detection
    interactions = npc.get("interactions", {})
    repeat_count = interactions.get(topic, 0)

    pname = player["name"]

    if topic == "selam":
        # Special openings for royalty
        if npc["profession"] == "kral" and band != "düşman":
            parts.append(_pick(rng, [
                f"Yaklaş {pname}. Krallığım nezdinde ne istersin?",
                "Kelamını ölç, vakit dardır.",
                "Sözünü söyle ve git.",
            ]))
        elif npc["profession"] == "lord":
            parts.append(_pick(rng, LORD_FORMAL).format(pname=pname))
        else:
            parts.append(_pick(rng, GREETING_BY_BAND[band]).format(pname=pname))
        # Mood-driven follow up (new profile system)
        mg = MOOD_GREETING.get(mood)
        if mg:
            parts.append(_pick(rng, mg))
        # Surface a recent personal event ~40% of the time
        if rng.random() < 0.4:
            ev = latest_event_line(npc)
            if ev:
                parts.append(ev)

    elif topic == "iş":
        if npc["profession"] == "tüccar":
            # Look at location supply/demand to vary line
            loc_supply = npc.get("_loc_supply_signal", "normal")
            parts.append(_pick(rng, MERCHANT_PRICE_TALK[loc_supply]))
        elif npc["profession"] == "asker" and player.get("crime", 0) > 30:
            parts.append(_pick(rng, SOLDIER_THREAT))
        else:
            prof_lines = PROFESSION_TALK.get(npc["profession"], [
                f"Ben {npc['profession']}'ım, işim başımdan aşkın.",
                "Her gün aynı, ekmek peşindeyiz.",
            ])
            parts.append(_pick(rng, prof_lines))
        # Daily log flavor
        log = npc.get("daily_log") or []
        if log and rng.random() < 0.5:
            parts.append(f"Geçen hafta {log[-1]['text']}.")

    elif topic == "aile":
        if npc.get("spouse_id"):
            parts.append(_pick(rng, [
                "Bir eşim var, çok şükür birlikte yaşlanıyoruz.",
                "Eşim olmasa yaşayamazdım.",
                "Eşim son zamanlarda hastaydı, daha iyi şimdi.",
            ]))
        else:
            parts.append(_pick(rng, [
                "Hâlâ yalnızım. Kısmet açılır belki.",
                "Bekarım, niye herkes sorar bunu?",
                "Evlenmek istemiyorum aslında, kimseye yük olmayayım.",
            ]))
        if npc.get("children_ids"):
            n = len(npc["children_ids"])
            parts.append(f"{n} çocuğum var, onlar için yaşıyorum.")
        # Personal event surface
        pe = latest_event_line(npc) or _personal_event_line(npc, recent_world_events)
        if pe:
            parts.append(pe)

    elif topic == "dünya":
        # Prefer a rumor from the rumor pool if available
        chose_rumor = False
        if state is not None and rng.random() < 0.7:
            r = rumor_for_npc(npc, state)
            if r:
                parts.append(_pick(rng, [
                    f"Duydun mu? {r['text']}",
                    f"Bir kulağıma çalındı: {r['text']}",
                    f"Söylenti dolaşıyor: {r['text']}",
                ]))
                chose_rumor = True
        if not chose_rumor and recent_world_events:
            ev = recent_world_events[-min(10, len(recent_world_events)) + rng.randrange(min(10, len(recent_world_events)))]
            parts.append(_pick(rng, [
                f"Duydun mu? {ev['text']}",
                f"Söyledikleri doğruysa: {ev['text']}",
                f"Köyde duyulan en taze haber: {ev['text']}",
            ]))
        elif not chose_rumor:
            parts.append(_pick(rng, [
                "Bu civarda son zamanlarda kayda değer pek bir şey olmadı.",
                "Sessizlik bazen kötüye işarettir.",
            ]))

    elif topic == "üzgün":
        # Recent event takes priority
        ev_line = latest_event_line(npc)
        if ev_line and mood in ("üzgün", "stresli", "öfkeli"):
            parts.append(ev_line)
        elif mood in ("üzgün", "stresli", "öfkeli"):
            parts.append("Sorma. " + _pick(rng, MOOD_GREETING.get(mood, [""])))
            goal_meta = GOAL_BY_KEY.get(npc["goal"])
            if goal_meta:
                parts.append(f"{goal_meta['label']} istiyorum ama her şey ters gidiyor.")
        else:
            parts.append(_pick(rng, [
                "Üzgün değilim aslında. Belki biraz dalgın.",
                "Hayat işte, herkes biraz yorgun.",
                "Sorun olmasa hayat hayat olmaz.",
            ]))

    elif topic == "hedef":
        goal_meta = GOAL_BY_KEY.get(npc["goal"])
        if goal_meta:
            parts.append(f"Hayatta tek istediğim: {goal_meta['label'].lower()}.")
        gline = goal_line(npc)
        if gline:
            parts.append(gline)
        progress = npc.get("goal_progress", 0)
        if progress > 0:
            if progress < 30:
                parts.append("Daha yolun başındayım.")
            elif progress < 70:
                parts.append("Yolun yarısı geride.")
            else:
                parts.append("Çok az kaldı, hissediyorum.")
        if band in ("dost", "arkadaş"):
            parts.append(_pick(rng, [
                "Belki bir gün bana yardım edersin.",
                "Eline imkân geçerse aklında olsun.",
            ]))

    elif topic == "veda":
        if band in ("düşman", "rakip"):
            parts.append(_pick(rng, [
                "Git de bir daha gözüm seni görmesin.",
                "Yolun açık olsun da uzak olsun.",
                "Defol, bir daha karşıma çıkma.",
            ]))
        elif band in ("dost", "arkadaş"):
            parts.append(_pick(rng, [
                "Yolun açık olsun, yine bekleriz.",
                "Eyvallah dostum, kendine iyi bak.",
                "Allah'a emanet ol, beklerim seni.",
                "Görüşmek üzere, başın sağ olsun yolculuğunda.",
            ]))
        elif mood == "öfkeli":
            parts.append(_pick(rng, [
                "Defol, biraz nefes alayım.",
                "Git, vaktim yok.",
            ]))
        elif mood == "üzgün":
            parts.append(_pick(rng, [
                "Hadi git, ben başımı yere koyayım.",
                "Eyvallah... yalnız kalayım biraz.",
            ]))
        elif mood == "mutlu":
            parts.append(_pick(rng, [
                "Güle güle dostum, gün güzeldi sayende.",
                "Eyvallah, yine uğra.",
            ]))
        else:
            parts.append(_pick(rng, [
                "Hadi eyvallah.",
                "Hoşçakal.",
                "Selametle.",
                "Yolun açık olsun.",
            ]))

    else:
        parts.append("Anlamadım. Daha açık konuş.")

    # Player crime / reputation flavor
    if player.get("crime", 0) > 40 and band != "dost":
        parts.append(_pick(rng, CRIME_REACTION))
    if player.get("reputation", 0) >= 30 and band != "düşman":
        parts.append(_pick(rng, HIGH_REP))

    # Personality flavor
    pf = _personality_flavor(rng, npc, band)
    if pf:
        parts.append(pf)

    # Repeat irritation
    if repeat_count >= 2 and topic not in ("veda",):
        line = REPEAT_LINES.get(min(repeat_count, 5), REPEAT_LINES[5])
        if line:
            parts.insert(0, line)

    return " ".join(p for p in parts if p)


DIALOG_TOPICS = [
    ("selam", "Selam ver"),
    ("iş", "İşinden bahset"),
    ("aile", "Aileni sor"),
    ("dünya", "Dünyada ne oluyor?"),
    ("üzgün", "Neden üzgünsün?"),
    ("hedef", "Hedefin ne?"),
    ("veda", "Hoşçakal"),
]


def relationship_delta(npc, topic, player, repeat_count):
    """How much should relationship change for this interaction?

    Emotional stages affect relationship:
    1 (merak)         → base topic delta
    2 (kafa karış.)   → -1 (slight)
    3 (sinirlilik)    → -2
    4+ (düşmanlık)    → -4
    """
    if repeat_count >= 4:
        return -4
    if repeat_count == 3:
        return -2
    if repeat_count == 2:
        return -1
    if topic == "selam":
        base = 1
    elif topic == "aile":
        base = 1 if "konuşkan" in npc["personality"] else 0
    elif topic == "üzgün":
        base = 2 if "merhametli" in npc["personality"] else 0
    elif topic == "hedef":
        base = 1
    elif topic == "veda":
        base = 0
    else:
        base = 0
    # Crime penalty in nobility responses
    if player.get("crime", 0) > 50 and npc["profession"] in ("kral", "lord", "asker"):
        base -= 2
    if player.get("reputation", 0) > 40 and npc["profession"] in ("kral", "lord"):
        base += 1
    return base
