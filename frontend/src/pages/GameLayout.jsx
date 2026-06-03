import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/AuthContext";
import { useGame } from "@/lib/GameContext";
import {
  Map, User, Backpack, Users, Scroll, ListChecks,
  Sword, Heart, LogOut, Flame, Hourglass, Loader2, Sparkles,
} from "lucide-react";
import { toast, Toaster } from "sonner";

const NAV = [
  { to: "/oyun", label: "Dünya", icon: Map, end: true, testid: "nav-world" },
  { to: "/oyun/karakter", label: "Karakter", icon: User, testid: "nav-character" },
  { to: "/oyun/envanter", label: "Envanter", icon: Backpack, testid: "nav-inventory" },
  { to: "/oyun/npcler", label: "NPC'ler", icon: Users, testid: "nav-npcs" },
  { to: "/oyun/iliskiler", label: "İlişkiler", icon: Heart, testid: "nav-relations" },
  { to: "/oyun/gorevler", label: "Görevler", icon: ListChecks, testid: "nav-quests" },
  { to: "/oyun/savas", label: "Savaş", icon: Sword, testid: "nav-battle" },
  { to: "/oyun/tarih", label: "Tarih", icon: Scroll, testid: "nav-history" },
];

function NavItem({ to, label, icon: Icon, end, testid }) {
  return (
    <NavLink
      to={to}
      end={end}
      data-testid={testid}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-sm border transition-all ${
          isActive
            ? "border-orange-800 bg-stone-900 text-orange-400"
            : "border-transparent text-stone-400 hover:text-stone-200 hover:bg-stone-900/60"
        }`
      }
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span className="text-sm font-heading tracking-wider">{label}</span>
    </NavLink>
  );
}

function MobileNavItem({ to, label, icon: Icon, end, testid }) {
  return (
    <NavLink
      to={to}
      end={end}
      data-testid={`m-${testid}`}
      className={({ isActive }) =>
        `flex flex-col items-center gap-0.5 px-2 py-1.5 ${
          isActive ? "text-orange-400" : "text-stone-500"
        }`
      }
    >
      <Icon className="w-5 h-5" />
      <span className="text-[10px] tracking-wider">{label}</span>
    </NavLink>
  );
}

export default function GameLayout() {
  const { user, logout } = useAuth();
  const { state, fetchState, advance } = useGame();
  const navigate = useNavigate();
  const [advancing, setAdvancing] = useState(false);

  useEffect(() => {
    fetchState().then((s) => {
      if (s === null) navigate("/yeni-oyun");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onAdvance = async (days) => {
    setAdvancing(true);
    try {
      await advance(days);
      toast.success(`${days} gün geçti.`);
    } catch (e) {
      toast.error("Zaman ilerletilemedi.");
    } finally {
      setAdvancing(false);
    }
  };

  if (!state || !state.world) {
    return (
      <div className="min-h-screen flex items-center justify-center text-stone-500 bg-stone-950">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  const player = state.player;
  return (
    <div className="min-h-screen bg-stone-950 text-stone-200 flex">
      <div className="grain-overlay" />
      <Toaster theme="dark" position="top-center" />
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col w-64 border-r border-stone-800 bg-stone-950 p-4 sticky top-0 h-screen z-10">
        <div className="flex items-center gap-2 mb-6">
          <Flame className="w-6 h-6 text-orange-600 ember-flicker" />
          <div>
            <div className="label-tiny">Kronikler</div>
            <div className="font-heading text-lg text-stone-100 leading-tight">Küllerin Mirası</div>
          </div>
        </div>
        <div className="card-frame p-3 mb-4 text-xs">
          <div className="label-tiny mb-1">Oyuncu</div>
          <div className="font-heading text-stone-100 text-sm" data-testid="layout-player-name">{player.name}</div>
          <div className="text-stone-500">{player.profession} · {player.age}</div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <div>
              <div className="label-tiny">Altın</div>
              <div className="text-amber-400 font-semibold" data-testid="layout-money">{player.money}</div>
            </div>
            <div>
              <div className="label-tiny">Sağlık</div>
              <div className="text-emerald-400 font-semibold">{player.health}</div>
            </div>
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((n) => <NavItem key={n.to} {...n} />)}
        </nav>
        <div className="divider-ash my-4" />
        <button
          onClick={() => onAdvance(7)}
          disabled={advancing}
          data-testid="advance-week"
          className="btn-ember w-full py-2 font-heading text-xs tracking-widest mb-2 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Hourglass className="w-4 h-4" />
          {advancing ? "GEÇİYOR…" : "BİR HAFTA GEÇ"}
        </button>
        <button
          onClick={() => onAdvance(1)}
          disabled={advancing}
          data-testid="advance-day"
          className="btn-ghost-ash w-full py-2 font-heading text-xs tracking-widest disabled:opacity-50"
        >
          BİR GÜN GEÇ
        </button>
        <div className="mt-auto pt-4 text-xs">
          <div className="text-stone-600 mb-2">
            Gün <span className="text-stone-300" data-testid="layout-day">{state.day}</span> · {user?.email}
          </div>
          <button
            onClick={logout}
            data-testid="logout-button"
            className="flex items-center gap-2 text-stone-500 hover:text-stone-300 text-xs"
          >
            <LogOut className="w-3 h-3" /> Çıkış
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 relative z-[2] pb-24 lg:pb-6">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-20 bg-stone-950/90 backdrop-blur border-b border-stone-800 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="w-5 h-5 text-orange-600 ember-flicker" />
            <div>
              <div className="font-heading text-sm text-stone-100" data-testid="mobile-player-name">{player.name}</div>
              <div className="text-[10px] text-stone-500 uppercase tracking-wider">
                {player.profession} · Gün {state.day} · {player.money}A
              </div>
            </div>
          </div>
          <button
            onClick={() => onAdvance(7)}
            disabled={advancing}
            data-testid="mobile-advance-week"
            className="btn-ember px-3 py-1.5 text-xs font-heading tracking-wider disabled:opacity-50 flex items-center gap-1.5"
          >
            <Hourglass className="w-3.5 h-3.5" />
            {advancing ? "…" : "HAFTA"}
          </button>
        </header>
        <div className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-30 border-t border-stone-800 bg-stone-950/95 backdrop-blur grid grid-cols-8">
        {NAV.map((n) => <MobileNavItem key={n.to} {...n} />)}
      </nav>
    </div>
  );
}
