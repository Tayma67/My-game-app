import { useEffect, useState } from "react";
import { useGame } from "@/lib/GameContext";
import { useNavigate } from "react-router-dom";
import { Flame, Loader2 } from "lucide-react";

export default function NewGame() {
  const { state, fetchState, newGame } = useGame();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  useEffect(() => {
    if (state && state.world) navigate("/oyun");
  }, [state, navigate]);

  const start = async () => {
    setBusy(true);
    try {
      await newGame();
      navigate("/oyun");
    } finally {
      setBusy(false);
    }
  };

  if (state === null) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-500">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-950 flex items-center justify-center p-6">
      <div className="card-frame max-w-2xl w-full p-10 rise-in">
        <div className="flex items-center gap-3 mb-6">
          <Flame className="w-8 h-8 text-orange-600 ember-flicker" />
          <h1 className="font-heading text-3xl text-stone-100">Yeni Yolculuk</h1>
        </div>
        <div className="divider-ash mb-6" />
        <p className="text-stone-300 leading-relaxed mb-4">
          Bu, kahramanların değil <span className="text-orange-400">çocukların</span> hikâyesi.
          Yedi yaşındasın. Külleri savrulmuş bu dünyada bir köyde annenle babanın yanında
          doğdun. Zayıf bir kolun, küçük bir aklın var; üstünde köylü giysisi, heybende
          iki dilim ekmek. Hayat seni bekliyor.
        </p>
        <p className="text-stone-300 leading-relaxed mb-4">
          1 tur = 1 hafta. 48 hafta sonra bir yaş büyüyeceksin.
          Her kış sandığın incelecek, her yaz tarlalar dolacak. Aç kalırsan zayıflarsın,
          aç bırakmazsan büyürsün. Çocukken yaptığın her şey —ne kadar tahta sopa salladığın,
          kaç kez pazarda pazarlık ettiğin— büyüyünce <span className="text-amber-400">kalıcı statlara</span> dönüşecek.
        </p>
        <p className="text-stone-400 italic text-sm mb-8">
          13 yaşında dünya sana açılacak: meslek, savaş, ticaret, evlilik. O zamana kadar
          ailenin görevleri yolun olsun.
        </p>
        <button
          onClick={start}
          disabled={busy}
          data-testid="new-game-start"
          className="btn-ember px-8 py-3 font-heading tracking-widest text-sm disabled:opacity-50"
        >
          {busy ? "DÜNYA YARATILIYOR…" : "DÜNYAYI YARAT"}
        </button>
      </div>
    </div>
  );
}
