"""Game API endpoints — new game, state, advance time, actions, NPC chat, quests."""
import random
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from auth import make_get_current_user
from world_gen import generate_world, generate_player, initial_history, new_id
from simulation import advance_time, _push_event
from dialogue import generate_response, relation_band, DIALOG_TOPICS


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
    crime_type: str  # "hırsızlık", "kaçakçılık", "dolandırıcılık", "cinayet"
    target_npc_id: Optional[str] = None


class JobIn(BaseModel):
    profession: str


class QuestIn(BaseModel):
    quest_id: str


class MarryIn(BaseModel):
    npc_id: str


def _ensure_state(state):
    state.setdefault("relationships", {})
    state.setdefault("quests", [])
    state.setdefault("day", 0)
    state.setdefault("history", [])
    return state


async def _load_state(db, user_id: str):
    state = await db.game_states.find_one({"user_id": user_id})
    if not state:
        raise HTTPException(status_code=404, detail="Aktif oyun bulunamadı")
    state.pop("_id", None)
    return _ensure_state(state)


async def _save_state(db, user_id: str, state: dict):
    state["user_id"] = user_id
    await db.game_states.update_one(
        {"user_id": user_id},
        {"$set": state},
        upsert=True,
    )


def build_game_router(db):
    router = APIRouter(prefix="/api/game", tags=["game"])
    get_current_user = make_get_current_user(db)

    @router.post("/new")
    async def new_game(user: dict = Depends(get_current_user)):
        world = generate_world(**WORLD_DEFAULTS)
        player = generate_player(world)
        state = {
            "user_id": user["_id"],
            "day": 0,
            "world": world,
            "player": player,
            "relationships": {},
            "quests": [],
            "history": initial_history(),
        }
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
            raise HTTPException(status_code=404, detail="NPC bulunamadı")
        rel = state["relationships"].get(npc["id"], 0)
        response = generate_response(
            npc, rel, body.topic, state["player"]["name"],
            state["history"],
        )
        # Talking slightly nudges relationship
        delta = 1 if body.topic in ("selam", "aile", "hedef") else 0
        if body.topic == "üzgün" and "merhametli" in npc["personality"]:
            delta = 2
        state["relationships"][npc["id"]] = max(-100, min(100, rel + delta))
        await _save_state(db, user["_id"], state)
        return {"response": response, "relationship": state["relationships"][npc["id"]],
                "band": relation_band(state["relationships"][npc["id"]])}

    @router.get("/dialog-topics")
    async def dialog_topics():
        return [{"id": t[0], "label": t[1]} for t in DIALOG_TOPICS]

    @router.post("/travel")
    async def travel(body: TravelIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        loc = next((l for l in state["world"]["locations"] if l["id"] == body.location_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum bulunamadı")
        state["player"]["location_id"] = loc["id"]
        state["player"]["location_name"] = loc["name"]
        _push_event(state, state["day"],
                    "yolculuk",
                    f"{state['player']['name']} {loc['name']}'e doğru yola çıktı.")
        # Travel costs some time
        advance_time(state, days=3)
        await _save_state(db, user["_id"], state)
        return state

    @router.post("/trade")
    async def trade(body: TradeIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        loc = next((l for l in state["world"]["locations"] if l["id"] == body.location_id), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum bulunamadı")
        if body.good not in loc["prices"]:
            raise HTTPException(status_code=400, detail="Geçersiz ürün")
        if body.qty < 1:
            raise HTTPException(status_code=400, detail="Miktar 1'den az olamaz")
        price = loc["prices"][body.good]
        total = round(price * body.qty, 1)
        player = state["player"]
        inv = player.setdefault("inventory", {})
        if body.action == "al":
            if player["money"] < total:
                raise HTTPException(status_code=400, detail="Yeterli paran yok")
            player["money"] -= total
            inv[body.good] = inv.get(body.good, 0) + body.qty
            _push_event(state, state["day"], "ticaret",
                        f"{player['name']} {loc['name']}'de {body.qty} {body.good} satın aldı.")
        elif body.action == "sat":
            if inv.get(body.good, 0) < body.qty:
                raise HTTPException(status_code=400, detail="Yeterli ürünün yok")
            inv[body.good] -= body.qty
            player["money"] = round(player["money"] + total, 1)
            _push_event(state, state["day"], "ticaret",
                        f"{player['name']} {loc['name']}'de {body.qty} {body.good} sattı.")
        else:
            raise HTTPException(status_code=400, detail="Geçersiz işlem")
        # Trade slightly affects local price
        loc["prices"][body.good] = max(1.0, round(price * (1.02 if body.action == "al" else 0.98), 1))
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
        """Player works one week at their current profession."""
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
        advance_time(state, days=7)
        await _save_state(db, user["_id"], state)
        return state

    @router.post("/crime")
    async def commit_crime(body: CrimeIn, user: dict = Depends(get_current_user)):
        state = await _load_state(db, user["_id"])
        player = state["player"]
        loc = next((l for l in state["world"]["locations"] if l["id"] == player["location_id"]), None)
        if not loc:
            raise HTTPException(status_code=404, detail="Konum yok")
        # Success based on location security
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
            # Caught
            fine = random.randint(50, 200)
            paid = min(player["money"], fine)
            player["money"] = round(player["money"] - paid, 1)
            player["crime"] = player.get("crime", 0) + 5
            player["reputation"] -= 5
            outcome = {"success": False, "fine": paid, "caught": True}
            _push_event(state, state["day"], "suç_yakalandı",
                        f"{player['name']} {body.crime_type} yaparken yakalandı, {paid} altın ceza ödedi.")
        advance_time(state, days=1)
        await _save_state(db, user["_id"], state)
        return {"state": state, "outcome": outcome}

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
        # Simple success chance based on skills and quest type
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
        """Simple text-based battle: player vs random enemy at current location."""
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
