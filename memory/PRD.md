# Kronikler: Küllerin Mirası — PRD

## Original problem statement
Mobile-first text-based RPG / life-sim. Player is an ordinary person in a procedurally generated medieval Turkish-flavored world. World simulates kingdoms, cities, villages, castles, and NPCs that age, marry, have children, die, and engage in politics & economy autonomously — even when the player does nothing. JSON-based data, auto-save, single-click play, modular code, mobile-friendly responsive UI.

## User choices (Feb 2026)
- NPC dialogue: template-based dynamic (no LLM)
- Storage: MongoDB backend + JWT user accounts
- Visual style: dark ashen medieval (Cinzel + Lora fonts, stone/ember palette, grain overlay)
- Language: Turkish only
- World scale: 3 kingdoms, 3 cities, 10 villages, 5 castles, ~100 NPCs

## Architecture
- **Backend (FastAPI + MongoDB)**: `server.py` mounts `auth_routes.py` (register/login/me, bcrypt + PyJWT, Bearer tokens) and `game_routes.py`. `world_gen.py` does procedural generation; `simulation.py` runs the tick (aging, marriages, births, deaths, economy drift, random events, quest gen); `dialogue.py` produces template NPC responses based on personality + relationship band + recent events.
- **Frontend (React + Tailwind + Shadcn)**: `App.js` routing; `AuthContext` (localStorage `kkm_token`); `GameContext` (state + actions). Pages: Login, Register, NewGame, GameLayout (responsive sidebar + mobile bottom nav), WorldMap, CityDetail, CharacterSheet, Inventory, NPCList, NPCDetail, Relationships, Chronicle, Quests, Battle.

## What's implemented (Feb 2026)
### Iteration 1 (MVP)
- ✅ JWT auth, procedural world (3 kingdoms, 3 cities, 10 villages, 5 castles, ~100 NPCs)
- ✅ NPC families, marriage/birth/death/royal succession, time advance, history chronicle
- ✅ Living economy drift, dynamic quests, text battle, crime, NPC chat (template), responsive UI

### Iteration 2 (Real game logic upgrade)
- ✅ **NPC memory**: per-NPC `interactions` counter per topic + `memory[]` log of last 20 chats. Repeated questions trigger irritation lines ("Yine mi aynı soru?", "Sabrımı sınama") and start hurting relationship at 3+ repeats.
- ✅ **Varied dialogue**: response is deterministically seeded by (npc_id, topic, day, turn) so repeats produce different lines from multi-phrase pools.
- ✅ **Faction roles**: kings/lords refuse audience to low-status low-reputation players (`KING_REJECT`/`LORD_FORMAL`). Soldiers threaten players with crime ≥ 30. Merchants reference local supply state (scarce/abundant/normal).
- ✅ **Real economy**: each location has `market[good] = {price, supply, demand, base}`. Production from NPC professions (çiftçi→buğday, demirci→demir, …) adds supply each tick; population consumption depletes it. Price formula `base * (demand/supply)^0.45 * wealth_factor`. Player trades directly move supply/demand. NPC merchants do arbitrage between cheap/expensive locations.
- ✅ **Combat against specific NPCs**: `/api/game/attack_npc` kills target permanently (alive=False persists), scales by social status, large crime/reputation hit. Killing nobility adds player to `wanted_in` for that kingdom.
- ✅ **Soldier enforcement**: `soldier_check` runs after work/travel/crime/attack and fines or imprisons the player based on crime + city security + soldier presence.
- ✅ **UI surfacing**: NPC Detail shows SALDIR button + memory log "Hatırladıkları"; City Detail shows Arz/Talep/Fiyat with scarcity coloring.

## Backlog (P0 → P2)
- **P1**: lord/castle takeover loop (own a kale + collect taxes); player aging → death → continue as child.
- **P1**: kingdom-level army battles (siege/raid) where player can command troops; turn `at_war_with` flags into actual battles that decide territory.
- **P2**: NPC↔NPC relationships (gossip, alliances, vendettas), per-NPC schedule/movement, religion conflicts.
- **P2**: Persistent quest chains, assassination contracts, escort missions tied to NPC personal events.
- **P2**: Unify all endpoint return shapes to `{state, ...}` for consistency (currently mixed).
- **P3**: Shareable Chronicle card export (social shareability hook).
