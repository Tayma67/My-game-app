import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useGame } from "@/lib/GameContext";
import { Crown, Search } from "lucide-react";

function bandFromScore(score = 0) {
  if (score < -50) return ["düşman", "text-red-400"];
  if (score < -20) return ["rakip", "text-red-300"];
  if (score < 20) return ["nötr", "text-stone-400"];
  if (score < 50) return ["arkadaş", "text-emerald-300"];
  return ["dost", "text-emerald-400"];
}

export default function NPCList() {
  const { state } = useGame();
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("hepsi");

  const npcs = useMemo(() => {
    let arr = state.world.npcs.filter((n) => n.alive);
    if (filter === "burası") arr = arr.filter((n) => n.location_id === state.player.location_id);
    if (filter === "krali") arr = arr.filter((n) => ["kral", "veliaht", "lord", "general"].includes(n.profession));
    if (q) arr = arr.filter((n) => n.name.toLowerCase().includes(q.toLowerCase()));
    return arr;
  }, [state, q, filter]);

  return (
    <div className="space-y-6 rise-in">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="label-tiny">NPC Defteri</div>
          <h1 className="font-heading text-3xl text-stone-100">Yaşayan Ruhlar</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2.5 top-2.5 text-stone-500" />
            <input
              data-testid="npc-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="İsim ara…"
              className="pl-8 pr-3 py-2 bg-stone-950 border border-stone-800 text-sm rounded-sm"
            />
          </div>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            data-testid="npc-filter"
            className="bg-stone-950 border border-stone-800 px-3 py-2 text-sm rounded-sm"
          >
            <option value="hepsi">Hepsi ({state.world.npcs.filter(n=>n.alive).length})</option>
            <option value="burası">Bu Konumda</option>
            <option value="krali">Soylular</option>
          </select>
        </div>
      </div>

      <div className="card-frame divide-y divide-stone-900">
        {npcs.slice(0, 200).map((n) => {
          const rel = state.relationships?.[n.id] ?? 0;
          const [band, cls] = bandFromScore(rel);
          return (
            <Link key={n.id} to={`/oyun/npc/${n.id}`} data-testid={`npc-row-${n.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-stone-900/60 text-sm">
              <div className="flex items-center gap-3 min-w-0">
                {["kral", "veliaht"].includes(n.profession) && <Crown className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                <div className="min-w-0">
                  <div className="text-stone-100 truncate">{n.name}</div>
                  <div className="text-xs text-stone-500 truncate">{n.profession} · {n.age} · {n.location_name}</div>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-xs ${cls}`}>{band}</div>
                <div className="text-[10px] text-stone-600">{rel > 0 ? `+${rel}` : rel}</div>
              </div>
            </Link>
          );
        })}
        {npcs.length === 0 && <div className="px-4 py-6 text-stone-500 text-sm">Kimse bulunamadı.</div>}
      </div>
      {npcs.length > 200 && <div className="text-xs text-stone-500">İlk 200 sonuç gösteriliyor.</div>}
    </div>
  );
}
