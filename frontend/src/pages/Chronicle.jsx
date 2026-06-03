import { useGame } from "@/lib/GameContext";
import { ScrollText } from "lucide-react";

const TYPE_LABEL = {
  başlangıç: "Başlangıç",
  ölüm: "Ölüm",
  doğum: "Doğum",
  evlilik: "Evlilik",
  tahta_çıkış: "Taht",
  savaş_ilanı: "Savaş",
  barış: "Barış",
  isyan: "İsyan",
  kıtlık: "Kıtlık",
  haydut_baskını: "Baskın",
  şenlik: "Şenlik",
  yolculuk: "Yolculuk",
  ticaret: "Ticaret",
  çalışma: "Emek",
  suç: "Suç",
  suç_yakalandı: "Yakalandı",
  meslek_değişimi: "Meslek",
  görev_tamamlandı: "Görev",
  görev_başarısız: "Başarısız",
  savaş_zaferi: "Zafer",
  savaş_kaybı: "Kayıp",
};

const TYPE_COLOR = {
  ölüm: "border-red-900 text-red-400",
  doğum: "border-emerald-900 text-emerald-400",
  evlilik: "border-pink-900 text-pink-300",
  tahta_çıkış: "border-amber-900 text-amber-400",
  savaş_ilanı: "border-red-900 text-red-400",
  barış: "border-emerald-900 text-emerald-300",
  isyan: "border-red-900 text-red-300",
  başlangıç: "border-orange-900 text-orange-400",
  ticaret: "border-stone-700 text-stone-400",
};

export default function Chronicle() {
  const { state } = useGame();
  const events = [...(state.history || [])].reverse();

  return (
    <div className="space-y-6 rise-in">
      <div>
        <div className="label-tiny">Tarih</div>
        <h1 className="font-heading text-3xl text-stone-100 flex items-center gap-3">
          <ScrollText className="w-7 h-7 text-orange-600" /> Küllerin Kroniği
        </h1>
      </div>
      <div className="space-y-2 max-w-3xl">
        {events.map((e) => (
          <div key={e.id} className="card-frame px-4 py-3 flex gap-3 items-start" data-testid={`event-${e.id}`}>
            <div className="shrink-0 w-16 text-right">
              <div className="label-tiny">Gün</div>
              <div className="text-stone-200 font-heading">{e.day}</div>
            </div>
            <div className="flex-1">
              <span className={`text-xs px-2 py-0.5 border rounded-sm font-heading tracking-wider ${TYPE_COLOR[e.type] || "border-stone-700 text-stone-400"}`}>
                {TYPE_LABEL[e.type] || e.type}
              </span>
              <div className="text-sm text-stone-200 mt-1.5">{e.text}</div>
            </div>
          </div>
        ))}
        {events.length === 0 && <div className="text-stone-500">Henüz tarih yazılmadı.</div>}
      </div>
    </div>
  );
}
