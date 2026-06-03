import { useEffect, useState } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { Baby, Lock, CheckCircle2, Hourglass } from "lucide-react";

const STATUS_LABEL = {
  "kilitli": "Kilitli",
  "açık": "Açık",
  "tamamlandı": "Tamamlandı",
};

const STATUS_STYLE = {
  "kilitli":     "text-stone-500 border-stone-800",
  "açık":        "text-amber-400 border-amber-900",
  "tamamlandı":  "text-emerald-400 border-emerald-900",
};

function objectiveText(obj, progress) {
  if (obj.type === "collect")       return `${obj.item} topla (${progress}/${obj.qty})`;
  if (obj.type === "work_count")    return `Bir hafta çalış (${progress}/${obj.qty})`;
  if (obj.type === "chat_count")    return `NPC ile konuş (${progress}/${obj.qty})`;
  if (obj.type === "travel_count")  return `Bir yere git (${progress}/${obj.qty})`;
  if (obj.type === "equip")         return `Kuşan: ${obj.item}`;
  return JSON.stringify(obj);
}

export default function FamilyQuests() {
  const { state } = useGame();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/game/family-quests").then(({ data }) => setData(data));
  }, [state.turn, state.player.age]);

  const quests = data?.quests || state.family_quests || [];
  const p = state.player;

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Aile Yolu</div>
        <h1 className="font-heading text-3xl text-stone-100 flex items-center gap-3">
          <Baby className="w-7 h-7 text-amber-500" /> Aile Görevleri
        </h1>
        <p className="text-stone-400 text-sm mt-1">
          {p.is_child ? (
            <>Sen daha bir çocuksun. Ailen sana yol gösteriyor.
            Bu görevleri tamamla — her birinden büyürken kalacak yetenekler kazanacaksın.</>
          ) : (
            <>Çocukluğun geride kaldı. Bu görevler artık seni şekillendirdi.</>
          )}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {quests.map((q) => {
          const Icon = q.status === "tamamlandı" ? CheckCircle2
                     : q.status === "kilitli" ? Lock : Hourglass;
          return (
            <div key={q.id} className="card-frame p-4" data-testid={`family-quest-${q.id}`}>
              <div className="flex justify-between items-start mb-2 gap-3">
                <h3 className="font-heading text-stone-100 flex items-center gap-2">
                  <Icon className="w-4 h-4 text-stone-400" />
                  {q.title}
                </h3>
                <span className={`text-[10px] px-2 py-0.5 border rounded-sm font-heading tracking-wider ${STATUS_STYLE[q.status]}`}>
                  {STATUS_LABEL[q.status]}
                </span>
              </div>
              <p className="text-sm text-stone-400 mb-3">{q.description}</p>
              <div className="text-xs text-stone-300 mb-2">
                Hedef: <span className="text-stone-200">{objectiveText(q.objective, q.progress)}</span>
              </div>
              <div className="flex justify-between text-[11px] text-stone-500">
                <span>Veren: {q.giver_role === "anne" ? "Annen" : "Baban"}</span>
                {q.min_age > p.age ? (
                  <span className="text-stone-600">{q.min_age} yaşında açılır</span>
                ) : (
                  <span>
                    Ödül:
                    {q.reward.money ? <span className="text-amber-400"> {q.reward.money}A</span> : null}
                    {q.reward.item ? <span className="text-orange-400"> +{Object.keys(q.reward.item)[0]}</span> : null}
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {quests.length === 0 && (
          <div className="text-stone-500 col-span-full">Aile görevi yok.</div>
        )}
      </div>
    </div>
  );
}
