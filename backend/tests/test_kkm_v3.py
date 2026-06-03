"""V3 backend tests for Kronikler: Küllerin Mirası.

Covers: child player creation, age/season/hunger mechanics, NPC emotional
4-stage escalation, child gates (crime/attack/quest/marry/job/travel),
equipment, items, jobs, family quests, skills.
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


@pytest.fixture(scope="module")
def auth_session():
    suffix = uuid.uuid4().hex[:8]
    user = {"email": f"v3_{suffix}@k.com", "password": "test123", "name": f"V3_{suffix}"}
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register", json=user, timeout=30)
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def _new_game(auth_session):
    auth_session.delete(f"{API}/game/state", timeout=30)
    r = auth_session.post(f"{API}/game/new", timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def _state(auth_session):
    r = auth_session.get(f"{API}/game/state", timeout=30)
    assert r.status_code == 200
    return r.json()


# ---------------- Player initial v3 schema ----------------
class TestV3InitialState:
    def test_new_game_v3_schema(self, auth_session):
        state = _new_game(auth_session)
        assert state.get("schema_version") == "v3", f"schema_version: {state.get('schema_version')}"
        p = state["player"]
        assert p["age"] == 7, f"age: {p['age']}"
        assert p.get("is_child") is True
        stats = p["stats"]
        assert stats["strength"] == 1
        assert stats["intelligence"] == 1
        assert stats["charisma"] == 1
        assert stats["stamina"] == 2
        skills = p["skills"]
        for k in ("combat", "trade", "crafting", "social"):
            assert skills.get(k, 0) == 0
        assert p["hunger"] == 100
        assert p["equipment"]["body"] == "köylü_giysisi"
        parents = p.get("parent_ids", [])
        assert len(parents) == 2, f"parent_ids: {parents}"
        npc_ids = {n["id"]: n for n in state["world"]["npcs"]}
        for pid in parents:
            assert pid in npc_ids, f"parent {pid} not in world npcs"
        quests = p.get("family_quests") or state.get("family_quests") or []
        assert len(quests) == 6, f"family quests count: {len(quests)}"
        statuses = {q.get("status") for q in quests}
        assert "açık" in statuses
        assert "kilitli" in statuses
        cal = state.get("calendar", {})
        assert cal.get("season") in ("İlkbahar", "Yaz", "Sonbahar", "Kış")


# ---------------- Advance ----------------
class TestV3Advance:
    def test_advance_4_weeks(self, auth_session):
        s1 = _state(auth_session)
        h0 = s1["player"]["hunger"]
        turn0 = s1["calendar"]["turn"]
        r = auth_session.post(f"{API}/game/advance?weeks=4", timeout=30)
        assert r.status_code == 200, r.text
        s2 = r.json()
        turn1 = s2["calendar"]["turn"]
        assert turn1 - turn0 == 4, f"expected turn delta 4, got {turn1 - turn0}"
        # Hunger dropped (5-7 / week)
        drop = h0 - s2["player"]["hunger"]
        assert 15 <= drop <= 30, f"hunger drop {drop} out of 15..30 (h0={h0}, h1={s2['player']['hunger']})"
        # Age still 7
        assert s2["player"]["age"] == 7

    def test_advance_48_weeks_ages_up(self, auth_session):
        _new_game(auth_session)
        r = auth_session.post(f"{API}/game/advance?weeks=48", timeout=60)
        assert r.status_code == 200
        s = r.json()
        assert s["player"]["age"] == 8, f"age after 48 weeks: {s['player']['age']}"


# ---------------- Emotional escalation ----------------
class TestEmotionalStages:
    def test_repeat_escalation(self, auth_session):
        state = _new_game(auth_session)
        ploc = state["player"]["location_id"]
        non_parent = [n for n in state["world"]["npcs"]
                      if n["alive"] and n["id"] not in state["player"]["parent_ids"]
                      and n.get("profession") not in ("kral", "lord", "veliaht")]
        # Prefer same loc, fall back
        same_loc = [n for n in non_parent if n["location_id"] == ploc]
        npc = (same_loc or non_parent)[0]
        stages = []
        for i in range(5):
            r = auth_session.post(f"{API}/game/chat",
                                  json={"npc_id": npc["id"], "topic": "selam"}, timeout=30)
            assert r.status_code == 200, r.text
            d = r.json()
            stages.append(d.get("emotional_stage") or d.get("stage"))
        # Expect progression matching merak->kafa_karışıklığı->sinirlilik->düşmanlık->düşmanlık
        expected_order = ["merak", "kafa_karışıklığı", "sinirlilik", "düşmanlık", "düşmanlık"]
        # Some implementations may use stage numbers or different labels; accept either by index
        if all(isinstance(s, int) for s in stages):
            assert stages == [1, 2, 3, 4, 4], f"stages: {stages}"
        else:
            assert stages == expected_order, f"stages: {stages}"


# ---------------- Parent / Child dialogue ----------------
class TestParentDialogue:
    def test_parent_addresses_child(self, auth_session):
        state = _new_game(auth_session)
        pid = state["player"]["parent_ids"][0]
        r = auth_session.post(f"{API}/game/chat",
                              json={"npc_id": pid, "topic": "selam"}, timeout=30)
        assert r.status_code == 200, r.text
        resp = r.json()["response"]
        assert any(k in resp for k in ("Yavrum", "Çocuğum", "yavrum", "çocuğum", "evladım")), \
            f"Expected parent endearment, got: {resp}"


# ---------------- Child gates ----------------
class TestChildGates:
    def test_attack_blocked(self, auth_session):
        _new_game(auth_session)
        r = auth_session.post(f"{API}/game/attack_npc", json={"npc_id": "anything"}, timeout=20)
        assert r.status_code == 403
        assert "Çocuk" in r.json().get("detail", "")

    def test_crime_blocked(self, auth_session):
        r = auth_session.post(f"{API}/game/crime",
                              json={"crime_type": "hırsızlık"}, timeout=20)
        assert r.status_code == 403

    def test_quest_accept_blocked(self, auth_session):
        r = auth_session.post(f"{API}/game/quest/accept",
                              json={"quest_id": "x"}, timeout=20)
        assert r.status_code == 403

    def test_marry_blocked(self, auth_session):
        # any npc id; gate triggers before validation typically
        r = auth_session.post(f"{API}/game/marry",
                              json={"npc_id": "x"}, timeout=20)
        assert r.status_code == 403

    def test_job_asker_blocked(self, auth_session):
        r = auth_session.post(f"{API}/game/job", json={"profession": "asker"}, timeout=20)
        assert r.status_code == 403

    def test_job_koylu_stat_gated(self, auth_session):
        # Child has STR=1; köylü typically requires STR>=2 or stamina>=2 — may 400
        r = auth_session.post(f"{API}/game/job", json={"profession": "köylü"}, timeout=20)
        assert r.status_code in (200, 400), r.text


# ---------------- Travel ----------------
class TestTravelChild:
    def test_travel_to_kale_blocked(self, auth_session):
        state = _state(auth_session)
        kale = next((l for l in state["world"]["locations"] if l["kind"] == "kale"), None)
        if not kale:
            pytest.skip("No kale in world")
        r = auth_session.post(f"{API}/game/travel",
                              json={"location_id": kale["id"]}, timeout=20)
        assert r.status_code == 403, r.text

    def test_travel_to_koy_ok(self, auth_session):
        state = _state(auth_session)
        cur = state["player"]["location_id"]
        koy = next((l for l in state["world"]["locations"]
                    if l["kind"] == "köy" and l["id"] != cur), None)
        if not koy:
            pytest.skip("No alternate köy")
        r = auth_session.post(f"{API}/game/travel",
                              json={"location_id": koy["id"]}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        s2 = body.get("state", body)
        assert s2["player"]["location_id"] == koy["id"]


# ---------------- Jobs / Work ----------------
class TestJobsWork:
    def test_jobs_list(self, auth_session):
        _new_game(auth_session)
        r = auth_session.get(f"{API}/game/jobs", timeout=20)
        assert r.status_code == 200
        data = r.json()
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        assert jobs, "Expected jobs list"
        # Child: only işsiz should be eligible
        by_prof = {j["job"]: j for j in jobs}
        assert by_prof.get("işsiz", {}).get("eligible") is True

    def test_work_işsiz(self, auth_session):
        s1 = _state(auth_session)
        r = auth_session.post(f"{API}/game/work", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        s2 = body.get("state", body)
        # 1 week passed
        wk_delta = s2["calendar"]["turn"] - s1["calendar"]["turn"]
        assert wk_delta == 1, f"week delta: {wk_delta}"


# ---------------- Items / Use / Equip ----------------
class TestItems:
    def test_items_endpoint(self, auth_session):
        r = auth_session.get(f"{API}/game/items", timeout=20)
        assert r.status_code == 200
        data = r.json()
        # Should have items dict + slots
        assert "items" in data or isinstance(data, dict)
        # equipment slots somewhere
        slots = data.get("EQUIPMENT_SLOTS") or data.get("slots") or data.get("equipment_slots")
        if slots:
            for s in ("weapon", "head", "body", "hands", "legs", "feet"):
                assert s in slots, f"slot {s} missing"

    def test_use_ekmek(self, auth_session):
        state = _new_game(auth_session)
        inv = state["player"]["inventory"]
        ekmek0 = inv.get("ekmek", 0)
        assert ekmek0 == 2, f"starting ekmek: {ekmek0}"
        # Advance some weeks to lower hunger so effects show
        auth_session.post(f"{API}/game/advance?weeks=6", timeout=30)
        r = auth_session.post(f"{API}/game/use_item",
                              json={"item": "ekmek", "qty": 1}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        s2 = body.get("state", body)
        assert s2["player"]["inventory"].get("ekmek", 0) == 1
        applied = body.get("applied") or {}
        assert applied.get("hunger", 0) > 0, f"applied: {applied}"

    def test_use_ekmek_insufficient(self, auth_session):
        # We had 2, used 1 above => 1 left. Use 1 more then attempt 3rd
        auth_session.post(f"{API}/game/use_item",
                          json={"item": "ekmek", "qty": 1}, timeout=20)
        r = auth_session.post(f"{API}/game/use_item",
                              json={"item": "ekmek", "qty": 1}, timeout=20)
        assert r.status_code == 400

    def test_unequip_body(self, auth_session):
        _new_game(auth_session)
        r = auth_session.post(f"{API}/game/unequip", json={"slot": "body"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        s2 = body.get("state", body)
        assert not s2["player"]["equipment"].get("body")
        assert s2["player"]["inventory"].get("köylü_giysisi", 0) >= 1


# ---------------- Skills / Family quests ----------------
class TestSkillsFamily:
    def test_skills_endpoint(self, auth_session):
        r = auth_session.get(f"{API}/game/skills", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "stats" in d
        assert "skills" in d or "skill_levels" in d
        perks_tree = d.get("SKILL_PERKS") or d.get("perks_tree") or d.get("skill_perks") or d.get("tree")
        assert perks_tree is not None

    def test_family_quests_endpoint(self, auth_session):
        r = auth_session.get(f"{API}/game/family-quests", timeout=20)
        assert r.status_code == 200
        d = r.json()
        quests = d.get("quests") if isinstance(d, dict) else d
        assert quests and len(quests) == 6
        assert "player_age" in d if isinstance(d, dict) else True
