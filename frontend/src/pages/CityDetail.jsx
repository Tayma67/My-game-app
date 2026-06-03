import { useParams, useNavigate, Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft, Crown, Users, Coins, ShieldCheck, TrendingUp } from "lucide-react";

export default function CityDetail() {
  const { id } = useParams();
  const { state, setState } = useGame();
  const navigate = useNavigate();
  const loc = useMemo(
    () => state?.world.locations.find((l) => l.id === id),
    [state, id]
  );
  const [busy, setBusy] = useState(false);
  const [tradeGood, setTradeGood] = useState("buğday");
  const [qty, setQty] = useState(1);

  if (!loc) {
    return (
      <div className="text-stone-400">
        Konum bulunamadı. <Link to="/oyun" className="text-orange-500">Geri dön</Link>
      </div>
    );
  }

  const kingdom = state.world.kingdoms.find((k) => k.id === loc.kingdom_id);
  const notableNpcs = state.world.npcs
    .filter((n) => n.location_id === loc.id && n.alive)
    .sort((a, b) => b.wealth - a.wealth)
    .slice(0, 8);

  const isHere = state.player.location_id === loc.id;

  const travel = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/travel", { location_id: loc.id });
      setState(data);
      toast.success(`${loc.name}'e ulaştın.`);
    } catch (e) {
      toast.error("Yolculuk başarısız.");
    } finally {
      setBusy(false);
    }
  };

  const trade = async (action) => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/trade", {
        location_id: loc.id,
        good: tradeGood,
        qty: Number(qty),
        action,
      });
      setState(data);
      toast.success(action === "al" ? "Satın aldın." : "Sattın.");
    } catch (e) {
      toast.error(e.response?.data?.detail || "İşlem başarısız");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 rise-in">
      <button onClick={() => navigate("/oyun")} className="text-stone-400 hover:text-stone-200 flex items-center gap-2 text-sm" data-testid="city-back">
        <ArrowLeft className="w-4 h-4" /> Dünya Haritasına Dön
      </button>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label-tiny">{loc.kind} · {kingdom?.name}</div>
          <h1 className="font-heading text-3xl text-stone-100">{loc.name}</h1>
        </div>
        {isHere ? (
          <span className="px-3 py-1.5 border border-emerald-800 bg-emerald-950/30 text-emerald-400 text-xs rounded-sm font-heading tracking-wider">
            BURADASIN
          </span>
        ) : (
          <button onClick={travel} disabled={busy} data-testid="city-travel" className="btn-ember px-4 py-2 text-xs font-heading tracking-widest disabled:opacity-50">
            BURAYA YOLCULUK ET (3 GÜN)
          </button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard icon={Users} label="Nüfus" value={loc.population.toLocaleString()} />
        <StatCard icon={Coins} label="Refah" value={loc.wealth} suffix="%" />
        <StatCard icon={ShieldCheck} label="Güvenlik" value={loc.security} suffix="%" />
        <StatCard icon={TrendingUp} label="Bolluk" value={loc.prosperity} suffix="%" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card-frame p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-lg text-stone-100">Pazar Fiyatları</h2>
            <span className="label-tiny">Altın / Birim</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-stone-800 text-stone-500 text-xs">
                <th className="text-left py-2 font-normal label-tiny">Ürün</th>
                <th className="text-right py-2 font-normal label-tiny">Fiyat</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(loc.prices).map(([g, p]) => (
                <tr key={g} className="border-b border-stone-900">
                  <td className="py-2 text-stone-200 capitalize">{g}</td>
                  <td className="py-2 text-right text-amber-400">{p}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {isHere && (
            <div className="mt-5 pt-5 border-t border-stone-800 space-y-3">
              <div className="label-tiny">Pazarda Al / Sat</div>
              <div className="flex flex-wrap gap-2 items-end">
                <select
                  value={tradeGood}
                  onChange={(e) => setTradeGood(e.target.value)}
                  data-testid="trade-good"
                  className="bg-stone-950 border border-stone-800 px-3 py-2 text-sm rounded-sm"
                >
                  {Object.keys(loc.prices).map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
                <input
                  type="number"
                  min={1}
                  value={qty}
                  onChange={(e) => setQty(e.target.value)}
                  data-testid="trade-qty"
                  className="bg-stone-950 border border-stone-800 px-3 py-2 text-sm w-24 rounded-sm"
                />
                <button onClick={() => trade("al")} disabled={busy} data-testid="trade-buy" className="btn-ember px-4 py-2 text-xs font-heading tracking-widest">SATIN AL</button>
                <button onClick={() => trade("sat")} disabled={busy} data-testid="trade-sell" className="btn-ghost-ash px-4 py-2 text-xs font-heading tracking-widest">SAT</button>
              </div>
            </div>
          )}
        </div>

        <div className="card-frame p-5">
          <h2 className="font-heading text-lg text-stone-100 mb-4">Önemli Sakinler</h2>
          <ul className="space-y-2">
            {notableNpcs.map((n) => (
              <li key={n.id} className="flex items-center justify-between text-sm py-1.5 border-b border-stone-900 last:border-0">
                <Link to={`/oyun/npc/${n.id}`} className="flex items-center gap-2 text-stone-200 hover:text-orange-400" data-testid={`city-npc-${n.id}`}>
                  {n.profession === "kral" && <Crown className="w-3.5 h-3.5 text-amber-500" />}
                  <span>{n.name}</span>
                </Link>
                <span className="text-xs text-stone-500">{n.profession} · {n.wealth}a</span>
              </li>
            ))}
            {notableNpcs.length === 0 && <li className="text-stone-500 text-sm">Bu konumda hayat eseri görünmüyor.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, suffix = "" }) {
  return (
    <div className="card-frame p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="label-tiny">{label}</span>
        <Icon className="w-4 h-4 text-orange-700" />
      </div>
      <div className="font-heading text-2xl text-stone-100">{value}{suffix}</div>
    </div>
  );
}
