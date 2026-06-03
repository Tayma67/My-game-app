import { useState } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { Swords } from "lucide-react";
import { toast } from "sonner";

export default function Battle() {
  const { state, setState } = useGame();
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState(null);

  const fight = async () => {
    setBusy(true);
    setLog([]);
    setOutcome(null);
    try {
      const { data } = await api.post("/game/battle");
      setState(data.state);
      setLog(data.log);
      setOutcome(data.outcome);
    } catch (e) {
      toast.error("Savaş başlatılamadı.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Çatışma</div>
        <h1 className="font-heading text-3xl text-stone-100 flex items-center gap-3">
          <Swords className="w-7 h-7 text-orange-600" /> Savaş Alanı
        </h1>
        <p className="text-stone-400 text-sm mt-1">
          Yollar tehlikelidir. Karşına çıkanı yenebilir misin?
        </p>
      </div>

      <div className="card-frame p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="text-sm text-stone-400">
            Sağlığın: <span className="text-emerald-400">{state.player.health}</span>
          </div>
          <button onClick={fight} disabled={busy || state.player.health < 20} data-testid="battle-start" className="btn-ember px-4 py-2 text-xs font-heading tracking-widest disabled:opacity-50">
            {busy ? "ÇARPIŞIYORSUN…" : state.player.health < 20 ? "ÖNCE İYİLEŞ" : "SAVAŞA GİR"}
          </button>
        </div>

        <div className="bg-stone-950 border border-stone-800 rounded-sm p-4 min-h-[220px] font-mono text-xs space-y-1" data-testid="battle-log">
          {log.length === 0 ? (
            <div className="text-stone-600 italic">Sessizlik... Karşına biri çıkmasını bekliyorsun.</div>
          ) : (
            log.map((line, i) => (
              <div key={i} className="text-stone-300 rise-in">{line}</div>
            ))
          )}
        </div>
        {outcome && (
          <div className={`mt-4 px-4 py-2 border rounded-sm text-sm font-heading tracking-widest ${outcome === "zafer" ? "border-emerald-800 text-emerald-400 bg-emerald-950/30" : "border-red-800 text-red-400 bg-red-950/30"}`} data-testid="battle-outcome">
            {outcome === "zafer" ? "ZAFER KAZANDIN" : "YENİLDİN"}
          </div>
        )}
      </div>
    </div>
  );
}
