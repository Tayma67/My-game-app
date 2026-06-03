import { Link } from "react-router-dom";
import { useMemo } from "react";
import { useGame } from "@/lib/GameContext";
import { Crown, MapPin, ShieldCheck, Coins, Castle, Tent, Building2 } from "lucide-react";

const KIND_ICON = {
  şehir: Building2,
  köy: Tent,
  kale: Castle,
};

function StatBar({ value, color = "ember", label }) {
  const fill = {
    ember: "stat-bar-fill",
    cool: "stat-bar-fill stat-bar-fill-cool",
    good: "stat-bar-fill stat-bar-fill-good",
    bad: "stat-bar-fill stat-bar-fill-bad",
  }[color];
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="label-tiny">{label}</span>
        <span className="text-xs text-stone-300">{value}</span>
      </div>
      <div className="stat-bar">
        <div className={fill} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

export default function WorldMap() {
  const { state } = useGame();
  const locationsByKingdom = useMemo(() => {
    const m = {};
    for (const loc of state.world.locations) {
      m[loc.kingdom_id] = m[loc.kingdom_id] || [];
      m[loc.kingdom_id].push(loc);
    }
    return m;
  }, [state]);

  const kingFor = (kid) => state.world.npcs.find((n) => n.id === state.world.kingdoms.find((k) => k.id === kid)?.king_id);

  return (
    <div className="space-y-8 rise-in">
      <div>
        <div className="label-tiny">Dünya</div>
        <h1 className="font-heading text-3xl sm:text-4xl text-stone-100">Yedi Tepe Diyarı</h1>
        <p className="text-stone-400 text-sm mt-1">
          Krallıklar yaşıyor, halklar çekişiyor, fiyatlar dalgalanıyor — sen olsan da olmasan da.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {state.world.kingdoms.map((k) => {
          const king = kingFor(k.id);
          const locs = locationsByKingdom[k.id] || [];
          const wars = k.at_war_with.length;
          return (
            <div key={k.id} className="card-frame p-5" data-testid={`kingdom-${k.id}`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="label-tiny">{k.culture} · {k.religion}</div>
                  <h2 className="font-heading text-xl text-stone-100">{k.name}</h2>
                </div>
                <Crown className="w-5 h-5 text-amber-500" />
              </div>
              {king && (
                <div className="text-xs text-stone-400 mb-3">
                  Kral <span className="text-stone-200">{king.name}</span> ({king.age})
                </div>
              )}
              <div className="space-y-3 mb-4">
                <StatBar value={k.stability} color="good" label="İstikrar" />
              </div>
              {wars > 0 && (
                <div className="text-xs text-red-400 border border-red-900/50 bg-red-950/30 px-2 py-1 rounded-sm mb-3">
                  {wars} krallıkla savaş halinde
                </div>
              )}
              <div className="divider-ash my-3" />
              <div className="space-y-1">
                {locs.map((loc) => {
                  const Icon = KIND_ICON[loc.kind] || MapPin;
                  return (
                    <Link
                      key={loc.id}
                      to={`/oyun/sehir/${loc.id}`}
                      data-testid={`location-${loc.id}`}
                      className="flex items-center justify-between text-sm py-1.5 px-2 rounded-sm hover:bg-stone-900/80 group"
                    >
                      <div className="flex items-center gap-2">
                        <Icon className="w-3.5 h-3.5 text-stone-500 group-hover:text-orange-500" />
                        <span className="text-stone-200">{loc.name}</span>
                        <span className="text-stone-600 text-xs">({loc.kind})</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-stone-500">
                        <span className="flex items-center gap-1"><ShieldCheck className="w-3 h-3" />{loc.security}</span>
                        <span className="flex items-center gap-1"><Coins className="w-3 h-3" />{loc.wealth}</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
