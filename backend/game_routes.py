"""Game API endpoints — V3: child-start, stats, skills, items, family quests."""
import random
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from auth import make_get_current_user
from world_gen import generate_world, generate_player, initial_history, new_id
from simulation import (
    advance_time, _push_event, _ensure_state_fields, _recompute_prices,
    soldier_check, _ensure_market,
)
from dialogue import (
    generate_response, relation_band, relationship_delta,
    DIALOG_TOPICS, npc_status, player_status, SOCIAL_STATUS,
    emotional_stage,
)
from calendar_tr import current_calendar, player_age
from items import ITEMS, EQUIPMENT_SLOTS, apply_use_effects, equipment_bonuses, get_item
from skills import (
    JOB_REQUIREMENTS, check_job_eligible, list_eligible_jobs,
    apply_work_training, unlocked_perks, get_age_group, SKILL_PERKS, SKILL_KEYS, STAT_KEYS,
)
from family_quests import make_family_quests, unlock_age_appropriate, progress_quest

SCHEMA_VERSION = "v3"

WORLD_DEFAULTS = {
    "n_kingdoms": 3,
    "n_cities": 3,
    "n_villages": 10,
    "n_castles": 5,
    "n_npcs": 100,
}

# Child can do these (everything else gated until age 13)
CHILD_ALLOWED_PROFESSIONS = ["işsiz", "köylü"]
ADULT_AGE = 13


# -------- Pydantic --------
class ChatIn(BaseModel):
    npc_id: str
    topic: str


class TravelIn(BaseModel):
    location_id: str


class TradeIn(BaseModel):
    location_id: str
    good: str
    qty: int
    action: str  # "al" or "sat"


class CrimeIn(BaseModel):
    crime_type: str
    target_npc_id: Optional[str] = None


class JobIn(BaseModel):
    profession: str


class QuestIn(BaseModel):
    quest_id: str


class MarryIn(BaseModel):
    npc_id: str


class AttackIn(BaseModel):
    npc_id: str


class UseItemIn(BaseModel):
    item: str
    qty: int = 1


class EquipIn(BaseModel):
    item: str  # item key in inventory


class UnequipIn(BaseModel):
    slot: str


class AdvanceIn(BaseModel):
    weeks: int = 1


# -------- State helpers --------
async def _load_state(db, user_id: str):
    state = await db.game_states.find_one({"user_id": user_id})
    if not state:
        raise HTTPException(status_code=404, detail="Aktif oyun bulunamadı")
    if state.get("schema_version") != SCHEMA_VERSION:
        # Old game schema — purge and require new game
        await db.game_states.delete_one({"user_id": user_id})
        raise HTTPException(status_code=409,
                            detail="Oyun şeması güncellendi. Lütfen yeni oyun başlat.")
    state.pop("_id", None)
    _ensure_state_fields(state)
    return state


async def _save_state(db, user_id: str, state: dict):
    state["user_id"] = user_id
    state["schema_version"] = SCHEMA_VERSION
    await db.game_states.update_one(
        {"user_id": user_id}, {"$set": state}, upsert=True
    )


def _decorate(state):
    """Attach derived view-only fields (calendar, perks, eligible jobs)."""
    cal = current_calendar(state)
    state["calendar"] = cal
    state["player"]["age"] = player_age(state)
    state["player"]["age_group"] = get_age_group(state["player"]["age"])
    state["player"]["is_child"] = state["player"]["age"] < ADULT_AGE
    state["player"]["perks"] = unlocked_perks(state["player"])
    state["player"]["equipment_bonuses"] = equipment_bonuses(state["player"])
    return state


def _require_adult(state, what="bu eylemi"):
    if state["player"]["age"] < ADULT_AGE:
        raise HTTPException(
            status_code=403,
            detail=f"Çocuk yaştasın ({state['player']['age']}). 13 yaşına gelmeden {what} yapamazsın.",
        )


def build_game_router(db):
    router = APIRouter(prefix="/api/game", tags=["game"])
    get_current_user = make_get_current_user(db)

    # ---------- core ----------
    @router.post("/new")
    async def new_game(user: dict = Depends(get_current_user)):
        world = generate_world(**WORLD_DEFAULTS)
        player, mother, father = generate_player(world)
        state = {
            "user_id": user["_id"],
            "schema_version": SCHEMA_VERSION,
            "turn": 0, "day": 0,
            "world": world, "player": player,
            "relationships": {}, "quests": [], "history": initial_history(),
            "family_quests": make_family_quests({}, mother["id"], father["id"]),
        }
        _ensure_state_fields(state)
        # Unlock starting quests
        unlock_age_appropriate(state)
        _push_event(state, 0, "doğum",
                    f"{player['name']} doğdu. Anne: {mother['name']}, Baba: {father['name']}.")
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    @router.get("/state")
    async def get_state(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        return _decorate(state)

    @router.delete("/state")
    async def delete_state(user: dict = Depends(get_current_user)):
        await db.game_states.delete_one({"user_id": user["_id"]})
        return {"ok": True}

    @router.post("/advance")
    async def advance(weeks: int = 1, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        advance_time(state, weeks=max(1, weeks))
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    # ---------- chat ----------
    @router.post("/chat")
    async def chat(body: ChatIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        npc = next((n for n in state["world"]["npcs"] if n["id"] == body.npc_id), None)
        if not npc or not npc["alive"]:
            raise HTTPException(status_code=404, detail="NPC bulunamadı veya ölü")

        rel = state["relationships"].get(npc["id"], 0)
        if rel <= -70 and npc["profession"] in ("asker", "lord", "haydut") and body.topic == "selam":
            return {
                "response": f"{npc['name']} kılıcını çekti! Konuşma değil savaş istiyor.",
                "relationship": rel,
                "band": relation_band(rel),
                "hostile": True,
            }

        npc["interactions"][body.topic] = npc["interactions"].get(body.topic, 0) + 1
        npc["turn_counter"] = npc.get("turn_counter", 0) + 1
        repeat = npc["interactions"][body.topic]
        stage = emotional_stage(repeat)

        # Merchant supply signal
        loc = next((l for l in state["world"]["locations"] if l["id"] == npc["location_id"]), None)
        if loc and npc["profession"] == "tüccar":
            good = random.choice(list(loc["market"].keys()))
            ratio = loc["market"][good]["supply"] / max(1, loc["market"][good]["demand"])
            if ratio < 0.5:
                npc["_loc_supply_signal"] = "scarce"
            elif ratio > 1.5:
                npc["_loc_supply_signal"] = "abundant"
            else:
                npc["_loc_supply_signal"] = "normal"

        # Ensure player age set for dialogue
        state["player"]["age"] = player_age(state)
        # Make parent_ids visible to dialogue (used by child path)
        _ = state["player"].get("parent_ids") or []

        response = generate_response(
            npc, rel, body.topic, state["player"],
            state["history"], state["turn"], npc["turn_counter"],
        )

        delta = relationship_delta(npc, body.topic, state["player"], repeat)
        new_rel = max(-100, min(100, rel + delta))
        state["relationships"][npc["id"]] = new_rel

        npc.setdefault("memory", []).append({
            "day": state["turn"],
            "topic": body.topic,
            "delta": delta,
            "stage": stage,
            "player_rep": state["player"].get("reputation", 0),
            "player_crime": state["player"].get("crime", 0),
        })
        if len(npc["memory"]) > 20:
            npc["memory"] = npc["memory"][-20:]

        npc.pop("_loc_supply_signal", None)

        # Child charisma/social training from interactions
        if state["player"]["age"] < ADULT_AGE:
            from skills import add_stat_xp, add_skill_xp
            add_skill_xp(state["player"], "social", 1)
            if repeat == 1:
                add_stat_xp(state["player"], "charisma", 2)

        progress_quest(state, "chat", {"npc_id": npc["id"]})

        await _save_state(db, user["_id"], state)
        return {
            "response": response,
            "relationship": new_rel,
            "band": relation_band(new_rel),
            "repeat_count": repeat,
            "stage": stage,
            "delta": delta,
            "state": _decorate(state),
        }

    @router.get("/dialog-topics")
    async def dialog_topics():
        return [{"id": t[0], "label": t[1]} for t in DIALOG_TOPICS]

    # ---------- travel ----------
    @router.post("/travel")
    async def travel(body: TravelIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        loc = next((l for l in state["world"]["locations"] if l["id"] == body.location_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum bulunamadı")
        # Children can only travel to villages or their home location
        if state["player"]["age"] < ADULT_AGE and loc["kind"] in ("kale",):
            raise HTTPException(status_code=403,
                                detail="Çocuk olarak kaleye gidemezsin.")
        if loc["kingdom_id"] in state["player"].get("wanted_in", []):
            return {
                "state": _decorate(state),
                "blocked": True,
                "message": f"{loc['name']} {loc['kingdom_name']} sınırlarında, oraya başın için ödül var.",
            }
        state["player"]["location_id"] = loc["id"]
        state["player"]["location_name"] = loc["name"]
        _push_event(state, state["turn"], "yolculuk",
                    f"{state['player']['name']} {loc['name']}'e doğru yola çıktı.")
        advance_time(state, weeks=1)
        outcome = soldier_check(state)
        progress_quest(state, "travel", {"location_id": loc["id"]})
        await _save_state(db, user["_id"], state)
        return {"state": _decorate(state), "enforcement": outcome}

    # ---------- trade ----------
    @router.post("/trade")
    async def trade(body: TradeIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        loc = next((l for l in state["world"]["locations"] if l["id"] == body.location_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum bulunamadı")
        if body.good not in loc["market"]:
            raise HTTPException(status_code=400, detail="Geçersiz ürün")
        if body.qty < 1:
            raise HTTPException(status_code=400, detail="Miktar 1'den az olamaz")
        m = loc["market"][body.good]
        player = state["player"]
        inv = player.setdefault("inventory", {})

        if body.action == "al":
            if m["supply"] < body.qty:
                raise HTTPException(status_code=400, detail=f"Stokta sadece {m['supply']} adet var")
            total = round(m["price"] * body.qty, 1)
            if player["money"] < total:
                raise HTTPException(status_code=400, detail="Yeterli paran yok")
            player["money"] = round(player["money"] - total, 1)
            inv[body.good] = inv.get(body.good, 0) + body.qty
            m["supply"] -= body.qty
            m["demand"] += body.qty
            _recompute_prices(loc)
            _push_event(state, state["turn"], "ticaret",
                        f"{player['name']} {loc['name']}'de {body.qty} {body.good} aldı ({total} altın).")
        elif body.action == "sat":
            if inv.get(body.good, 0) < body.qty:
                raise HTTPException(status_code=400, detail="Yeterli ürünün yok")
            total = round(m["price"] * body.qty, 1)
            inv[body.good] -= body.qty
            player["money"] = round(player["money"] + total, 1)
            m["supply"] += body.qty
            m["demand"] = max(1, m["demand"] - body.qty)
            _recompute_prices(loc)
            _push_event(state, state["turn"], "ticaret",
                        f"{player['name']} {loc['name']}'de {body.qty} {body.good} sattı ({total} altın).")
        else:
            raise HTTPException(status_code=400, detail="Geçersiz işlem")

        # Trade training
        from skills import add_skill_xp, add_stat_xp
        add_skill_xp(player, "trade", 1)
        if player["age"] < ADULT_AGE:
            add_stat_xp(player, "charisma", 1)

        progress_quest(state, "inventory_changed")
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    # ---------- job / work ----------
    @router.get("/jobs")
    async def list_jobs(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        return {"jobs": list_eligible_jobs(state["player"])}

    @router.post("/job")
    async def change_job(body: JobIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        if body.profession not in JOB_REQUIREMENTS:
            raise HTTPException(status_code=400, detail="Geçersiz meslek")
        if body.profession == "lord":
            raise HTTPException(status_code=403, detail="Lord olmak için bir kale ele geçirmelisin")
        if state["player"]["age"] < ADULT_AGE and body.profession not in CHILD_ALLOWED_PROFESSIONS:
            raise HTTPException(status_code=403,
                                detail=f"Çocuk olarak sadece şunları yapabilirsin: {', '.join(CHILD_ALLOWED_PROFESSIONS)}")
        ok, reasons = check_job_eligible(state["player"], body.profession)
        if not ok:
            raise HTTPException(status_code=400,
                                detail="Bu meslek için yeterli değilsin: " + "; ".join(reasons))
        state["player"]["profession"] = body.profession
        _push_event(state, state["turn"], "meslek_değişimi",
                    f"{state['player']['name']} artık bir {body.profession}.")
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    @router.post("/work")
    async def work(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        player = state["player"]
        # Income scales with stats and skills
        income_map = {
            "işsiz": (0, 2),
            "köylü": (3, 12), "çiftçi": (8, 25), "asker": (15, 35),
            "tüccar": (20, 60), "avcı": (10, 40), "demirci çırağı": (8, 25),
            "demirci": (25, 80), "zanaatkar": (15, 45), "haydut": (20, 80),
            "lord": (100, 500), "şövalye": (40, 120), "şifacı": (20, 70),
            "katip": (15, 45), "rahip": (15, 50),
        }
        prof = player["profession"]
        lo, hi = income_map.get(prof, (3, 10))
        # Skill bonus
        skills = player.get("skills", {})
        if prof in ("tüccar", "demirci"):
            bonus = 1 + skills.get("trade", 0) * 0.05 + skills.get("crafting", 0) * 0.05
            lo, hi = int(lo * bonus), int(hi * bonus)
        income = random.randint(lo, hi) if hi > lo else lo
        player["money"] = round(player["money"] + income, 1)
        player["health"] = max(20, player["health"] - random.randint(1, 4))
        player["hunger"] = max(0, player.get("hunger", 100) - 4)
        _push_event(state, state["turn"], "çalışma",
                    f"{player['name']} bir hafta {prof} olarak çalıştı, {income} altın kazandı.")

        # Production at current location
        loc = next((l for l in state["world"]["locations"] if l["id"] == player["location_id"]), None)
        if loc:
            from simulation import PRODUCTION
            _ensure_market(loc)
            prod = PRODUCTION.get(prof)
            if prod and prod[0]:
                good, amt = prod
                loc["market"][good]["supply"] += amt * 3
                _recompute_prices(loc)

        # Skill/stat training
        leveled = apply_work_training(player, prof)

        # Child labor still trains stats (early-game shapes adult)
        progress_quest(state, "work")

        advance_time(state, weeks=1)
        outcome = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"state": _decorate(state), "enforcement": outcome,
                "income": income, "leveled": leveled}

    # ---------- crime / attack ----------
    @router.post("/crime")
    async def commit_crime(body: CrimeIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        _require_adult(state, "suç")
        player = state["player"]
        loc = next((l for l in state["world"]["locations"] if l["id"] == player["location_id"]), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum yok")
        difficulty = loc["security"] / 100
        success_chance = max(0.15, 0.85 - difficulty)
        success = random.random() < success_chance
        outcome = {}
        crime_rewards = {
            "hırsızlık": (30, 150), "kaçakçılık": (80, 300),
            "dolandırıcılık": (50, 200), "cinayet": (0, 0),
        }
        if body.crime_type not in crime_rewards:
            raise HTTPException(status_code=400, detail="Geçersiz suç")
        lo, hi = crime_rewards[body.crime_type]
        if success:
            gain = random.randint(lo, hi)
            player["money"] = round(player["money"] + gain, 1)
            player["crime"] = player.get("crime", 0) + {"hırsızlık": 10, "kaçakçılık": 15,
                                                       "dolandırıcılık": 12, "cinayet": 60}[body.crime_type]
            player["reputation"] -= {"hırsızlık": 2, "kaçakçılık": 1,
                                     "dolandırıcılık": 3, "cinayet": 25}[body.crime_type]
            outcome = {"success": True, "gain": gain, "caught": False}
            _push_event(state, state["turn"], "suç",
                        f"{player['name']} {loc['name']}'de gizlice {body.crime_type} yaptı.")
        else:
            fine = random.randint(50, 200)
            paid = min(player["money"], fine)
            player["money"] = round(player["money"] - paid, 1)
            player["crime"] = player.get("crime", 0) + 5
            player["reputation"] -= 5
            outcome = {"success": False, "fine": paid, "caught": True}
            _push_event(state, state["turn"], "suç_yakalandı",
                        f"{player['name']} {body.crime_type} yaparken yakalandı, {paid} altın ceza ödedi.")
        advance_time(state, weeks=1)
        enf = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"state": _decorate(state), "outcome": outcome, "enforcement": enf}

    @router.post("/attack_npc")
    async def attack_npc(body: AttackIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        _require_adult(state, "saldırı")
        npc = next((n for n in state["world"]["npcs"] if n["id"] == body.npc_id), None)
        if not npc or not npc["alive"]:
            raise HTTPException(status_code=404, detail="Hedef bulunamadı veya ölü")
        if npc["location_id"] != state["player"]["location_id"]:
            raise HTTPException(status_code=400, detail="Hedef burada değil")

        player = state["player"]
        log = []
        log.append(f"{npc['name']}'a saldırdın!")
        eq = equipment_bonuses(player)
        enemy_atk = 6 + npc_status(npc) * 3 + random.randint(0, 4)
        enemy_hp = 30 + npc_status(npc) * 15 + random.randint(0, 20)
        player_atk = (5 + player["stats"].get("strength", 1) * 2
                      + player["skills"].get("combat", 0) * 2 + eq["attack"])
        player_def = eq["defense"]
        player_hp = player["health"]
        rounds = 0
        while enemy_hp > 0 and player_hp > 0 and rounds < 14:
            rounds += 1
            dmg = random.randint(max(1, player_atk - 5), player_atk + 5)
            enemy_hp -= dmg
            log.append(f"Tur {rounds}: {npc['name']}'a {dmg} hasar. (kalan: {max(0, enemy_hp)})")
            if enemy_hp <= 0:
                break
            edmg = max(1, random.randint(max(1, enemy_atk - 3), enemy_atk + 3) - player_def)
            player_hp = max(0, player_hp - edmg)
            log.append(f"        Sen {edmg} hasar aldın. (canın: {player_hp})")
        player["health"] = player_hp
        if player_hp <= 0:
            player["health"] = 5
            player["money"] = round(player["money"] * 0.6, 1)
            log.append(f"{npc['name']} seni dövdü, kaçtın.")
            _push_event(state, state["turn"], "savaş_kaybı",
                        f"{player['name']}, {npc['name']}'a saldırdı ama kaybetti.")
            outcome = "kayıp"
        else:
            npc["alive"] = False
            log.append(f"{npc['name']} öldü.")
            crime_add = 40 + npc_status(npc) * 20
            rep_loss = 8 + npc_status(npc) * 10
            player["crime"] = player.get("crime", 0) + crime_add
            player["reputation"] = player.get("reputation", 0) - rep_loss
            _push_event(state, state["turn"], "cinayet",
                        f"{player['name']}, {npc['name']}'i öldürdü ({npc.get('location_name','?')})")
            if npc["profession"] in ("kral", "veliaht", "lord", "general"):
                if npc["kingdom_id"] not in player.setdefault("wanted_in", []):
                    player["wanted_in"].append(npc["kingdom_id"])
                player["crime"] += 50
                _push_event(state, state["turn"], "ödül",
                            f"{npc['kingdom_name']}, {player['name']}'in başına ödül koydu.")
            kingdom = next((k for k in state["world"]["kingdoms"] if k["king_id"] == npc["id"]), None)
            if kingdom:
                heir = next((n for n in state["world"]["npcs"] if n["id"] == kingdom["heir_id"] and n["alive"]), None)
                if heir:
                    heir["profession"] = "kral"
                    kingdom["king_id"] = heir["id"]
                    _push_event(state, state["turn"], "tahta_çıkış",
                                f"{heir['name']}, {kingdom['name']} tahtına çıktı.")
            from skills import add_skill_xp, add_stat_xp
            add_skill_xp(player, "combat", 4)
            add_stat_xp(player, "strength", 2)
            outcome = "zafer"

        advance_time(state, weeks=1)
        enf = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"log": log, "outcome": outcome, "state": _decorate(state), "enforcement": enf}

    # ---------- items ----------
    @router.post("/use_item")
    async def use_item(body: UseItemIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        item = ITEMS.get(body.item)
        if not item:
            raise HTTPException(status_code=404, detail="Eşya bulunamadı")
        inv = state["player"].setdefault("inventory", {})
        if inv.get(body.item, 0) < body.qty:
            raise HTTPException(status_code=400, detail="Envanterinde yeterli yok")
        applied = apply_use_effects(state["player"], body.item, body.qty)
        if applied is None:
            raise HTTPException(status_code=400, detail="Bu eşya tüketilemez. Belki kuşanılabilir?")
        inv[body.item] -= body.qty
        if inv[body.item] <= 0:
            inv.pop(body.item, None)
        _push_event(state, state["turn"], "kullanım",
                    f"{state['player']['name']} {item['name']} kullandı.")
        progress_quest(state, "inventory_changed")
        await _save_state(db, user["_id"], state)
        return {"state": _decorate(state), "applied": applied,
                "item_name": item["name"]}

    @router.post("/equip")
    async def equip(body: EquipIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        item = ITEMS.get(body.item)
        if not item or not item.get("slot"):
            raise HTTPException(status_code=400, detail="Bu eşya kuşanılamaz")
        inv = state["player"].setdefault("inventory", {})
        if inv.get(body.item, 0) < 1:
            raise HTTPException(status_code=400, detail="Envanterinde yok")
        slot = item["slot"]
        equipment = state["player"].setdefault("equipment", {s: None for s in EQUIPMENT_SLOTS})
        # Swap currently equipped item back to inventory
        current = equipment.get(slot)
        if current:
            inv[current] = inv.get(current, 0) + 1
        inv[body.item] -= 1
        if inv[body.item] <= 0:
            inv.pop(body.item, None)
        equipment[slot] = body.item
        _push_event(state, state["turn"], "kuşanma",
                    f"{state['player']['name']} {item['name']} kuşandı.")
        progress_quest(state, "equip", {"item": body.item})
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    @router.post("/unequip")
    async def unequip(body: UnequipIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        if body.slot not in EQUIPMENT_SLOTS:
            raise HTTPException(status_code=400, detail="Geçersiz slot")
        equipment = state["player"].setdefault("equipment", {s: None for s in EQUIPMENT_SLOTS})
        current = equipment.get(body.slot)
        if not current:
            raise HTTPException(status_code=400, detail="Bu slotta eşya yok")
        inv = state["player"].setdefault("inventory", {})
        inv[current] = inv.get(current, 0) + 1
        equipment[body.slot] = None
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    @router.get("/items")
    async def list_items():
        return {"items": ITEMS, "slots": EQUIPMENT_SLOTS}

    # ---------- skills/perks ----------
    @router.get("/skills")
    async def skills(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        return {
            "stats": state["player"].get("stats", {}),
            "stat_xp": state["player"].get("stat_xp", {}),
            "skills": state["player"].get("skills", {}),
            "skill_xp": state["player"].get("skill_xp", {}),
            "perks": unlocked_perks(state["player"]),
            "tree": SKILL_PERKS,
        }

    # ---------- family quests ----------
    @router.get("/family-quests")
    async def get_family_quests(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        return {"quests": state.get("family_quests", []), "player_age": state["player"]["age"]}

    # ---------- quests (general world) ----------
    @router.post("/quest/accept")
    async def accept_quest(body: QuestIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        _require_adult(state, "dış görev")
        quest = next((q for q in state["quests"] if q["id"] == body.quest_id), None)
        if not quest:
            raise HTTPException(status_code=404, detail="Görev yok")
        if quest["status"] != "açık":
            raise HTTPException(status_code=400, detail="Görev kabul edilemez")
        quest["status"] = "kabul_edildi"
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    @router.post("/quest/complete")
    async def complete_quest(body: QuestIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        _require_adult(state, "görev tamamlama")
        quest = next((q for q in state["quests"] if q["id"] == body.quest_id), None)
        if not quest:
            raise HTTPException(status_code=404, detail="Görev yok")
        if quest["status"] not in ("kabul_edildi", "açık"):
            raise HTTPException(status_code=400, detail="Görev tamamlanamaz")
        # Skill-based outcome
        skills = state["player"]["skills"]
        if quest["type"] == "haydut_yuvası":
            skill = skills.get("combat", 0)
        elif quest["type"] == "ticaret_fırsatı":
            skill = skills.get("trade", 0)
        elif quest["type"] == "kayıp_çocuk":
            skill = skills.get("social", 0)
        else:
            skill = skills.get("social", 0)
        chance = min(0.95, 0.4 + skill * 0.08)
        if random.random() < chance:
            state["player"]["money"] = round(state["player"]["money"] + quest["reward"], 1)
            state["player"]["reputation"] += 2
            quest["status"] = "tamamlandı"
            _push_event(state, state["turn"], "görev_tamamlandı",
                        f"{state['player']['name']} '{quest['title']}' görevini tamamladı.")
        else:
            quest["status"] = "başarısız"
            state["player"]["reputation"] -= 1
            _push_event(state, state["turn"], "görev_başarısız",
                        f"{state['player']['name']} '{quest['title']}' görevinde başarısız oldu.")
        advance_time(state, weeks=1)
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    # ---------- battle (random encounter) ----------
    @router.post("/battle")
    async def battle(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        _require_adult(state, "savaş")
        player = state["player"]
        eq = equipment_bonuses(player)
        log = []
        enemy_hp = random.randint(40, 90)
        enemy_atk = random.randint(8, 18)
        enemy_name = random.choice(["Haydut", "Asker", "Paralı asker", "Hain", "Sınır eşkıyası"])
        log.append(f"Karşına bir {enemy_name} çıktı! ({enemy_hp} can)")
        player_atk = (5 + player["stats"].get("strength", 1) * 2
                      + player["skills"].get("combat", 0) * 2 + eq["attack"])
        player_def = eq["defense"]
        rounds = 0
        while enemy_hp > 0 and player["health"] > 0 and rounds < 12:
            rounds += 1
            dmg = random.randint(max(1, player_atk - 5), player_atk + 5)
            enemy_hp -= dmg
            log.append(f"Tur {rounds}: {dmg} hasar verdin. Düşman canı: {max(0, enemy_hp)}")
            if enemy_hp <= 0:
                break
            edmg = max(1, random.randint(enemy_atk - 3, enemy_atk + 3) - player_def)
            player["health"] = max(0, player["health"] - edmg)
            log.append(f"        {edmg} hasar aldın. Canın: {player['health']}")
        if player["health"] <= 0:
            outcome = "kayıp"
            player["health"] = 5
            player["money"] = round(player["money"] * 0.7, 1)
            log.append("Yenildin. Bilincin yerine geldiğinde paranın bir kısmı çalınmıştı.")
            _push_event(state, state["turn"], "savaş_kaybı", f"{player['name']} bir çatışmada yenildi.")
        else:
            outcome = "zafer"
            loot = random.randint(20, 120)
            player["money"] = round(player["money"] + loot, 1)
            player["reputation"] += 1
            log.append(f"Zafer! {loot} altın ganimet aldın.")
            _push_event(state, state["turn"], "savaş_zaferi",
                        f"{player['name']} bir {enemy_name}'ı yendi.")
            from skills import add_skill_xp, add_stat_xp
            add_skill_xp(player, "combat", 3)
            add_stat_xp(player, "strength", 1)
        advance_time(state, weeks=1)
        await _save_state(db, user["_id"], state)
        return {"log": log, "outcome": outcome, "state": _decorate(state)}

    # ---------- marry ----------
    @router.post("/marry")
    async def marry(body: MarryIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        _require_adult(state, "evlilik")
        if state["player"].get("spouse_id"):
            raise HTTPException(status_code=400, detail="Zaten evlisin")
        npc = next((n for n in state["world"]["npcs"] if n["id"] == body.npc_id), None)
        if not npc or not npc["alive"]:
            raise HTTPException(status_code=404, detail="NPC yok")
        if npc["spouse_id"]:
            raise HTTPException(status_code=400, detail="Bu kişi zaten evli")
        if npc["age"] < 18:
            raise HTTPException(status_code=400, detail="Çok genç")
        rel = state["relationships"].get(npc["id"], 0)
        if rel < 60:
            raise HTTPException(status_code=400, detail="İlişkiniz evlilik için yeterince güçlü değil (60+)")
        state["player"]["spouse_id"] = npc["id"]
        npc["spouse_id"] = "PLAYER"
        _push_event(state, state["turn"], "evlilik",
                    f"{state['player']['name']} ile {npc['name']} dünya evine girdi.")
        await _save_state(db, user["_id"], state)
        return _decorate(state)

    return router
