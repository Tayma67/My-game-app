import { useState, useEffect } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Heart, Coins, ShieldAlert, Zap, Briefcase, Sword, Hammer, ShoppingBasket,
  Users, Sparkles, Lock, Baby, Apple,
} from "lucide-react";

const STAT_META = [
  { key: "strength",      label: "Güç",       icon: Sword,   color: "text-red-400",     fill: "bg-red-700" },
  { key: "intelligence",  label: "Zekâ",      icon: Sparkles,color: "text-sky-400",     fill: "bg-sky-700" },
  { key: "charisma",      label: "Karizma",   icon: Users,   color: "text-pink-400",    fill: "bg-pink-700" },
  { key: "stamina",       label: "Dayanıklılık", icon: Heart,color: "text-emerald-400", fill: "bg-emerald-700" },
];

const SKILL_META = [
  { key: "combat",   label: "Savaş",     icon: Sword,         fill: "bg-red-700" },
  { key: "trade",    label: "Ticaret",   icon: ShoppingBasket,fill: "bg-amber-700" },
  { key: "crafting", label: "Zanaat",    icon: Hammer,        fill: "bg-stone-500" },
  { key: "social",   label: "Sosyal",    icon: Users,         fill: "bg-pink-700" },
];

const CRIMES = [
  { id: "hırsızlık", label: "Hırsızlık" },
  { id: "kaçakçılık", label: "Kaçakçılık" },
  { id: "dolandırıcılık", label: "Dolandırıcılık" },
];

function Bar({ value, max = 10, fill = "bg-orange-700", small = false }) {
  const w = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`bg-stone-900 rounded-sm overflow-hidden ${small ? "h-1.5" : "h-2"}`}>
      <div className={`h-full ${fill}`} style={{ width: `${w}%` }} />
    </div>
  );
}

export default function CharacterSheet() {
  const { state, setState } = useGame();
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [skillsData, setSkillsData] = useState(null);

  const p = state.player;
  const parents = (p.parent_ids || [])
    .map((id) => state.world.npcs.find((n) => n.id === id))
    .filter(Boolean);
  const spouse = p.spouse_id ? state.world.npcs.find((n) => n.id === p.spouse_id) : null;
  const children = (p.children_ids || [])
    .filter((id) => id !== "PLAYER")
    .map((cid) => state.world.npcs.find((n) => n.id === cid))
    .filter(Boolean);

  useEffect(() => {
    api.get("/game/jobs").then(({ data }) => setJobs(data.jobs || []));
    api.get("/game/skills").then(({ data }) => setSkillsData(data));
  }, [state.turn, state.player.age]);

  const doWork = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/work");
      setState(data.state || data);
      if (data.enforcement) {
        toast.error(`${data.enforcement.by} seni yakaladı: ${data.enforcement.fine} altın ceza.`);
      } else {
        const lvls = (data.leveled || []).map((l) => `${l[1]} +1`).join(", ");
        toast.success(`Bir hafta çalıştın (+${data.income || 0} altın)${lvls ? ` · ${lvls}` : ""}`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Çalışılamadı.");
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
        <p className="text-stone-400 text-sm flex items-center flex-wrap gap-x-2">
          <span>{p.gender}</span>·<span data-testid="char-age">{p.age} yaşında</span>
          {p.is_child && (
            <span className="text-[10px] uppercase tracking-wider text-amber-400 border border-amber-900 px-1.5 py-0.5 rounded-sm flex items-center gap-1">
              <Baby className="w-3 h-3" /> Çocuk · 13 yaşında özgürleşeceksin
            </span>
          )}
          <span>·</span><span>{p.culture}</span>·<span>{p.religion}</span>
        </p>
      </div>

      {/* Top stats grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card-frame p-5 lg:col-span-2 space-y-5">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <KpiBlock icon={Coins} label="Altın" value={p.money} color="text-amber-400" />
            <KpiBlock icon={Heart} label="Sağlık" value={p.health} color="text-emerald-400" />
            <KpiBlock icon={Apple} label="Açlık" value={p.hunger ?? 100} color={(p.hunger ?? 100) < 25 ? "text-red-400" : "text-orange-300"} />
            <KpiBlock icon={ShieldAlert} label="Suç" value={p.crime || 0} color="text-red-400" />
          </div>
          <div className="divider-ash" />

          {/* Stats */}
          <div>
            <div className="label-tiny mb-3">Temel Yetenekler (1-10)</div>
            <div className="grid grid-cols-2 gap-4">
              {STAT_META.map((s) => {
                const v = p.stats?.[s.key] ?? 0;
                const xp = p.stat_xp?.[s.key] ?? 0;
                const next = 25 + v * 15;
                const Icon = s.icon;
                return (
                  <div key={s.key} data-testid={`stat-${s.key}`}>
                    <div className="flex justify-between mb-1 text-xs">
                      <span className="flex items-center gap-1.5">
                        <Icon className={`w-3 h-3 ${s.color}`} />
                        <span className={s.color}>{s.label}</span>
                      </span>
                      <span className="text-stone-300 font-heading">{v}/10</span>
                    </div>
                    <Bar value={v} max={10} fill={s.fill} />
                    <div className="text-[10px] text-stone-500 mt-0.5">XP: {xp}/{next}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="divider-ash" />

          {/* Skills */}
          <div>
            <div className="label-tiny mb-3">Yetenek Ağaçları (0-10)</div>
            <div className="grid grid-cols-2 gap-4">
              {SKILL_META.map((s) => {
                const v = p.skills?.[s.key] ?? 0;
                const xp = p.skill_xp?.[s.key] ?? 0;
                const next = 10 + v * 5;
                const Icon = s.icon;
                return (
                  <div key={s.key} data-testid={`skill-${s.key}`}>
                    <div className="flex justify-between mb-1 text-xs">
                      <span className="flex items-center gap-1.5 text-stone-300">
                        <Icon className="w-3 h-3" /> {s.label}
                      </span>
                      <span className="text-stone-200 font-heading">{v}/10</span>
                    </div>
                    <Bar value={v} max={10} fill={s.fill} />
                    <div className="text-[10px] text-stone-500 mt-0.5">XP: {xp}/{next}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Perks */}
          {(p.perks || []).length > 0 && (
            <>
              <div className="divider-ash" />
              <div>
                <div className="label-tiny mb-2 flex items-center gap-1"><Sparkles className="w-3 h-3 text-amber-400" /> Açılan Yetenekler</div>
                <ul className="space-y-1.5">
                  {p.perks.map((perk) => (
                    <li key={perk.perk} className="text-xs text-stone-300" data-testid={`perk-${perk.perk}`}>
                      <span className="text-amber-400 font-heading uppercase tracking-wider">{perk.skill}</span>
                      <span className="text-stone-500"> · {perk.level} → </span>
                      <span>{perk.desc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>

        {/* Family card */}
        <div className="card-frame p-5 space-y-4">
          <h2 className="font-heading text-lg text-stone-100 flex items-center gap-2"><Users className="w-4 h-4 text-stone-500" /> Aile</h2>
          {parents.length > 0 && (
            <div>
              <div className="label-tiny mb-1">Ebeveynler</div>
              <ul className="text-sm text-stone-300 space-y-0.5">
                {parents.map((par) => (
                  <li key={par.id} data-testid={`parent-${par.id}`}>
                    <span className="text-stone-200">{par.name}</span>
                    <span className="text-stone-500"> · {par.profession} · {par.age}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
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
          <div className="divider-ash" />
          <div>
            <div className="label-tiny mb-1">Meslek</div>
            <div className="flex items-center gap-2 text-stone-200 capitalize">
              <Briefcase className="w-3 h-3 text-stone-500" /> {p.profession}
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="card-frame p-5 space-y-4">
        <h2 className="font-heading text-lg text-stone-100">Eylemler</h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={doWork}
            disabled={busy}
            data-testid="action-work"
            className="btn-ember px-4 py-2 text-xs font-heading tracking-widest disabled:opacity-50"
          >
            BİR HAFTA ÇALIŞ
          </button>
          {!p.is_child && CRIMES.map((c) => (
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

        {p.is_child && (
          <div className="text-xs text-amber-400/80 italic border border-amber-900/50 rounded-sm p-3 bg-amber-950/20">
            <Baby className="w-3 h-3 inline-block mr-1" />
            Çocuksun — sadece "işsiz" ve "köylü" yapabilirsin, suç işleyemezsin.
            Ama yaptıkların yine de seni şekillendiriyor: bugün topladığın her odun,
            yarın daha güçlü bir adam olmana yarayacak.
          </div>
        )}

        <div className="pt-2">
          <div className="label-tiny mb-2">Meslekler</div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {jobs.map((j) => {
              const isCurrent = j.job === p.profession;
              const locked = !j.eligible;
              return (
                <button
                  key={j.job}
                  onClick={() => !locked && changeJob(j.job)}
                  disabled={busy || locked || isCurrent}
                  data-testid={`job-${j.job}`}
                  title={locked ? j.missing.join(", ") : ""}
                  className={`px-3 py-2 text-xs border rounded-sm text-left capitalize transition-colors ${
                    isCurrent
                      ? "border-orange-700 text-orange-400 bg-stone-900"
                      : locked
                        ? "border-stone-900 text-stone-600 cursor-not-allowed"
                        : "border-stone-800 text-stone-300 hover:border-orange-800 hover:bg-stone-900/60"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    {locked && <Lock className="w-3 h-3" />}
                    <span className="font-heading tracking-wide">{j.job}</span>
                  </div>
                  {locked && j.missing.length > 0 && (
                    <div className="text-[9px] text-stone-600 mt-0.5 truncate">
                      {j.missing.slice(0, 2).join(", ")}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiBlock({ icon: Icon, label, value, color = "text-stone-200" }) {
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
