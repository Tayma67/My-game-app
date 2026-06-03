import { useEffect, useState, useMemo } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Package, Shirt, Hand, Footprints, Crown, Sword, ShieldHalf, Apple, FlaskRound,
} from "lucide-react";

const SLOT_META = [
  { key: "head",   label: "Baş",     icon: Crown },
  { key: "body",   label: "Vücut",   icon: Shirt },
  { key: "weapon", label: "Silah",   icon: Sword },
  { key: "hands",  label: "Eller",   icon: Hand },
  { key: "legs",   label: "Bacaklar",icon: ShieldHalf },
  { key: "feet",   label: "Ayaklar", icon: Footprints },
];

const TYPE_ICON = {
  food: Apple,
  drink: FlaskRound,
  consumable: FlaskRound,
  weapon: Sword,
  armor: Shirt,
};

export default function Inventory() {
  const { state, setState } = useGame();
  const [items, setItems] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/game/items").then(({ data }) => setItems(data.items || {}));
  }, []);

  const inv = state.player.inventory || {};
  const equipment = state.player.equipment || {};
  const bonuses = state.player.equipment_bonuses || { attack: 0, defense: 0, charisma: 0 };

  const invEntries = Object.entries(inv).filter(([, q]) => q > 0);

  const consumeItem = async (key) => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/use_item", { item: key, qty: 1 });
      setState(data.state);
      const a = data.applied || {};
      const parts = [];
      if (a.hunger) parts.push(`+${a.hunger} açlık`);
      if (a.health) parts.push(`+${a.health} sağlık`);
      toast.success(`${data.item_name} kullanıldı${parts.length ? ` (${parts.join(", ")})` : ""}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Kullanılamadı");
    } finally {
      setBusy(false);
    }
  };

  const equipItem = async (key) => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/equip", { item: key });
      setState(data);
      toast.success("Kuşandın");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Kuşanılamadı");
    } finally {
      setBusy(false);
    }
  };

  const unequip = async (slot) => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/unequip", { slot });
      setState(data);
      toast.success("Çıkardın");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Çıkarılamadı");
    } finally {
      setBusy(false);
    }
  };

  const currentLoc = state.world.locations.find((l) => l.id === state.player.location_id);
  const netWorth = useMemo(() => {
    let v = state.player.money;
    if (currentLoc) {
      for (const [g, q] of invEntries) {
        v += (currentLoc.prices?.[g] || 0) * q;
      }
    }
    return Math.round(v);
  }, [invEntries, currentLoc, state.player.money]);

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Envanter</div>
        <h1 className="font-heading text-3xl text-stone-100">Heybe & Donanım</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Equipment silhouette */}
        <div className="card-frame p-5 lg:col-span-1">
          <h2 className="font-heading text-lg text-stone-100 mb-4">Donanım</h2>
          <div className="grid grid-cols-2 gap-2">
            {SLOT_META.map((slot) => {
              const itemKey = equipment[slot.key];
              const item = itemKey ? items[itemKey] : null;
              const Icon = slot.icon;
              return (
                <div
                  key={slot.key}
                  data-testid={`slot-${slot.key}`}
                  className={`border rounded-sm p-3 min-h-[88px] flex flex-col justify-between ${
                    item ? "border-orange-800/60 bg-stone-900/50" : "border-stone-800 bg-stone-950/40"
                  }`}
                >
                  <div className="flex items-center gap-1 label-tiny">
                    <Icon className="w-3 h-3" /> {slot.label}
                  </div>
                  {item ? (
                    <>
                      <div className="text-sm text-stone-100 font-heading mt-1">{item.name}</div>
                      <button
                        onClick={() => unequip(slot.key)}
                        disabled={busy}
                        data-testid={`unequip-${slot.key}`}
                        className="text-[10px] text-stone-500 hover:text-orange-400 self-start mt-1"
                      >
                        çıkar
                      </button>
                    </>
                  ) : (
                    <div className="text-xs text-stone-600 italic mt-2">boş</div>
                  )}
                </div>
              );
            })}
          </div>
          <div className="divider-ash my-4" />
          <div className="text-xs space-y-1">
            <div className="flex justify-between"><span className="text-stone-500">Saldırı</span><span className="text-red-400 font-heading">+{bonuses.attack}</span></div>
            <div className="flex justify-between"><span className="text-stone-500">Savunma</span><span className="text-sky-400 font-heading">+{bonuses.defense}</span></div>
            <div className="flex justify-between"><span className="text-stone-500">Karizma</span><span className="text-pink-400 font-heading">+{bonuses.charisma}</span></div>
          </div>
        </div>

        {/* Items list */}
        <div className="card-frame p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-lg flex items-center gap-2 text-stone-100"><Package className="w-4 h-4" /> Eşyalarım</h2>
            <div className="text-xs text-stone-500">Toplam Değer: <span className="text-amber-400">{netWorth} altın</span></div>
          </div>
          {invEntries.length === 0 ? (
            <div className="text-stone-500 text-sm">Heyben bomboş.</div>
          ) : (
            <ul className="divide-y divide-stone-900">
              {invEntries.map(([key, qty]) => {
                const item = items[key];
                const TypeIcon = item ? (TYPE_ICON[item.type] || Package) : Package;
                const canUse = item && (item.type === "food" || item.type === "drink" || item.type === "consumable");
                const canEquip = item && item.slot;
                return (
                  <li key={key} className="py-2 flex items-center gap-3" data-testid={`inv-row-${key}`}>
                    <TypeIcon className="w-4 h-4 text-stone-500 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-stone-100 capitalize">
                        {item ? item.name : key}
                        <span className="text-stone-500 text-xs ml-2">×{qty}</span>
                      </div>
                      {item?.desc && <div className="text-[11px] text-stone-500 truncate">{item.desc}</div>}
                    </div>
                    <div className="flex gap-1.5">
                      {canUse && (
                        <button
                          onClick={() => consumeItem(key)}
                          disabled={busy}
                          data-testid={`use-${key}`}
                          className="px-2 py-1 text-[10px] border border-emerald-900 text-emerald-400 hover:bg-emerald-900/30 rounded-sm font-heading tracking-wider"
                        >
                          KULLAN
                        </button>
                      )}
                      {canEquip && (
                        <button
                          onClick={() => equipItem(key)}
                          disabled={busy}
                          data-testid={`equip-${key}`}
                          className="px-2 py-1 text-[10px] border border-orange-900 text-orange-400 hover:bg-orange-900/30 rounded-sm font-heading tracking-wider"
                        >
                          KUŞAN
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          <div className="text-xs text-stone-500 mt-3">
            Satmak veya almak için bir şehrin pazarına git: <span className="text-stone-300">{currentLoc?.name}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
