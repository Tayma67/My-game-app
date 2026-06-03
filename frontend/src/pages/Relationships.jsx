import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useGame } from "@/lib/GameContext";

const BANDS = [
  { id: "dost", label: "Dostlar", test: (s) => s >= 50, cls: "border-emerald-800 text-emerald-300" },
  { id: "arkadaş", label: "Arkadaşlar", test: (s) => s >= 20 && s < 50, cls: "border-emerald-900/70 text-emerald-200" },
  { id: "nötr", label: "Nötr", test: (s) => s > -20 && s < 20, cls: "border-stone-700 text-stone-300" },
  { id: "rakip", label: "Rakipler", test: (s) => s <= -20 && s > -50, cls: "border-red-900/70 text-red-300" },
  { id: "düşman", label: "Düşmanlar", test: (s) => s <= -50, cls: "border-red-800 text-red-400" },
];

export default function Relationships() {
  const { state } = useGame();
  const grouped = useMemo(() => {
    const out = {};
    for (const band of BANDS) out[band.id] = [];
    for (const [npcId, score] of Object.entries(state.relationships || {})) {
      const npc = state.world.npcs.find((n) => n.id === npcId);
      if (!npc) continue;
      const band = BANDS.find((b) => b.test(score));
      if (band) out[band.id].push({ npc, score });
    }
    for (const k of Object.keys(out)) {
      out[k].sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
    }
    return out;
  }, [state]);

  const total = Object.values(grouped).reduce((s, a) => s + a.length, 0);

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">İlişkiler</div>
        <h1 className="font-heading text-3xl text-stone-100">Bağlar & Anlaşmazlıklar</h1>
        <p className="text-stone-400 text-sm mt-1">
          {total === 0 ? "Henüz kimseyle bağ kurmadın." : `${total} kişiyle bir ilişkin var.`}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {BANDS.map((band) => (
          <div key={band.id} className="card-frame p-4">
            <div className={`text-xs px-2 py-1 inline-block border rounded-sm font-heading tracking-wider ${band.cls}`}>
              {band.label} ({grouped[band.id].length})
            </div>
            <ul className="mt-3 space-y-1.5">
              {grouped[band.id].map(({ npc, score }) => (
                <li key={npc.id} className="flex justify-between text-sm">
                  <Link to={`/oyun/npc/${npc.id}`} className="text-stone-200 hover:text-orange-400 truncate mr-2" data-testid={`rel-${npc.id}`}>
                    {npc.name}
                  </Link>
                  <span className="text-stone-500 text-xs shrink-0">{score > 0 ? `+${score}` : score}</span>
                </li>
              ))}
              {grouped[band.id].length === 0 && (
                <li className="text-stone-600 text-xs italic">—</li>
              )}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
