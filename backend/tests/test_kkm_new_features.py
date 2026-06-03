"""Tests for new game-logic features (iteration 2):
- NPC memory + repeat-irritation
- Role-based dialogue (king reject, soldier threat, merchant scarcity)
- Real economy supply/demand on trade
- Economy passive simulation
- Attack NPC with persistent death + bounty
- Soldier enforcement check on work/travel
"""
import os
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ----- fixtures -----
@pytest.fixture(scope="module")
def auth_session():
    suffix = uuid.uuid4().hex[:8]
    user = {"email": f"feat_{suffix}@k.com", "password": "test123", "name": f"Feat_{suffix}"}
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register", json=user, timeout=30)
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def fresh_game(auth_session):
    auth_session.delete(f"{API}/game/state", timeout=30)
    r = auth_session.post(f"{API}/game/new", timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def _state(auth_session):
    r = auth_session.get(f"{API}/game/state", timeout=30)
    assert r.status_code == 200
    return r.json()


# ----- NPC memory + interactions counter -----
class TestNPCMemoryAndRepeat:
    def test_chat_increments_interactions_and_varies(self, auth_session, fresh_game):
        state = fresh_game
        # Pick any commoner NPC at player location
        ploc = state["player"]["location_id"]
        npcs = [n for n in state["world"]["npcs"] if n["alive"] and n["location_id"] == ploc
                and n["profession"] not in ("kral", "lord", "veliaht")]
        if not npcs:
            npcs = [n for n in state["world"]["npcs"] if n["alive"]
                    and n["profession"] not in ("kral", "lord", "veliaht")]
        assert npcs, "Need at least one non-noble NPC"
        npc = npcs[0]

        responses = []
        for i in range(4):
            r = auth_session.post(f"{API}/game/chat",
                                  json={"npc_id": npc["id"], "topic": "selam"}, timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            responses.append(data["response"])
            assert data["repeat_count"] == i + 1, f"repeat_count should be {i+1}, got {data['repeat_count']}"

        # At least 2 different responses across 4 turns
        assert len(set(responses)) >= 2, f"Expected varied responses but got: {responses}"

        # NPC interactions counter persisted
        s2 = _state(auth_session)
        n2 = next(n for n in s2["world"]["npcs"] if n["id"] == npc["id"])
        assert n2["interactions"].get("selam", 0) >= 4
        assert len(n2["memory"]) >= 4

    def test_repeat_irritation_text(self, auth_session, fresh_game):
        state = _state(auth_session)
        ploc = state["player"]["location_id"]
        npcs = [n for n in state["world"]["npcs"] if n["alive"] and n["location_id"] == ploc
                and n["profession"] not in ("kral", "lord", "veliaht", "tüccar", "asker")]
        if not npcs:
            npcs = [n for n in state["world"]["npcs"] if n["alive"]
                    and n["profession"] not in ("kral", "lord", "veliaht", "tüccar", "asker")]
        npc = npcs[0]

        irritation_keywords = ["Yine mi", "Sabrımı", "az önce sormadın", "Yeter artık", "aynı soru"]
        found = False
        responses = []
        for _ in range(5):
            r = auth_session.post(f"{API}/game/chat",
                                  json={"npc_id": npc["id"], "topic": "hedef"}, timeout=30)
            assert r.status_code == 200
            text = r.json()["response"]
            responses.append(text)
            if any(k in text for k in irritation_keywords):
                found = True
        assert found, f"Expected irritation phrase in repeated chats, got: {responses}"


# ----- Faction / role rules -----
class TestFactionRoles:
    def test_king_refuses_low_status_player(self, auth_session, fresh_game):
        state = _state(auth_session)
        king = next((n for n in state["world"]["npcs"]
                     if n["alive"] and n["profession"] == "kral"), None)
        assert king, "King must exist"
        # Teleport-equivalent: move player to king's location via travel
        # (king location may differ; just call chat anyway since chat doesn't need same loc)
        r = auth_session.post(f"{API}/game/chat",
                              json={"npc_id": king["id"], "topic": "selam"}, timeout=30)
        assert r.status_code == 200, r.text
        resp = r.json()["response"]
        rejection_keywords = [
            "İtibarın yetersiz", "Sen kim oluyorsun",
            "Sana kelam edecek değilim", "Bir köylüyle laflanmaz",
        ]
        assert any(k in resp for k in rejection_keywords), \
            f"King should reject low-status player. Got: {resp}"

    def test_soldier_threat_when_player_has_crime(self, auth_session, fresh_game):
        # Boost crime by committing several crimes
        state = _state(auth_session)
        # Repeated crimes until crime >= 35
        for _ in range(8):
            r = auth_session.post(f"{API}/game/crime",
                                  json={"crime_type": "hırsızlık"}, timeout=30)
            if r.status_code == 200:
                s = r.json()["state"]
                if s["player"].get("crime", 0) >= 35:
                    break

        state = _state(auth_session)
        assert state["player"].get("crime", 0) >= 30, \
            f"Need crime>=30 to test soldier; got {state['player'].get('crime')}"

        # Find any soldier NPC (location doesn't matter for chat)
        soldier = next((n for n in state["world"]["npcs"]
                        if n["alive"] and n["profession"] == "asker"), None)
        assert soldier, "Need a soldier NPC"

        threat_keywords = ["demir vururum", "kayıpta görünme", "kelle uçar", "izliyorum"]
        found = False
        responses = []
        for _ in range(3):
            r = auth_session.post(f"{API}/game/chat",
                                  json={"npc_id": soldier["id"], "topic": "iş"}, timeout=30)
            assert r.status_code == 200
            text = r.json()["response"]
            responses.append(text)
            if any(k in text for k in threat_keywords):
                found = True
                break
        assert found, f"Expected soldier threat. crime={state['player'].get('crime')}, got: {responses}"


# ----- Economy: real supply/demand -----
class TestEconomySupplyDemand:
    def test_state_has_market_per_location(self, auth_session, fresh_game):
        state = _state(auth_session)
        loc = state["world"]["locations"][0]
        assert "market" in loc and loc["market"]
        any_good = next(iter(loc["market"]))
        m = loc["market"][any_good]
        for k in ("price", "supply", "demand", "base"):
            assert k in m, f"market[{any_good}] missing {k}"

    def test_buying_decreases_supply_increases_price(self, auth_session, fresh_game):
        state = _state(auth_session)
        # Find player's location and choose a good with enough supply and affordable price
        ploc_id = state["player"]["location_id"]
        loc = next(l for l in state["world"]["locations"] if l["id"] == ploc_id)
        # Make sure we have money
        money = state["player"]["money"]
        good = None
        for g, m in loc["market"].items():
            if m["supply"] >= 3 and m["price"] * 3 <= money:
                good = g
                break
        if not good:
            pytest.skip("No affordable good with sufficient supply at player location")

        s0 = loc["market"][good]["supply"]
        p0 = loc["market"][good]["price"]
        r = auth_session.post(f"{API}/game/trade",
                              json={"location_id": ploc_id, "good": good, "qty": 3, "action": "al"},
                              timeout=30)
        assert r.status_code == 200, r.text
        s = r.json()
        loc2 = next(l for l in s["world"]["locations"] if l["id"] == ploc_id)
        s1 = loc2["market"][good]["supply"]
        p1 = loc2["market"][good]["price"]
        assert s1 == s0 - 3, f"supply expected {s0-3}, got {s1}"
        assert p1 >= p0, f"price should rise/equal; before={p0}, after={p1}"

    def test_selling_increases_supply_decreases_price(self, auth_session, fresh_game):
        state = _state(auth_session)
        ploc_id = state["player"]["location_id"]
        inv = state["player"].get("inventory", {})
        # Try to sell something we own
        good = None
        for g, q in inv.items():
            if q >= 2:
                good = g
                break
        if not good:
            # Buy something first
            loc = next(l for l in state["world"]["locations"] if l["id"] == ploc_id)
            for g, m in loc["market"].items():
                if m["supply"] >= 4 and m["price"] * 2 <= state["player"]["money"]:
                    auth_session.post(f"{API}/game/trade",
                                      json={"location_id": ploc_id, "good": g, "qty": 2, "action": "al"},
                                      timeout=30)
                    good = g
                    break
        if not good:
            pytest.skip("Couldn't acquire any inventory item to sell")

        s_before = _state(auth_session)
        loc_b = next(l for l in s_before["world"]["locations"] if l["id"] == ploc_id)
        s0 = loc_b["market"][good]["supply"]
        p0 = loc_b["market"][good]["price"]

        r = auth_session.post(f"{API}/game/trade",
                              json={"location_id": ploc_id, "good": good, "qty": 2, "action": "sat"},
                              timeout=30)
        assert r.status_code == 200, r.text
        s_after = r.json()
        loc_a = next(l for l in s_after["world"]["locations"] if l["id"] == ploc_id)
        s1 = loc_a["market"][good]["supply"]
        p1 = loc_a["market"][good]["price"]
        assert s1 == s0 + 2, f"supply expected {s0+2}, got {s1}"
        assert p1 <= p0 + 0.5, f"price should drop/equal; before={p0}, after={p1}"

    def test_advance_simulates_market(self, auth_session, fresh_game):
        s_before = _state(auth_session)
        # Snapshot some prices/supplies
        snap = {}
        for loc in s_before["world"]["locations"][:5]:
            snap[loc["id"]] = {g: (m["supply"], m["price"]) for g, m in loc["market"].items()}

        r = auth_session.post(f"{API}/game/advance?days=28", timeout=30)
        assert r.status_code == 200
        s_after = r.json()
        changed = 0
        for loc in s_after["world"]["locations"][:5]:
            for g, m in loc["market"].items():
                pre = snap.get(loc["id"], {}).get(g)
                if pre and (pre[0] != m["supply"] or pre[1] != m["price"]):
                    changed += 1
        assert changed > 0, "Expected supply/price to change after 28-day advance"


# ----- Attack NPC -----
class TestAttackNPC:
    def test_attack_kills_npc_and_persists(self, auth_session, fresh_game):
        state = _state(auth_session)
        ploc_id = state["player"]["location_id"]
        # Heal player by setting via crime success failure won't help; use any low-status NPC at our location
        targets = [n for n in state["world"]["npcs"] if n["alive"]
                   and n["location_id"] == ploc_id
                   and n["profession"] in ("köylü", "çiftçi", "fırıncı", "balıkçı", "çoban", "avcı")]
        if not targets:
            pytest.skip("No commoner NPC at player location to attack")
        target = targets[0]
        tid = target["id"]

        r = auth_session.post(f"{API}/game/attack_npc", json={"npc_id": tid}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "log" in data and isinstance(data["log"], list) and len(data["log"]) >= 2
        assert data["outcome"] in ("zafer", "kayıp")

        # Whether zafer or kayıp, fetch state. If zafer => NPC must be dead persistently
        s2 = _state(auth_session)
        n2 = next(n for n in s2["world"]["npcs"] if n["id"] == tid)
        if data["outcome"] == "zafer":
            assert n2["alive"] is False, "Killed NPC must persist as dead"
            # Crime should increase and reputation drop
            assert s2["player"]["crime"] > state["player"].get("crime", 0)
        else:
            # On loss, player health was clamped to >=5 by code
            assert s2["player"]["health"] >= 1

    def test_attack_invalid_target(self, auth_session, fresh_game):
        r = auth_session.post(f"{API}/game/attack_npc",
                              json={"npc_id": "does-not-exist"}, timeout=30)
        assert r.status_code == 404


# ----- Soldier enforcement on actions -----
class TestSoldierEnforcement:
    def test_work_returns_enforcement_field(self, auth_session, fresh_game):
        # Make sure crime is high
        state = _state(auth_session)
        # Already pumped earlier; pump more if not high
        tries = 0
        while state["player"].get("crime", 0) < 60 and tries < 10:
            auth_session.post(f"{API}/game/crime", json={"crime_type": "kaçakçılık"}, timeout=30)
            state = _state(auth_session)
            tries += 1

        r = auth_session.post(f"{API}/game/work", timeout=30)
        assert r.status_code == 200
        body = r.json()
        # Response shape must include state + enforcement (may be empty dict if not triggered)
        assert "state" in body
        assert "enforcement" in body
        # enforcement is dict or None — accept either; if present and player crime high it may
        # contain by/fine/days. We don't force-trigger because it's random.
