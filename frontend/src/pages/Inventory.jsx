import { useMemo } from "react";
import { useGame } from "@/lib/GameContext";
import { Package } from "lucide-react";

export default function Inventory() {
  const { state } = useGame();
  const inv = state.player.inventory || {};
  const items = Object.entries(inv).filter(([, q]) => q > 0);

  // Estimate net worth across all known prices (current location)
  const currentLoc = state.world.locations.find((l) => l.id === state.player.location_id);
  const netWorth = useMemo(() => {
    let v = state.player.money;
    if (currentLoc) {
      for (const [g, q] of items) {
        v += (currentLoc.prices[g] || 0) * q;
      }
    }
    return Math.round(v);
  }, [items, currentLoc, state.player.money]);

  // Market comparison across all locations
  const allGoods = currentLoc ? Object.keys(currentLoc.prices) : [];

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Envanter</div>
        <h1 className="font-heading text-3xl text-stone-100">Heybe & Pazarlar</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card-frame p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-lg flex items-center gap-2 text-stone-100"><Package className="w-4 h-4" /> Eşyalarım</h2>
            <div className="text-xs text-stone-500">Toplam Değer: <span className="text-amber-400">{netWorth} altın</span></div>
          </div>
          {items.length === 0 ? (
            <div className="text-stone-500 text-sm">Heyben bomboş.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-stone-800 text-xs">
                  <th className="text-left py-2 label-tiny">Ürün</th>
                  <th className="text-right py-2 label-tiny">Miktar</th>
                  <th className="text-right py-2 label-tiny">Burada Fiyat</th>
                </tr>
              </thead>
              <tbody>
                {items.map(([g, q]) => (
                  <tr key={g} className="border-b border-stone-900" data-testid={`inv-row-${g}`}>
                    <td className="py-2 capitalize text-stone-200">{g}</td>
                    <td className="py-2 text-right text-stone-300">{q}</td>
                    <td className="py-2 text-right text-amber-400">
                      {currentLoc ? currentLoc.prices[g] : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="text-xs text-stone-500 mt-3">
            Satmak için bir şehrin pazarına git: <span className="text-stone-300">{currentLoc?.name}</span> menüsü.
          </div>
        </div>

        <div className="card-frame p-5">
          <h2 className="font-heading text-lg text-stone-100 mb-4">Pazar Karşılaştırma</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-stone-800">
                  <th className="text-left py-2 label-tiny">Konum</th>
                  {allGoods.map((g) => (
                    <th key={g} className="text-right py-2 label-tiny capitalize">{g}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {state.world.locations.map((loc) => (
                  <tr key={loc.id} className="border-b border-stone-900">
                    <td className="py-1.5 text-stone-200">{loc.name}</td>
                    {allGoods.map((g) => {
                      const here = currentLoc?.prices[g] || 0;
                      const there = loc.prices[g];
                      const diff = there - here;
                      const cls = diff > 0 ? "text-emerald-400" : diff < 0 ? "text-red-400" : "text-stone-400";
                      return <td key={g} className={`py-1.5 text-right ${cls}`}>{there}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
