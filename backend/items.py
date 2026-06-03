"""Item catalog with effects. Items are USABLE and applied to player state.

Each item entry:
- name (TR)
- type: food | drink | consumable | weapon | armor_head | armor_body | armor_hands | armor_legs | material
- slot: equipment slot key (for armor/weapon), else None
- effects: dict of stat deltas applied on use (consumables) or while equipped
- weight: int
- base_value: int (suggested market price)
"""

ITEMS = {
    "ekmek": {
        "name": "Ekmek", "type": "food", "slot": None,
        "effects": {"hunger": 25, "health": 3},
        "weight": 1, "base_value": 6,
    },
    "buğday": {
        "name": "Buğday", "type": "material", "slot": None,
        "effects": {"hunger": 8},
        "weight": 1, "base_value": 4,
    },
    "et": {
        "name": "Et", "type": "food", "slot": None,
        "effects": {"hunger": 45, "health": 5, "stamina_temp": 1},
        "weight": 2, "base_value": 12,
    },
    "şifa_iksiri": {
        "name": "Şifa İksiri", "type": "consumable", "slot": None,
        "effects": {"health": 40},
        "weight": 1, "base_value": 80,
    },
    "şarap": {
        "name": "Bal Şarabı", "type": "drink", "slot": None,
        "effects": {"hunger": 10, "stamina_temp": 2, "charisma_temp": 1, "health": -2},
        "weight": 1, "base_value": 15,
    },
    "demir": {
        "name": "Demir", "type": "material", "slot": None,
        "effects": {},
        "weight": 3, "base_value": 25,
    },
    "odun": {
        "name": "Odun", "type": "material", "slot": None,
        "effects": {},
        "weight": 2, "base_value": 5,
    },
    "kumaş": {
        "name": "Kumaş", "type": "material", "slot": None,
        "effects": {},
        "weight": 1, "base_value": 10,
    },
    "silah": {
        "name": "Demir Kılıç", "type": "weapon", "slot": "weapon",
        "effects": {"attack": 6},
        "weight": 4, "base_value": 60,
    },
    "tahta_sopa": {
        "name": "Tahta Sopa", "type": "weapon", "slot": "weapon",
        "effects": {"attack": 2},
        "weight": 2, "base_value": 8,
    },
    "av_yayı": {
        "name": "Av Yayı", "type": "weapon", "slot": "weapon",
        "effects": {"attack": 4, "stamina_passive": 1},
        "weight": 2, "base_value": 35,
    },
    "deri_zırh": {
        "name": "Deri Zırh", "type": "armor_body", "slot": "body",
        "effects": {"defense": 3},
        "weight": 4, "base_value": 40,
    },
    "demir_zırh": {
        "name": "Demir Zırh", "type": "armor_body", "slot": "body",
        "effects": {"defense": 7, "stamina_passive": -1},
        "weight": 8, "base_value": 150,
    },
    "miğfer": {
        "name": "Miğfer", "type": "armor_head", "slot": "head",
        "effects": {"defense": 2},
        "weight": 2, "base_value": 30,
    },
    "köylü_giysisi": {
        "name": "Köylü Giysisi", "type": "armor_body", "slot": "body",
        "effects": {"defense": 1},
        "weight": 1, "base_value": 5,
    },
}


# Slots a player can equip
EQUIPMENT_SLOTS = ["weapon", "head", "body", "hands", "legs", "feet"]


def get_item(key):
    return ITEMS.get(key)


def item_exists(key):
    return key in ITEMS


def apply_use_effects(player, item_key, qty=1):
    """Apply a consumable item's effects to player. Returns dict of applied changes."""
    item = ITEMS.get(item_key)
    if not item:
        return None
    if item["type"] not in ("food", "drink", "consumable"):
        return None
    applied = {}
    for stat, delta in item["effects"].items():
        change = delta * qty
        if stat == "health":
            new_v = max(0, min(100, player.get("health", 100) + change))
            applied["health"] = new_v - player.get("health", 100)
            player["health"] = new_v
        elif stat == "hunger":
            new_v = max(0, min(100, player.get("hunger", 100) + change))
            applied["hunger"] = new_v - player.get("hunger", 100)
            player["hunger"] = new_v
        elif stat.endswith("_temp"):
            stat_name = stat.replace("_temp", "")
            buffs = player.setdefault("buffs", {})
            buffs[stat_name] = buffs.get(stat_name, 0) + change
            applied[stat] = change
    return applied


def equipment_bonuses(player):
    """Compute current bonuses from equipped items: attack, defense, stat passives."""
    bonuses = {"attack": 0, "defense": 0,
               "strength_passive": 0, "intelligence_passive": 0,
               "charisma_passive": 0, "stamina_passive": 0}
    equipment = player.get("equipment") or {}
    for slot, item_key in equipment.items():
        if not item_key:
            continue
        item = ITEMS.get(item_key)
        if not item:
            continue
        for stat, delta in item["effects"].items():
            if stat in bonuses:
                bonuses[stat] += delta
    return bonuses
