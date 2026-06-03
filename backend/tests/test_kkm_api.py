"""End-to-end backend tests for Kronikler: Küllerin Mirası.

Covers auth (register/login/me), game lifecycle (new/state/advance), and all
game action endpoints (chat, travel, trade, work, job, crime, quest, battle, marry).
"""
import os
import uuid
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load frontend .env so REACT_APP_BACKEND_URL is reliably resolved
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---------------------------- fixtures ----------------------------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def test_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{suffix}@k.com",
        "password": "test123",
        "name": f"Tester_{suffix}",
    }


@pytest.fixture(scope="session")
def auth_token(session, test_user):
    r = session.post(f"{API}/auth/register", json=test_user, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["user"]["email"] == test_user["email"]
    return data["token"]


@pytest.fixture(scope="session")
def auth_session(session, auth_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    })
    return s


@pytest.fixture(scope="session")
def fresh_game(auth_session):
    # Delete any previous state then create new
    auth_session.delete(f"{API}/game/state", timeout=30)
    r = auth_session.post(f"{API}/game/new", timeout=60)
    assert r.status_code == 200, f"new game failed: {r.status_code} {r.text}"
    return r.json()


# ---------------------------- AUTH ----------------------------
class TestAuth:
    def test_health(self, session):
        r = session.get(f"{API}/", timeout=20)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_register_duplicate_rejected(self, session, test_user, auth_token):
        # auth_token fixture has already registered
        r = session.post(f"{API}/auth/register", json=test_user, timeout=20)
        assert r.status_code == 400

    def test_login_success(self, session, test_user, auth_token):
        r = session.post(f"{API}/auth/login",
                         json={"email": test_user["email"], "password": test_user["password"]},
                         timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and d["user"]["email"] == test_user["email"]

    def test_login_invalid(self, session, test_user):
        r = session.post(f"{API}/auth/login",
                         json={"email": test_user["email"], "password": "wrong!!"},
                         timeout=20)
        assert r.status_code == 401

    def test_me_with_token(self, auth_session, test_user):
        r = auth_session.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 200
        assert r.json()["email"] == test_user["email"]

    def test_me_without_token(self, session):
        r = session.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 401


# ---------------------------- WORLD GEN / STATE ----------------------------
class TestWorldGen:
    def test_world_counts(self, fresh_game):
        world = fresh_game["world"]
        assert len(world["kingdoms"]) == 3
        cities = [l for l in world["locations"] if l["kind"] == "şehir"]
        villages = [l for l in world["locations"] if l["kind"] == "köy"]
        castles = [l for l in world["locations"] if l["kind"] == "kale"]
        assert len(cities) == 3
        assert len(villages) == 10
        assert len(castles) == 5
        # NPCs ~ 100 (within tolerance)
        assert 95 <= len(world["npcs"]) <= 110, f"npc count: {len(world['npcs'])}"

    def test_kings_and_heirs(self, fresh_game):
        for k in fresh_game["world"]["kingdoms"]:
            assert k["king_id"], "king_id missing"
            assert k["heir_id"], "heir_id missing"
            king = next((n for n in fresh_game["world"]["npcs"] if n["id"] == k["king_id"]), None)
            heir = next((n for n in fresh_game["world"]["npcs"] if n["id"] == k["heir_id"]), None)
            assert king and king["profession"] == "kral"
            assert heir and heir["profession"] == "veliaht"

    def test_player_initialised(self, fresh_game):
        p = fresh_game["player"]
        assert p["health"] == 100
        assert "location_id" in p and p["location_name"]
        assert p["money"] > 0
        assert "inventory" in p

    def test_get_state(self, auth_session, fresh_game):
        r = auth_session.get(f"{API}/game/state", timeout=30)
        assert r.status_code == 200
        s = r.json()
        assert s["player"]["name"] == fresh_game["player"]["name"]
        assert s["day"] == 0


# ---------------------------- ADVANCE ----------------------------
class TestAdvance:
    def test_advance_seven_days(self, auth_session):
        before = auth_session.get(f"{API}/game/state").json()
        r = auth_session.post(f"{API}/game/advance?days=7", timeout=30)
        assert r.status_code == 200
        after = r.json()
        assert after["day"] == before["day"] + 7
        assert len(after["history"]) >= len(before["history"])


# ---------------------------- CHAT ----------------------------
class TestChat:
    def test_all_topics(self, auth_session):
        state = auth_session.get(f"{API}/game/state").json()
        alive = [n for n in state["world"]["npcs"] if n["alive"]]
        assert alive, "no alive NPCs"
        npc = alive[0]
        topics = ["selam", "iş", "aile", "dünya", "üzgün", "hedef", "veda"]
        for t in topics:
            r = auth_session.post(f"{API}/game/chat",
                                  json={"npc_id": npc["id"], "topic": t}, timeout=20)
            assert r.status_code == 200, f"topic {t} failed: {r.text}"
            d = r.json()
            assert isinstance(d["response"], str) and len(d["response"]) > 0
            assert "band" in d and "relationship" in d

    def test_invalid_npc(self, auth_session):
        r = auth_session.post(f"{API}/game/chat",
                              json={"npc_id": "deadbeef", "topic": "selam"}, timeout=20)
        assert r.status_code == 404


# ---------------------------- TRAVEL ----------------------------
class TestTravel:
    def test_travel_changes_location_and_advances(self, auth_session):
        s1 = auth_session.get(f"{API}/game/state").json()
        cur = s1["player"]["location_id"]
        target = next(l for l in s1["world"]["locations"] if l["id"] != cur)
        r = auth_session.post(f"{API}/game/travel",
                              json={"location_id": target["id"]}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        # New contract: {state, enforcement} or {state, blocked, message}
        s2 = body.get("state", body)
        if body.get("blocked"):
            pytest.skip("Travel blocked by wanted_in")
        assert s2["player"]["location_id"] == target["id"]
        assert s2["day"] == s1["day"] + 3


# ---------------------------- TRADE ----------------------------
class TestTrade:
    def test_buy_sell_cycle(self, auth_session):
        s = auth_session.get(f"{API}/game/state").json()
        loc_id = s["player"]["location_id"]
        loc = next(l for l in s["world"]["locations"] if l["id"] == loc_id)
        good = "buğday"
        # Ensure enough money
        if s["player"]["money"] < loc["prices"][good]:
            pytest.skip("not enough money to trade")
        # Buy 1
        r = auth_session.post(f"{API}/game/trade",
                              json={"location_id": loc_id, "good": good, "qty": 1, "action": "al"})
        assert r.status_code == 200, r.text
        after_buy = r.json()
        assert after_buy["player"]["inventory"].get(good, 0) >= 1
        # Sell 1
        r = auth_session.post(f"{API}/game/trade",
                              json={"location_id": loc_id, "good": good, "qty": 1, "action": "sat"})
        assert r.status_code == 200

    def test_buy_insufficient_funds(self, auth_session):
        s = auth_session.get(f"{API}/game/state").json()
        loc_id = s["player"]["location_id"]
        r = auth_session.post(f"{API}/game/trade",
                              json={"location_id": loc_id, "good": "silah", "qty": 99999, "action": "al"})
        assert r.status_code == 400

    def test_sell_insufficient_inventory(self, auth_session):
        s = auth_session.get(f"{API}/game/state").json()
        loc_id = s["player"]["location_id"]
        r = auth_session.post(f"{API}/game/trade",
                              json={"location_id": loc_id, "good": "silah", "qty": 9999, "action": "sat"})
        assert r.status_code == 400


# ---------------------------- WORK / JOB ----------------------------
class TestWorkJob:
    def test_work(self, auth_session):
        s1 = auth_session.get(f"{API}/game/state").json()
        r = auth_session.post(f"{API}/game/work", timeout=30)
        assert r.status_code == 200
        body = r.json()
        # New contract: {state, enforcement, income}
        s2 = body.get("state", body)
        assert s2["day"] == s1["day"] + 7
        assert s2["player"]["money"] >= s1["player"]["money"] or "enforcement" in body

    def test_change_job(self, auth_session):
        r = auth_session.post(f"{API}/game/job", json={"profession": "tüccar"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["player"]["profession"] == "tüccar"

    def test_change_job_invalid(self, auth_session):
        r = auth_session.post(f"{API}/game/job", json={"profession": "wizard"}, timeout=20)
        assert r.status_code == 400

    def test_change_job_lord_forbidden(self, auth_session):
        r = auth_session.post(f"{API}/game/job", json={"profession": "lord"}, timeout=20)
        assert r.status_code == 403


# ---------------------------- CRIME ----------------------------
class TestCrime:
    def test_crime_valid_type(self, auth_session):
        r = auth_session.post(f"{API}/game/crime",
                              json={"crime_type": "hırsızlık"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "outcome" in d and "state" in d
        assert "success" in d["outcome"]

    def test_crime_invalid(self, auth_session):
        r = auth_session.post(f"{API}/game/crime",
                              json={"crime_type": "ufo"}, timeout=20)
        assert r.status_code == 400


# ---------------------------- BATTLE ----------------------------
class TestBattle:
    def test_battle(self, auth_session):
        r = auth_session.post(f"{API}/game/battle", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["log"], list) and d["log"]
        assert d["outcome"] in ("zafer", "kayıp")


# ---------------------------- QUESTS ----------------------------
class TestQuests:
    def _ensure_quest(self, auth_session):
        # Advance several times to populate quest pool
        s = auth_session.get(f"{API}/game/state").json()
        tries = 0
        while not s.get("quests") and tries < 8:
            auth_session.post(f"{API}/game/advance?days=7", timeout=30)
            s = auth_session.get(f"{API}/game/state").json()
            tries += 1
        return s

    def test_accept_complete_quest(self, auth_session):
        s = self._ensure_quest(auth_session)
        open_quests = [q for q in s.get("quests", []) if q["status"] == "açık"]
        if not open_quests:
            pytest.skip("No quests generated within 8 advances (random)")
        q = open_quests[0]
        r = auth_session.post(f"{API}/game/quest/accept", json={"quest_id": q["id"]})
        assert r.status_code == 200
        s2 = r.json()
        q2 = next(x for x in s2["quests"] if x["id"] == q["id"])
        assert q2["status"] == "kabul_edildi"
        r = auth_session.post(f"{API}/game/quest/complete", json={"quest_id": q["id"]}, timeout=30)
        assert r.status_code == 200
        q3 = next(x for x in r.json()["quests"] if x["id"] == q["id"])
        assert q3["status"] in ("tamamlandı", "başarısız")

    def test_complete_unknown_quest(self, auth_session):
        r = auth_session.post(f"{API}/game/quest/complete", json={"quest_id": "nope"})
        assert r.status_code == 404


# ---------------------------- MARRY ----------------------------
class TestMarry:
    def test_marry_low_relationship_rejected(self, auth_session):
        s = auth_session.get(f"{API}/game/state").json()
        npc = next((n for n in s["world"]["npcs"]
                    if n["alive"] and n["age"] >= 18 and not n["spouse_id"]), None)
        if not npc:
            pytest.skip("No eligible NPC")
        r = auth_session.post(f"{API}/game/marry", json={"npc_id": npc["id"]})
        # Relationship is 0 — expect 400 with "60+" message
        assert r.status_code == 400
        assert "60" in r.json()["detail"]


# ---------------------------- DIALOG TOPICS ----------------------------
class TestDialogTopics:
    def test_dialog_topics(self, auth_session):
        r = auth_session.get(f"{API}/game/dialog-topics", timeout=20)
        assert r.status_code == 200
        topics = r.json()
        ids = {t["id"] for t in topics}
        assert {"selam", "iş", "aile", "dünya", "üzgün", "hedef", "veda"} <= ids


# ---------------------------- CLEANUP ----------------------------
def test_zz_cleanup_delete_state(auth_session):
    r = auth_session.delete(f"{API}/game/state", timeout=20)
    assert r.status_code == 200
