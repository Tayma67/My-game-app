"""Template-based dialogue generator.

Generates NPC responses based on personality, relationship score,
recent world events and the NPC's own state. No external LLM is used.
"""
import random


REL_BANDS = [
    (-100, -50, "düşman"),
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


GREETING_BY_BAND = {
    "dost": [
        "Seni gördüğüme ne kadar sevindim, {pname}!",
        "Yine yollarımız kesişti dostum, oturmaz mısın?",
        "Hoş geldin, sen olmadan günler eksik kalıyor.",
    ],
    "arkadaş": [
        "Ah, {pname}, seni görmek hoş.",
        "Selam! Vakit ayırdığın için sağol.",
        "İyi günler. Yine yollar mı?",
    ],
    "nötr": [
        "Ne istersin yabancı?",
        "Selam. Bir derdin mi var?",
        "İşim çok, lafa tutma uzun.",
    ],
    "rakip": [
        "Yine sen mi?",
        "Acele et, vaktim yok sana.",
        "Konuş ve git.",
    ],
    "düşman": [
        "Defol gözümün önünden!",
        "Seninle konuşacak bir şeyim yok.",
        "Bir adım daha at, göreceğin var.",
    ],
}


PROFESSION_TALK = {
    "çiftçi": [
        "Bu mevsim hasat zor. Yağmur ya çok ya az.",
        "Buğday yine ucuza gidiyor, tüccarlar canımıza okuyor.",
    ],
    "demirci": [
        "Demir pahalandı, ocak söndüyse iş bitti.",
        "Bir kılıç dövüyorum, savaş yakındır derler.",
    ],
    "tüccar": [
        "Yollar tehlikeli ama kar var. Yine de dikkatli olmak lazım.",
        "Doğuda kumaş ucuz, batıda altın gibi. Bilen bilir.",
    ],
    "asker": [
        "Lordumuz ne derse o. Biz emir kuluyuz.",
        "Sınırda hareketlilik var, hazır olun derler.",
    ],
    "avcı": [
        "Ormanlar bu sıralar tekin değil, kurtlar arttı.",
        "Bir ayı izi sürüyorum, bana eşlik eder misin?",
    ],
    "haydut": [
        "Keseni bırak, gitmene izin vereyim. Şaka şaka... belki.",
        "Doğru kaleyi bilirsen sığınak hazır.",
    ],
    "rahip": [
        "Tanrılar bizi sınıyor. Sabır gerek.",
        "Bu kül kokusunu duyuyor musun? Bir alâmet.",
    ],
    "lord": [
        "Ben buranın efendisiyim. Adabımla konuş.",
        "Vergiler ödenmeli. Yoksa ekmek bulamayız.",
    ],
    "kral": [
        "Krallığım dimdik ayakta durduğu sürece sözüm fermandır.",
        "İhanet edenin cezası ölümdür. Aklında bulunsun.",
    ],
    "veliaht": [
        "Tahta çıktığımda işler değişecek.",
        "Babamın yöntemleri eskidi.",
    ],
}


MOOD_LINE = {
    "neşeli": "Bugün içim ferah, dünya başka.",
    "yorgun": "Yorgunum dostum, dinlemem lazım.",
    "umutsuz": "Bazen her şey boşuna geliyor.",
    "kararlı": "Bir karara vardım, geri dönüş yok.",
    "huzurlu": "Sessizliği seviyorum.",
    "öfkeli": "İçimde bir ateş var, dokunma.",
}


def generate_response(npc, relationship_score, topic, player_name, recent_events):
    band = relation_band(relationship_score)
    parts = []

    if topic == "selam":
        parts.append(random.choice(GREETING_BY_BAND[band]).format(pname=player_name))
        parts.append(MOOD_LINE.get(npc["mood"], ""))

    elif topic == "iş":
        prof_lines = PROFESSION_TALK.get(npc["profession"], [
            f"Ben {npc['profession']}'ım. İşim başımdan aşkın.",
            "Her gün aynı, ekmek peşindeyiz.",
        ])
        parts.append(random.choice(prof_lines))

    elif topic == "aile":
        if npc["spouse_id"]:
            parts.append("Bir eşim var, çok şükür birlikte yaşlanıyoruz.")
        else:
            parts.append("Hâlâ yalnızım. Belki kısmet açılır.")
        if npc["children_ids"]:
            parts.append(f"Çocuklarım var, {len(npc['children_ids'])} tane. Onlar için yaşıyorum.")
        else:
            parts.append("Çocuğum yok henüz.")

    elif topic == "dünya":
        if recent_events:
            ev = random.choice(recent_events[-10:])
            parts.append(f"Duydun mu? {ev['text']}")
        else:
            parts.append("Bu civarda son zamanlarda kayda değer pek bir şey olmadı.")

    elif topic == "üzgün":
        if npc["mood"] in ("umutsuz", "öfkeli", "yorgun"):
            parts.append("Sorma. " + MOOD_LINE[npc["mood"]])
            parts.append(f"Hedefim {npc['goal']}, ama her şey ters gidiyor.")
        else:
            parts.append("Üzgün değilim aslında. Belki biraz dalgın.")

    elif topic == "hedef":
        parts.append(f"Hayatta tek istediğim: {npc['goal']}.")
        if band in ("dost", "arkadaş"):
            parts.append("Belki bir gün bana yardım edersin.")

    elif topic == "veda":
        if band in ("düşman", "rakip"):
            parts.append("Git de bir daha gözüm seni görmesin.")
        elif band in ("dost", "arkadaş"):
            parts.append("Yolun açık olsun, yine bekleriz.")
        else:
            parts.append("Hadi eyvallah.")

    else:
        parts.append("Anlamadım. Daha açık konuş.")

    # Personality flavor
    if "kibirli" in npc["personality"] and band != "dost":
        parts.append("Tabii sen anlamazsın, sıradan biri için fazla derin.")
    if "cömert" in npc["personality"] and band in ("dost", "arkadaş"):
        parts.append("İstersen bir kupa bal şarabı ısmarlayayım.")
    if "öfkeli" in npc["personality"] and band in ("rakip", "düşman"):
        parts.append("Sabrımı zorlama.")
    if "neşeli" in npc["personality"]:
        parts.append("Hayat ne kadar kötü olsa da gülmek lazım.")

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
