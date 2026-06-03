import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useState } from "react";
import { ListChecks } from "lucide-react";

const STATUS_LABEL = {
  açık: "Açık",
  kabul_edildi: "Kabul Edildi",
  tamamlandı: "Tamamlandı",
  başarısız: "Başarısız",
};

const STATUS_COLOR = {
  açık: "text-amber-400 border-amber-900",
  kabul_edildi: "text-orange-400 border-orange-900",
  tamamlandı: "text-emerald-400 border-emerald-900",
  başarısız: "text-red-400 border-red-900",
};

export default function Quests() {
  const { state, setState } = useGame();
  const [busy, setBusy] = useState(null);
  const quests = [...(state.quests || [])].reverse();

  const accept = async (id) => {
    setBusy(id);
    try {
      const { data } = await api.post("/game/quest/accept", { quest_id: id });
      setState(data);
      toast.success("Görev kabul edildi.");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Hata");
    } finally {
      setBusy(null);
    }
  };

  const complete = async (id) => {
    setBusy(id);
    try {
      const { data } = await api.post("/game/quest/complete", { quest_id: id });
      setState(data);
      toast.success("Görev sonuçlandı.");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Hata");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Görev Defteri</div>
        <h1 className="font-heading text-3xl text-stone-100 flex items-center gap-3">
          <ListChecks className="w-7 h-7 text-orange-600" /> Yapılacaklar
        </h1>
        <p className="text-stone-400 text-sm mt-1">
          Görevler dünyada kendiliğinden doğar. Zamanı ilerlettikçe yenileri çıkar.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {quests.map((q) => (
          <div key={q.id} className="card-frame p-4" data-testid={`quest-${q.id}`}>
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-heading text-stone-100">{q.title}</h3>
              <span className={`text-[10px] px-2 py-0.5 border rounded-sm font-heading tracking-wider ${STATUS_COLOR[q.status]}`}>
                {STATUS_LABEL[q.status]}
              </span>
            </div>
            <p className="text-sm text-stone-400 mb-3">{q.description}</p>
            <div className="flex justify-between items-center text-xs text-stone-500">
              <span>Konum: {q.location_name}</span>
              <span>Ödül: <span className="text-amber-400">{q.reward}a</span></span>
            </div>
            <div className="flex gap-2 mt-3">
              {q.status === "açık" && (
                <button onClick={() => accept(q.id)} disabled={busy === q.id} data-testid={`quest-accept-${q.id}`} className="btn-ghost-ash px-3 py-1.5 text-xs">
                  Kabul Et
                </button>
              )}
              {(q.status === "açık" || q.status === "kabul_edildi") && (
                <button onClick={() => complete(q.id)} disabled={busy === q.id} data-testid={`quest-complete-${q.id}`} className="btn-ember px-3 py-1.5 text-xs font-heading tracking-wider">
                  Tamamlamayı Dene
                </button>
              )}
            </div>
          </div>
        ))}
        {quests.length === 0 && (
          <div className="text-stone-500 col-span-full">
            Henüz bir görev yok. Birkaç gün geçir, dünya kendi sorunlarını yaratır.
          </div>
        )}
      </div>
    </div>
  );
}
