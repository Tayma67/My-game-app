"""Game API endpoints — new game, state, advance time, actions, NPC chat, quests."""
import random
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from auth import make_get_current_user
from world_gen import generate_world, generate_player, initial_history, new_id
from simulation import advance_time, _push_event, _ensure_state_fields, _recompute_prices, soldier_check
from dialogue import (
    generate_response, relation_band, relationship_delta,
    DIALOG_TOPICS, npc_status, player_status, SOCIAL_STATUS,
)


WORLD_DEFAULTS = {
    "n_kingdoms": 3,
    "n_cities": 3,
    "n_villages": 10,
    "n_castles": 5,
    "n_npcs": 100,
}


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


async def _load_state(db, user_id: str):
    state = await db.game_states.find_one({"user_id": user_id})
    if not state:
        raise HTTPException(status_code=404, detail="Aktif oyun bulunamadı")
    state.pop("_id", None)
    _ensure_state_fields(state)
    return state


async def _save_state(db, user_id: str, state: dict):
    state["user_id"] = user_id
    await db.game_states.update_one(
        {"user_id": user_id}, {"$set": state}, upsert=True
    )


def build_game_router(db):
    router = APIRouter(prefix="/api/game", tags=["game"])
    get_current_user = make_get_current_user(db)

    @router.post("/new")
    async def new_game(user: dict = Depends(get_current_user)):
        world = generate_world(**WORLD_DEFAULTS)
        player = generate_player(world)
        state = {
            "user_id": user["_id"], "day": 0,
            "world": world, "player": player,
            "relationships": {}, "quests": [], "history": initial_history(),
        }
        _ensure_state_fields(state)
        await _save_state(db, user["_id"], state)
        return state

    @router.get("/state")
    async def get_state(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        return state

    @router.delete("/state")
    async def delete_state(user: dict = Depends(get_current_user)):
        await db.game_states.delete_one({"user_id": user["_id"]})
        return {"ok": True}

    @router.post("/advance")
    async def advance(days: int = 7, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        advance_time(state, days=days)
        await _save_state(db, user["_id"], state)
        return state

    @router.post("/chat")
    async def chat(body: ChatIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        npc = next((n for n in state["world"]["npcs"] if n["id"] == body.npc_id), None)
        if not npc or not npc["alive"]:
            raise HTTPException(status_code=404, detail="NPC bulunamadı veya ölü")

        # Hostile detection - enemies attack on sight
        rel = state["relationships"].get(npc["id"], 0)
        if rel <= -70 and npc["profession"] in ("asker", "lord", "haydut") and body.topic == "selam":
            return {
                "response": f"{npc['name']} kılıcını çekti! Konuşma değil savaş istiyor.",
                "relationship": rel,
                "band": relation_band(rel),
                "hostile": True,
            }

        # Track turn count for response variation & repeat-irritation
        npc["interactions"][body.topic] = npc["interactions"].get(body.topic, 0) + 1
        npc["turn_counter"] = npc.get("turn_counter", 0) + 1
        repeat = npc["interactions"][body.topic]

        # Hint merchant about local supply
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

        response = generate_response(
            npc, rel, body.topic, state["player"],
            state["history"], state["day"], npc["turn_counter"],
        )

        delta = relationship_delta(npc, body.topic, state["player"], repeat)
        new_rel = max(-100, min(100, rel + delta))
        state["relationships"][npc["id"]] = new_rel

        # Memory entry
        npc.setdefault("memory", []).append({
            "day": state["day"],
            "topic": body.topic,
            "delta": delta,
            "player_rep": state["player"].get("reputation", 0),
            "player_crime": state["player"].get("crime", 0),
        })
        if len(npc["memory"]) > 20:
            npc["memory"] = npc["memory"][-20:]

        # Strip transient field
        npc.pop("_loc_supply_signal", None)

        await _save_state(db, user["_id"], state)
        return {
            "response": response,
            "relationship": new_rel,
            "band": relation_band(new_rel),
            "repeat_count": repeat,
            "delta": delta,
        }

    @router.get("/dialog-topics")
    async def dialog_topics():
        return [{"id": t[0], "label": t[1]} for t in DIALOG_TOPICS]

    @router.post("/travel")
    async def travel(body: TravelIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        loc = next((l for l in state["world"]["locations"] if l["id"] == body.location_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum bulunamadı")
        # Wanted-in check
        if loc["kingdom_id"] in state["player"].get("wanted_in", []):
            return {
                "state": state,
                "blocked": True,
                "message": f"{loc['name']} {loc['kingdom_name']} sınırlarında, oraya başın için ödül var.",
            }
        state["player"]["location_id"] = loc["id"]
        state["player"]["location_name"] = loc["name"]
        _push_event(state, state["day"], "yolculuk",
                    f"{state['player']['name']} {loc['name']}'e doğru yola çıktı.")
        advance_time(state, days=3)
        # Arrival enforcement
        outcome = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"state": state, "enforcement": outcome}

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
            m["demand"] += body.qty  # buying signals demand
            _recompute_prices(loc)
            _push_event(state, state["day"], "ticaret",
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
            _push_event(state, state["day"], "ticaret",
                        f"{player['name']} {loc['name']}'de {body.qty} {body.good} sattı ({total} altın).")
        else:
            raise HTTPException(status_code=400, detail="Geçersiz işlem")

        await _save_state(db, user["_id"], state)
        return state

    @router.post("/job")
    async def change_job(body: JobIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        valid = ["tüccar", "asker", "lord", "haydut", "çiftçi", "avcı", "zanaatkar", "köylü"]
        if body.profession not in valid:
            raise HTTPException(status_code=400, detail="Geçersiz meslek")
        if body.profession == "lord":
            raise HTTPException(status_code=403, detail="Lord olmak için bir kale ele geçirmelisin")
        state["player"]["profession"] = body.profession
        _push_event(state, state["day"], "meslek_değişimi",
                    f"{state['player']['name']} artık bir {body.profession}.")
        await _save_state(db, user["_id"], state)
        return state

    @router.post("/work")
    async def work(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        player = state["player"]
        income_map = {
            "köylü": (5, 20), "çiftçi": (10, 30), "asker": (15, 35),
            "tüccar": (20, 60), "avcı": (10, 40), "demirci çırağı": (8, 25),
            "zanaatkar": (15, 40), "haydut": (20, 80), "lord": (100, 500),
        }
        lo, hi = income_map.get(player["profession"], (5, 20))
        income = random.randint(lo, hi)
        player["money"] = round(player["money"] + income, 1)
        player["health"] = max(20, player["health"] - random.randint(1, 5))
        _push_event(state, state["day"], "çalışma",
                    f"{player['name']} bir hafta {player['profession']} olarak çalıştı, {income} altın kazandı.")

        # Profession-driven production at current location
        loc = next((l for l in state["world"]["locations"] if l["id"] == player["location_id"]), None)
        if loc:
            from simulation import PRODUCTION, _ensure_market, _recompute_prices as _rp
            _ensure_market(loc)
            prod = PRODUCTION.get(player["profession"])
            if prod and prod[0]:
                good, amt = prod
                loc["market"][good]["supply"] += amt * 3
                _rp(loc)

        advance_time(state, days=7)
        outcome = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"state": state, "enforcement": outcome, "income": income}

    @router.post("/crime")
    async def commit_crime(body: CrimeIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
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
            _push_event(state, state["day"], "suç",
                        f"{player['name']} {loc['name']}'de gizlice {body.crime_type} yaptı.")
            if body.crime_type == "cinayet" and body.target_npc_id:
                target = next((n for n in state["world"]["npcs"] if n["id"] == body.target_npc_id), None)
                if target and target["alive"]:
                    target["alive"] = False
                    _push_event(state, state["day"], "ölüm",
                                f"{target['name']} esrarengiz biçimde öldü.")
        else:
            fine = random.randint(50, 200)
            paid = min(player["money"], fine)
            player["money"] = round(player["money"] - paid, 1)
            player["crime"] = player.get("crime", 0) + 5
            player["reputation"] -= 5
            outcome = {"success": False, "fine": paid, "caught": True}
            _push_event(state, state["day"], "suç_yakalandı",
                        f"{player['name']} {body.crime_type} yaparken yakalandı, {paid} altın ceza ödedi.")
        advance_time(state, days=1)
        enf = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"state": state, "outcome": outcome, "enforcement": enf}

    @router.post("/attack_npc")
    async def attack_npc(body: AttackIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        npc = next((n for n in state["world"]["npcs"] if n["id"] == body.npc_id), None)
        if not npc or not npc["alive"]:
            raise HTTPException(status_code=404, detail="Hedef bulunamadı veya ölü")
        if npc["location_id"] != state["player"]["location_id"]:
            raise HTTPException(status_code=400, detail="Hedef burada değil")

        player = state["player"]
        log = []
        log.append(f"{npc['name']}'a saldırdın!")
        # Enemy strength scales with status
        enemy_atk = 6 + npc_status(npc) * 3 + random.randint(0, 4)
        enemy_hp = 30 + npc_status(npc) * 15 + random.randint(0, 20)
        player_atk = 10 + player["skills"].get("savaş", 1) * 3
        player_hp = player["health"]
        rounds = 0
        while enemy_hp > 0 and player_hp > 0 and rounds < 14:
            rounds += 1
            dmg = random.randint(max(1, player_atk - 5), player_atk + 5)
            enemy_hp -= dmg
            log.append(f"Tur {rounds}: {npc['name']}'a {dmg} hasar. (kalan: {max(0, enemy_hp)})")
            if enemy_hp <= 0:
                break
            edmg = random.randint(max(1, enemy_atk - 3), enemy_atk + 3)
            player_hp = max(0, player_hp - edmg)
            log.append(f"        Sen {edmg} hasar aldın. (canın: {player_hp})")
        player["health"] = player_hp
        if player_hp <= 0:
            # Player loses
            player["health"] = 5
            player["money"] = round(player["money"] * 0.6, 1)
            log.append(f"{npc['name']} seni dövdü, kaçtın.")
            _push_event(state, state["day"], "savaş_kaybı",
                        f"{player['name']}, {npc['name']}'a saldırdı ama kaybetti.")
            outcome = "kayıp"
        else:
            npc["alive"] = False
            log.append(f"{npc['name']} öldü.")
            crime_add = 40 + npc_status(npc) * 20
            rep_loss = 8 + npc_status(npc) * 10
            player["crime"] = player.get("crime", 0) + crime_add
            player["reputation"] = player.get("reputation", 0) - rep_loss
            _push_event(state, state["day"], "cinayet",
                        f"{player['name']}, {npc['name']}'i öldürdü ({loc_name_of(state, npc)})")
            # Royal kills make player wanted
            if npc["profession"] in ("kral", "veliaht", "lord", "general"):
                if npc["kingdom_id"] not in player.setdefault("wanted_in", []):
                    player["wanted_in"].append(npc["kingdom_id"])
                player["crime"] += 50
                _push_event(state, state["day"], "ödül",
                            f"{npc['kingdom_name']}, {player['name']}'in başına ödül koydu.")
            # Royal succession if king/heir
            kingdom = next((k for k in state["world"]["kingdoms"] if k["king_id"] == npc["id"]), None)
            if kingdom:
                heir = next((n for n in state["world"]["npcs"] if n["id"] == kingdom["heir_id"] and n["alive"]), None)
                if heir:
                    heir["profession"] = "kral"
                    kingdom["king_id"] = heir["id"]
                    _push_event(state, state["day"], "tahta_çıkış",
                                f"{heir['name']}, {kingdom['name']} tahtına çıktı.")
            outcome = "zafer"

        advance_time(state, days=1)
        enf = soldier_check(state)
        await _save_state(db, user["_id"], state)
        return {"log": log, "outcome": outcome, "state": state, "enforcement": enf}

    @router.post("/quest/accept")
    async def accept_quest(body: QuestIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        quest = next((q for q in state["quests"] if q["id"] == body.quest_id), None)
        if not quest:
            raise HTTPException(status_code=404, detail="Görev yok")
        if quest["status"] != "açık":
            raise HTTPException(status_code=400, detail="Görev kabul edilemez")
        quest["status"] = "kabul_edildi"
        await _save_state(db, user["_id"], state)
        return state

    @router.post("/quest/complete")
    async def complete_quest(body: QuestIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        quest = next((q for q in state["quests"] if q["id"] == body.quest_id), None)
        if not quest:
            raise HTTPException(status_code=404, detail="Görev yok")
        if quest["status"] not in ("kabul_edildi", "açık"):
            raise HTTPException(status_code=400, detail="Görev tamamlanamaz")
        skill = state["player"]["skills"].get("diplomasi", 1)
        if quest["type"] == "haydut_yuvası":
            skill = state["player"]["skills"].get("savaş", 1)
        elif quest["type"] == "ticaret_fırsatı":
            skill = state["player"]["skills"].get("ticaret", 1)
        elif quest["type"] == "kayıp_çocuk":
            skill = state["player"]["skills"].get("avcılık", 1)
        chance = min(0.95, 0.4 + skill * 0.08)
        if random.random() < chance:
            state["player"]["money"] = round(state["player"]["money"] + quest["reward"], 1)
            state["player"]["reputation"] += 2
            quest["status"] = "tamamlandı"
            _push_event(state, state["day"], "görev_tamamlandı",
                        f"{state['player']['name']} '{quest['title']}' görevini tamamladı.")
        else:
            quest["status"] = "başarısız"
            state["player"]["reputation"] -= 1
            _push_event(state, state["day"], "görev_başarısız",
                        f"{state['player']['name']} '{quest['title']}' görevinde başarısız oldu.")
        advance_time(state, days=2)
        await _save_state(db, user["_id"], state)
        return state

    @router.post("/battle")
    async def battle(user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        player = state["player"]
        log = []
        enemy_hp = random.randint(40, 90)
        enemy_atk = random.randint(8, 18)
        enemy_name = random.choice(["Haydut", "Asker", "Paralı asker", "Hain", "Sınır eşkıyası"])
        log.append(f"Karşına bir {enemy_name} çıktı! ({enemy_hp} can)")
        player_atk = 10 + player["skills"].get("savaş", 1) * 3
        rounds = 0
        while enemy_hp > 0 and player["health"] > 0 and rounds < 12:
            rounds += 1
            dmg = random.randint(player_atk - 5, player_atk + 5)
            enemy_hp -= dmg
            log.append(f"Tur {rounds}: {dmg} hasar verdin. Düşman canı: {max(0, enemy_hp)}")
            if enemy_hp <= 0:
                break
            edmg = random.randint(enemy_atk - 3, enemy_atk + 3)
            player["health"] = max(0, player["health"] - edmg)
            log.append(f"        {edmg} hasar aldın. Canın: {player['health']}")
        if player["health"] <= 0:
            outcome = "kayıp"
            player["health"] = 5
            player["money"] = round(player["money"] * 0.7, 1)
            log.append("Yenildin. Bilincin yerine geldiğinde paranın bir kısmı çalınmıştı.")
            _push_event(state, state["day"], "savaş_kaybı", f"{player['name']} bir çatışmada yenildi.")
        else:
            outcome = "zafer"
            loot = random.randint(20, 120)
            player["money"] = round(player["money"] + loot, 1)
            player["reputation"] += 1
            log.append(f"Zafer! {loot} altın ganimet aldın.")
            _push_event(state, state["day"], "savaş_zaferi",
                        f"{player['name']} bir {enemy_name}'ı yendi.")
        advance_time(state, days=1)
        await _save_state(db, user["_id"], state)
        return {"log": log, "outcome": outcome, "state": state}

    @router.post("/marry")
    async def marry(body: MarryIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
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
        _push_event(state, state["day"], "evlilik",
                    f"{state['player']['name']} ile {npc['name']} dünya evine girdi.")
        await _save_state(db, user["_id"], state)
        return state

    return router


def loc_name_of(state, npc):
    return npc.get("location_name", "?")
