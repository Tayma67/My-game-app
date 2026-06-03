import { useState } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Heart, Coins, ShieldAlert, Zap, BookOpen, Pickaxe, Sword, Swords, Briefcase } from "lucide-react";

const PROFESSIONS = ["köylü", "çiftçi", "asker", "tüccar", "avcı", "zanaatkar", "haydut"];

const CRIMES = [
  { id: "hırsızlık", label: "Hırsızlık" },
  { id: "kaçakçılık", label: "Kaçakçılık" },
  { id: "dolandırıcılık", label: "Dolandırıcılık" },
];

function Bar({ value, max = 100, color = "good", label }) {
  const fill = {
    good: "stat-bar-fill-good",
    bad: "stat-bar-fill-bad",
    ember: "stat-bar-fill",
    cool: "stat-bar-fill-cool",
  }[color];
  const w = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="label-tiny">{label}</span>
        <span className="text-xs text-stone-300">{value}{max === 100 ? "" : `/${max}`}</span>
      </div>
      <div className="stat-bar">
        <div className={`stat-bar-fill ${fill}`} style={{ width: `${w}%` }} />
      </div>
    </div>
  );
}

export default function CharacterSheet() {
  const { state, setState } = useGame();
  const [busy, setBusy] = useState(false);
  const p = state.player;
  const spouse = p.spouse_id ? state.world.npcs.find((n) => n.id === p.spouse_id) : null;
  const children = (p.children_ids || []).map(
    (cid) => state.world.npcs.find((n) => n.id === cid)
  ).filter(Boolean);

  const doWork = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/work");
      setState(data.state || data);
      if (data.enforcement) {
        toast.error(`${data.enforcement.by} seni yakaladı: ${data.enforcement.fine} altın ceza.`);
      } else {
        toast.success(`Bir hafta çalıştın (+${data.income || 0} altın).`);
      }
    } catch (e) {
      toast.error("Çalışılamadı.");
    } finally {
      setBusy(false);
    }
  };

  const changeJob = async (prof) => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/job", { profession: prof });
      setState(data);
      toast.success(`Artık bir ${prof}sın.`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Meslek değiştirilemedi.");
    } finally {
      setBusy(false);
    }
  };

  const commitCrime = async (crime_type) => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/crime", { crime_type });
      setState(data.state);
      if (data.outcome.caught) {
        toast.error(`Yakalandın! ${data.outcome.fine} altın ceza.`);
      } else {
        toast.success(`Başarılı! +${data.outcome.gain} altın.`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Başarısız");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Karakter</div>
        <h1 className="font-heading text-3xl text-stone-100">{p.name}</h1>
        <p className="text-stone-400 text-sm">{p.gender} · {p.age} yaşında · {p.culture} kültürü · {p.religion}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card-frame p-5 lg:col-span-2 space-y-5">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Stat icon={Coins} label="Altın" value={p.money} color="text-amber-400" />
            <Stat icon={Heart} label="Sağlık" value={p.health} color="text-emerald-400" />
            <Stat icon={Zap} label="İtibar" value={p.reputation} color="text-orange-400" />
            <Stat icon={ShieldAlert} label="Suç" value={p.crime || 0} color="text-red-400" />
          </div>
          <div className="divider-ash" />
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="label-tiny mb-2">Meslek</div>
              <div className="flex items-center gap-2 text-stone-200">
                <Briefcase className="w-4 h-4 text-stone-500" />
                <span className="capitalize">{p.profession}</span>
              </div>
            </div>
            <div>
              <div className="label-tiny mb-2">Eğitim</div>
              <div className="flex items-center gap-2 text-stone-200">
                <BookOpen className="w-4 h-4 text-stone-500" />
                <span className="capitalize">{p.education}</span>
              </div>
            </div>
            <div>
              <div className="label-tiny mb-2">Konum</div>
              <div className="text-stone-200">{p.location_name}</div>
            </div>
            <div>
              <div className="label-tiny mb-2">Krallık</div>
              <div className="text-stone-200">{p.kingdom_name}</div>
            </div>
          </div>
          <div className="divider-ash" />
          <div>
            <div className="label-tiny mb-3">Yetenekler</div>
            <div className="grid grid-cols-2 gap-4">
              <Bar value={p.skills.savaş} max={10} color="bad" label="Savaş" />
              <Bar value={p.skills.ticaret} max={10} color="ember" label="Ticaret" />
              <Bar value={p.skills.avcılık} max={10} color="good" label="Avcılık" />
              <Bar value={p.skills.diplomasi} max={10} color="cool" label="Diplomasi" />
            </div>
          </div>
        </div>

        <div className="card-frame p-5 space-y-4">
          <h2 className="font-heading text-lg text-stone-100">Aile</h2>
          <div>
            <div className="label-tiny mb-1">Eş</div>
            <div className="text-stone-200">{spouse ? spouse.name : <span className="text-stone-500">—</span>}</div>
          </div>
          <div>
            <div className="label-tiny mb-1">Çocuklar ({children.length})</div>
            {children.length === 0 ? (
              <div className="text-stone-500 text-sm">Henüz yok</div>
            ) : (
              <ul className="text-sm text-stone-300 space-y-1">
                {children.map((c) => <li key={c.id}>{c.name} ({c.age})</li>)}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="card-frame p-5 space-y-4">
        <h2 className="font-heading text-lg text-stone-100 flex items-center gap-2"><Pickaxe className="w-4 h-4" /> Eylemler</h2>
        <div className="flex flex-wrap gap-3">
          <button onClick={doWork} disabled={busy} data-testid="action-work" className="btn-ember px-4 py-2 text-xs font-heading tracking-widest disabled:opacity-50">
            BİR HAFTA ÇALIŞ
          </button>
          {CRIMES.map((c) => (
            <button
              key={c.id}
              onClick={() => commitCrime(c.id)}
              disabled={busy}
              data-testid={`crime-${c.id}`}
              className="btn-ghost-ash px-3 py-2 text-xs font-heading tracking-widest disabled:opacity-50"
            >
              {c.label.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="pt-2">
          <div className="label-tiny mb-2">Meslek Değiştir</div>
          <div className="flex flex-wrap gap-2">
            {PROFESSIONS.map((prof) => (
              <button
                key={prof}
                onClick={() => changeJob(prof)}
                disabled={busy || prof === p.profession}
                data-testid={`job-${prof}`}
                className={`px-3 py-1.5 text-xs border rounded-sm capitalize ${
                  prof === p.profession
                    ? "border-orange-700 text-orange-400 bg-stone-900"
                    : "border-stone-800 text-stone-300 hover:border-orange-800"
                }`}
              >
                {prof}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, color = "text-stone-200" }) {
  return (
    <div>
      <div className="flex items-center gap-1 label-tiny mb-1">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <div className={`font-heading text-2xl ${color}`}>{value}</div>
    </div>
  );
}
