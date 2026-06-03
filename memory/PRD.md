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
- ✅ JWT auth (register/login/me) with bcrypt
- ✅ Procedural world (kingdoms with kings/heirs, cities/villages/castles with population/wealth/security/prosperity/prices, ~100 NPCs with personality, family bonds, goals, mood)
- ✅ One game state per user, auto-save on every action
- ✅ Time advance (1 day / 1 week) — NPCs age, marry, have children, die; kings die and heirs ascend; new heirs picked
- ✅ Living economy — 7 goods with per-location prices that drift with wealth/security and respond to trades
- ✅ Random world events (haydut baskını, kıtlık, savaş ilanı, barış, isyan, şenlik) with chronicle entries
- ✅ Player actions: travel, work, change job, buy/sell, commit crime (4 types with caught/success outcomes), text-based battle with combat log, accept/complete dynamic quests
- ✅ NPC chat with 7 topics, personality-aware responses, relationship band (dost/arkadaş/nötr/rakip/düşman)
- ✅ Marriage with NPCs (≥60 relationship gate)
- ✅ Family tree, history chronicle, market comparison table
- ✅ Responsive UI (desktop sidebar + mobile bottom tab bar), Cinzel/Lora fonts, grain overlay, ember-themed buttons

## Personas
- Solo player who wants a meditative "living world" sandbox: log in, advance a few weeks, watch the world breathe, occasionally intervene as a farmer/merchant/soldier.

## Backlog (P0 → P2)
- **P1**: lord/castle takeover loop (currently `/api/game/job` blocks "lord"), pregnancy + child-of-player succession (player aging → death → continue as child), siege/army battles between kingdoms with player as commander.
- **P2**: more granular relationships among NPCs themselves (gossip, alliances), per-NPC schedule/movement, religion conflicts, more procedurally generated quest types (assassination, escort, lord intrigue), shareable world snapshots, sound atmosphere.
- **P2**: replace `@app.on_event` with FastAPI lifespan, tighten CORS for production, return diffs instead of full state to save bandwidth.

## Next action items
1. Iterate on player feedback re: pacing (how fast world should move).
2. Wire lord/castle takeover and player succession to make the "endless world" promise hit harder.
3. Add a Family/Children dedicated screen once succession lands.
