import { useParams, Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useGame } from "@/lib/GameContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft, Crown, Heart, Skull, MessageCircle, Swords, Brain } from "lucide-react";

function bandFromScore(score = 0) {
  if (score < -50) return { name: "düşman", cls: "text-red-400 border-red-900" };
  if (score < -20) return { name: "rakip", cls: "text-red-300 border-red-900/60" };
  if (score < 20) return { name: "nötr", cls: "text-stone-400 border-stone-700" };
  if (score < 50) return { name: "arkadaş", cls: "text-emerald-300 border-emerald-900" };
  return { name: "dost", cls: "text-emerald-400 border-emerald-800" };
}

export default function NPCDetail() {
  const { id } = useParams();
  const { state, setState } = useGame();
  const navigate = useNavigate();
  const [topics, setTopics] = useState([]);
  const [chat, setChat] = useState([]);
  const [busy, setBusy] = useState(false);

  const npc = state?.world.npcs.find((n) => n.id === id);

  useEffect(() => {
    api.get("/game/dialog-topics").then((r) => setTopics(r.data));
  }, []);

  if (!npc) {
    return (
      <div className="text-stone-400">
        NPC bulunamadı. <Link to="/oyun/npcler" className="text-orange-500">Geri</Link>
      </div>
    );
  }

  const rel = state.relationships?.[npc.id] ?? 0;
  const band = bandFromScore(rel);
  const spouse = npc.spouse_id && npc.spouse_id !== "PLAYER"
    ? state.world.npcs.find((n) => n.id === npc.spouse_id)
    : null;
  const isPlayerSpouse = npc.spouse_id === "PLAYER";
  const children = (npc.children_ids || []).map(
    (cid) => state.world.npcs.find((n) => n.id === cid)
  ).filter(Boolean);
  const parents = (npc.parent_ids || []).map(
    (pid) => state.world.npcs.find((n) => n.id === pid)
  ).filter(Boolean);

  const speak = async (topic, label) => {
    setBusy(true);
    setChat((c) => [...c, { from: "p", text: label }]);
    try {
      const { data } = await api.post("/game/chat", { npc_id: npc.id, topic });
      setChat((c) => [...c, {
        from: "n",
        text: data.response,
        repeat: data.repeat_count,
        delta: data.delta,
      }]);
      // sync state so relationship counter + NPC interactions update
      const r = await api.get("/game/state");
      setState(r.data);
      if (data.hostile) toast.error(`${npc.name} sana saldırıyor!`);
    } catch (e) {
      toast.error("Konuşma başarısız.");
    } finally {
      setBusy(false);
    }
  };

  const marry = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/game/marry", { npc_id: npc.id });
      setState(data);
      toast.success(`${npc.name} ile evlendin!`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Evlilik reddedildi.");
    } finally {
      setBusy(false);
    }
  };

  const attack = async () => {
    if (!window.confirm(`${npc.name}'a saldırmak istediğinden emin misin? Bu suç işlemen anlamına gelir.`)) return;
    setBusy(true);
    try {
      const { data } = await api.post("/game/attack_npc", { npc_id: npc.id });
      setState(data.state);
      setChat((c) => [
        ...c,
        ...data.log.map((line) => ({ from: "n", text: line })),
        { from: "n", text: data.outcome === "zafer" ? "ZAFER" : "YENİLDİN", band: "düşman" },
      ]);
      if (data.enforcement) {
        toast.error(`${data.enforcement.by} seni yakaladı! ${data.enforcement.fine} altın ceza.`);
      } else {
        toast(data.outcome === "zafer" ? "Saldırı başarılı." : "Yenildin.");
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Saldırı başarısız.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 rise-in">
      <button onClick={() => navigate(-1)} className="text-stone-400 hover:text-stone-200 flex items-center gap-2 text-sm" data-testid="npc-back">
        <ArrowLeft className="w-4 h-4" /> Geri
      </button>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card-frame p-5 lg:col-span-1 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="label-tiny">{npc.profession}</div>
              <h1 className="font-heading text-2xl text-stone-100 flex items-center gap-2">
                {["kral", "veliaht"].includes(npc.profession) && <Crown className="w-5 h-5 text-amber-500" />}
                {npc.name}
              </h1>
              <div className="text-xs text-stone-500 mt-1">{npc.age} yaşında · {npc.gender} · {npc.location_name}</div>
            </div>
            {!npc.alive && <Skull className="w-5 h-5 text-stone-500" />}
          </div>

          <div className={`px-2 py-1 inline-block text-xs rounded-sm border ${band.cls}`} data-testid="npc-band">
            {band.name} · {rel > 0 ? `+${rel}` : rel}
          </div>

          <div className="space-y-2 text-sm">
            <Row label="Kişilik">{npc.personality.join(", ")}</Row>
            <Row label="Hedef">{npc.goal}</Row>
            <Row label="Mizaç">{npc.mood}</Row>
            <Row label="Servet">{npc.wealth} altın</Row>
            <Row label="Sağlık">{npc.health}/100</Row>
            <Row label="Din">{npc.religion}</Row>
          </div>

          <div className="divider-ash" />
          <div>
            <div className="label-tiny mb-2">Aile Bağları</div>
            <div className="text-xs text-stone-300 space-y-1">
              {parents.length > 0 && <div>Anne/Baba: {parents.map((p) => p.name).join(", ")}</div>}
              {spouse && <div>Eşi: <Link to={`/oyun/npc/${spouse.id}`} className="text-orange-400">{spouse.name}</Link></div>}
              {isPlayerSpouse && <div className="text-orange-400">Senin eşin.</div>}
              {children.length > 0 && (
                <div>Çocukları: {children.map((c, i) => (
                  <span key={c.id}>
                    {i > 0 && ", "}
                    <Link to={`/oyun/npc/${c.id}`} className="text-orange-400">{c.name}</Link>
                  </span>
                ))}</div>
              )}
              {parents.length + (spouse ? 1 : 0) + children.length === 0 && (
                <div className="text-stone-600">Bilinen aile bağı yok.</div>
              )}
            </div>
          </div>

          {!isPlayerSpouse && !state.player.spouse_id && rel >= 60 && npc.age >= 18 && !npc.spouse_id && (
            <button onClick={marry} disabled={busy} data-testid="npc-marry" className="btn-ember w-full py-2 text-xs font-heading tracking-widest disabled:opacity-50 flex items-center justify-center gap-2">
              <Heart className="w-4 h-4" /> EVLENME TEKLİF ET
            </button>
          )}

          {npc.alive && npc.location_id === state.player.location_id && (
            <button
              onClick={attack}
              disabled={busy}
              data-testid="npc-attack"
              className="w-full py-2 text-xs font-heading tracking-widest disabled:opacity-50 flex items-center justify-center gap-2 border border-red-900 text-red-400 hover:bg-red-950/40 rounded-sm"
            >
              <Swords className="w-4 h-4" /> SALDIR
            </button>
          )}

          {(npc.memory || []).length > 0 && (
            <div className="pt-3 border-t border-stone-800">
              <div className="label-tiny mb-2 flex items-center gap-1"><Brain className="w-3 h-3" /> Hatırladıkları</div>
              <ul className="text-xs space-y-1 text-stone-500 max-h-32 overflow-y-auto">
                {(npc.memory || []).slice(-6).reverse().map((m, i) => (
                  <li key={i} className="flex justify-between gap-2">
                    <span>Gün {m.day}: <span className="text-stone-300">{m.topic}</span></span>
                    <span className={m.delta > 0 ? "text-emerald-400" : m.delta < 0 ? "text-red-400" : "text-stone-600"}>
                      {m.delta > 0 ? `+${m.delta}` : m.delta}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="card-frame p-5 lg:col-span-2 flex flex-col" style={{ minHeight: 480 }}>
          <h2 className="font-heading text-lg text-stone-100 mb-3 flex items-center gap-2">
            <MessageCircle className="w-4 h-4" /> Konuşma
          </h2>
          <div className="flex-1 overflow-y-auto space-y-3 pr-2 mb-4" data-testid="chat-log">
            {chat.length === 0 && (
              <div className="text-stone-500 text-sm italic">Bir konu seçerek konuşmaya başla.</div>
            )}
            {chat.map((m, i) => (
              <div key={i} className={`max-w-[85%] ${m.from === "p" ? "ml-auto text-right" : ""}`}>
                <div
                  className={`inline-block px-3 py-2 rounded-sm text-sm ${
                    m.from === "p"
                      ? "bg-orange-900/40 border border-orange-900 text-stone-100"
                      : "bg-stone-900 border border-stone-800 text-stone-200"
                  }`}
                >
                  {m.text}
                </div>
                <div className="text-[10px] text-stone-600 mt-0.5">{m.from === "p" ? "Sen" : npc.name}</div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 border-t border-stone-800 pt-4">
            {topics.map((t) => (
              <button
                key={t.id}
                onClick={() => speak(t.id, t.label)}
                disabled={busy || !npc.alive}
                data-testid={`chat-topic-${t.id}`}
                className="btn-ghost-ash px-3 py-1.5 text-xs disabled:opacity-50"
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div className="flex justify-between">
      <span className="label-tiny pt-0.5">{label}</span>
      <span className="text-stone-200 text-right max-w-[60%]">{children}</span>
    </div>
  );
}
