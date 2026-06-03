"""Rumor system — auto-generates rumors from world events and lets NPCs spread them.

A rumor lives in state['rumors'] with: id, day, type, text, region (kingdom_id),
truth (0..1), heard_by (set of npc ids), origin (event_id or npc_id).
"""
import random
import uuid


RUMOR_TEMPLATES = {
    # World event type → rumor text variations
    "ölüm": [
        "{loc}'de {name} öldü diyorlar.",
        "{name}'in ölümü dilden dile dolaşıyor.",
        "{loc}'de bir cenaze var, fısıltılar büyüyor.",
    ],
    "doğum": [
        "{loc}'de yeni bir bebek doğdu.",
        "{name} ailesine bir bebek katıldı, sevinçliler.",
    ],
    "evlilik": [
        "{name1} ile {name2} evlendi, şölen verdiler.",
        "İki kalp daha kavuştu {loc}'de.",
    ],
    "savaş": [
        "Sınırlarda asker hareketi var.",
        "Krallıklar arasında soğukluk büyüyor.",
        "Bir savaş çıkacağı söyleniyor.",
    ],
    "tahta_çıkış": [
        "Yeni bir kral oturdu tahta.",
        "{name} taç giydi, halk merakla bekliyor.",
    ],
    "cinayet": [
        "{loc}'de kanlı bir iş döndü, fail belli değil.",
        "Bir cinayet işlendi, soğukkanlılıkla.",
    ],
    "hapis": [
        "Birini zindana attılar, namı yayılıyor.",
    ],
    "festival": [
        "{loc}'de şölen var, herkes davetli sayılır.",
    ],
    "haydut": [
        "Güney yollarında haydutlar görüldü, dikkatli yolculuk edin.",
        "Bir kervan soyuldu, haydutlar cesurlaşıyor.",
    ],
    "yangın": [
        "{loc}'de yangın çıktı diye duydum.",
    ],
    "kıtlık": [
        "{loc}'de tahıl tükeniyor, kıtlık geliyor.",
    ],
    "evlat": [
        "{name} bir oğul/kız sahibi oldu.",
    ],
    "iyi_hasat": [
        "{loc}'de bu yıl bereket var, tahıl ucuzlayacakmış.",
    ],
    "kötü_hasat": [
        "{loc}'de bu yıl hasat kötü, ekmek pahalanacak.",
    ],
}


# Map state.history event types to rumor types
HISTORY_TO_RUMOR = {
    "ölüm": "ölüm", "doğum": "doğum", "evlilik": "evlilik",
    "tahta_çıkış": "tahta_çıkış", "cinayet": "cinayet",
    "hapis": "hapis", "savaş": "savaş", "ödül": "haydut",
}


def make_rumor(state, rtype, text, kingdom_id=None, origin=None, truth=0.9):
    rumor = {
        "id": uuid.uuid4().hex[:12],
        "day": state.get("turn", 0),
        "type": rtype,
        "text": text,
        "kingdom_id": kingdom_id,
        "truth": truth,
        "origin": origin,
        "heard_by": [],
    }
    state.setdefault("rumors", []).append(rumor)
    if len(state["rumors"]) > 80:
        state["rumors"] = state["rumors"][-80:]
    return rumor


def auto_rumors_from_events(state, new_events):
    """Convert significant world events into rumors."""
    for ev in new_events:
        etype = ev.get("type")
        rtype = HISTORY_TO_RUMOR.get(etype)
        if not rtype:
            continue
        # Skip player's own actions (those are already public knowledge)
        if etype in ("ticaret", "yolculuk", "çalışma", "kullanım", "kuşanma"):
            continue
        templates = RUMOR_TEMPLATES.get(rtype, [ev.get("text", "")])
        text = random.choice(templates) if templates else ev.get("text", "")
        # Try to fill {loc} {name} from ev.text — fallback to event text
        if "{" in text:
            text = ev.get("text", text)
        make_rumor(state, rtype, text, origin=ev.get("id"))


def seasonal_rumors(state):
    """Occasionally generate ambient rumors (haydut, kıtlık, hasat)."""
    if random.random() < 0.15:
        loc = random.choice(state["world"]["locations"])
        kind = random.choice(["haydut", "iyi_hasat", "kötü_hasat", "yangın"])
        text = random.choice(RUMOR_TEMPLATES[kind])
        text = text.replace("{loc}", loc["name"])
        make_rumor(state, kind, text, kingdom_id=loc.get("kingdom_id"), truth=0.6)


def rumor_for_npc(npc, state):
    """Pick a rumor this NPC might share. Prefer recent + same-kingdom rumors."""
    rumors = state.get("rumors") or []
    if not rumors:
        return None
    candidates = [r for r in rumors[-25:]
                  if r["kingdom_id"] in (None, npc.get("kingdom_id"))
                  and npc["id"] not in r.get("heard_by", [])]
    if not candidates:
        candidates = rumors[-10:]
    r = random.choice(candidates)
    if npc["id"] not in r["heard_by"]:
        r["heard_by"].append(npc["id"])
    return r
