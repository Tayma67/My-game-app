# Kronikler: Küllerin Mirası — PRD

## Original problem statement (latest, FULL V3 REBUILD)
A Turkish, mobile-friendly persistent-world RPG. Player starts as a 7-year-old
child. The world simulates time, hunger, NPC memory, stats, skills, items, and
family-driven progression. After age 13 the world fully opens (combat, crime,
jobs, marriage, free travel). Until then, the player is guided by their family
through scripted quests; everything done as a child still trains permanent
stats and skills.

User preferences (verbatim):
- 1 tur = 1 hafta (week). Seasons present in the calendar.
- Children 7–12 progress ONLY through family quests; serbest oyun 13+ açılır.
- Aile questlerin yanı sıra çocukken yapılan her şey statları/yetenekleri kalıcı şekilde etkiler.
- Hunger -5/week; 0'a ulaşınca yavaş can kaybı.
- Eski oyunlar silinsin; herkes yeni 7-yaş ile başlasın.

## Architecture
- Frontend: React + TailwindCSS + Shadcn UI (Turkish).
- Backend: FastAPI + MongoDB.
- Auth: Emergent custom JWT (test@k.com / test123).
- Schema version: v3 (legacy states auto-purged at startup).

### Calendar
- 1 turn = 1 week. 4 weeks = 1 month. 12 months = 1 year (48 weeks).
- Seasons: İlkbahar (Mar-May), Yaz (Jun-Aug), Sonbahar (Sep-Nov), Kış (Dec, Jan, Feb).
- Season multipliers: production (Spring 1.15, Summer 1.25, Autumn 1.10, Winter 0.55),
  hunger (Winter 1.3, Spring 0.9, others 1.0).
- Player ages +1 every 48 weeks.

### Stats / Skills / Equipment
- Stats (1-10): strength, intelligence, charisma, stamina. XP next level = 25 + level*15.
- Skill trees (0-10): combat, trade, crafting, social. XP next level = 10 + level*5.
- Skill perks per level (SKILL_PERKS in skills.py). Equipment slots:
  weapon, head, body, hands, legs, feet.

### Family
- generate_player creates a child in a village and spawns:
  - Mother (çiftçi / köylü / fırıncı)
  - Father (demirci / çiftçi / avcı / marangoz)
- Family quests:
  - ev_isleri (anne, age 7+): topla 3 odun → STR/STA xp, social xp
  - ekmek_pisir (anne, age 7+): topla 3 ekmek → CHA/INT xp, trade xp
  - baba_isi (baba, age 8+): bir hafta 2x çalış → STR/STA xp, crafting xp
  - kardes_oyun (anne, age 7+): 3 sohbet et → CHA xp, social xp
  - ilk_silah (baba, age 9+): kuşan tahta_sopa → STR xp, combat xp
  - kasaba_gezi (anne, age 10+): 2 seyahat → INT/CHA xp, trade+social xp

### Dialogue — 4-stage emotional escalation
Per (NPC, topic) repeat count:
1. **merak** — normal/positive response, +1 relationship
2. **kafa_karışıklığı** — "Hmm... bunu az önce sormuş gibisin", -1
3. **sinirlilik** — "Yine mi aynı soru?", -2
4. **düşmanlık** — "Sabrımı sınama!" / "Yeter artık! Çek git!", -4

Adult NPCs treat child players uniquely (king/lord refuse audience, soldiers warn, parents say "Yavrum/Çocuğum").

### Child gating (age < 13)
- /attack_npc, /crime, /marry, /quest/accept, /quest/complete → 403
- /job: only "işsiz" + "köylü" allowed (still stat-gated by check_job_eligible)
- /travel: kale (castles) blocked

## API surface (V3)
- POST /api/game/new
- GET  /api/game/state                  (409 → migration required)
- DELETE /api/game/state
- POST /api/game/advance?weeks=N        (default 1)
- POST /api/game/chat                   {npc_id, topic}
- GET  /api/game/dialog-topics
- POST /api/game/travel                 {location_id}
- POST /api/game/trade                  {location_id, good, qty, action}
- GET  /api/game/jobs
- POST /api/game/job                    {profession}
- POST /api/game/work
- POST /api/game/crime                  age >= 13
- POST /api/game/attack_npc             age >= 13
- POST /api/game/use_item               {item, qty}
- POST /api/game/equip                  {item}
- POST /api/game/unequip                {slot}
- GET  /api/game/items
- GET  /api/game/skills
- GET  /api/game/family-quests
- POST /api/game/quest/accept|complete  age >= 13
- POST /api/game/battle                 age >= 13
- POST /api/game/marry                  age >= 13

## Frontend layout
- /giris, /kayit, /yeni-oyun
- /oyun  → GameLayout shell with sidebar HUD (calendar, season, age, hunger, health, money)
  - / (WorldMap)
  - karakter (CharacterSheet — stats, skills, perks, family, jobs)
  - envanter (Inventory — equipment slot grid, item use/equip)
  - aile (FamilyQuests — guided child quests)
  - npcler, npc/:id, iliskiler, gorevler, savas, tarih

## Implementation status (Feb 2026)
✅ V3 schema migration (auto-purge old states on backend startup)
✅ Calendar with 4 seasons and weekly turn
✅ Player starts age 7 with weak stats and 2 parent NPCs
✅ Family quest system (6 quests, age-gated)
✅ Hunger / health weekly tick with season modifiers
✅ 4-stage NPC emotional escalation
✅ Stat-gated jobs (skills.py JOB_REQUIREMENTS) with skill perks
✅ Item system (food/weapon/armor/consumable) with use & equip
✅ Equipment slots (6) with attack/defense/charisma bonuses
✅ All child gating (combat, crime, marry, quests, etc.)
✅ Frontend HUD with season/age/hunger
✅ CharacterSheet, Inventory, FamilyQuests pages

## Backlog / Next (P1+)
- More family quests beyond the 6 starter (age 11-12 transition arc)
- "Yetişkin oluyorsun" cinematic at age 13
- Multi-generation: player dies → continue as their child
- Skill perks UI tree (interactive nodes)
- NPC↔NPC dynamic relationships outside marriage
- Lord/kale takeover (player becoming a lord at age 18+)
- Trade caravan NPC routes (moving goods between cities)
- Inheritance: child quests' rewards stack into adulthood with visible bonuses
