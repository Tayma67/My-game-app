import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/AuthContext";
import { extractErrorMessage } from "@/lib/api";
import { Flame } from "lucide-react";

const BG_IMG =
  "https://images.unsplash.com/photo-1570374953872-7ede4492beb1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwzfHxidXJuaW5nJTIwZW1iZXJzJTIwZGFya3xlbnwwfHx8fDE3ODA0ODMzNTB8MA&ixlib=rb-4.1.0&q=85";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate("/oyun");
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${BG_IMG})` }}
      />
      <div className="absolute inset-0 bg-stone-950/85" />
      <div className="relative z-10 flex min-h-screen items-center justify-center p-6">
        <div className="card-frame w-full max-w-md p-8 rise-in">
          <div className="flex items-center gap-3 mb-6">
            <Flame className="w-7 h-7 text-orange-600 ember-flicker" />
            <div>
              <div className="label-tiny">Kronikler</div>
              <h1 className="font-heading text-2xl text-stone-100">Küllerin Mirası</h1>
            </div>
          </div>
          <div className="divider-ash mb-6" />
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="label-tiny block mb-2">E-Posta</label>
              <input
                type="email"
                required
                data-testid="login-email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-stone-950 border border-stone-800 px-3 py-2 text-stone-200 focus:border-orange-700 outline-none rounded-sm"
                placeholder="ornek@kül.org"
              />
            </div>
            <div>
              <label className="label-tiny block mb-2">Şifre</label>
              <input
                type="password"
                required
                data-testid="login-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-stone-950 border border-stone-800 px-3 py-2 text-stone-200 focus:border-orange-700 outline-none rounded-sm"
                placeholder="••••••"
              />
            </div>
            {error && (
              <div className="text-sm text-red-400 border border-red-900/60 px-3 py-2 rounded-sm bg-red-950/30" data-testid="login-error">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={busy}
              data-testid="login-submit"
              className="w-full btn-ember py-2.5 font-heading tracking-widest text-sm disabled:opacity-50"
            >
              {busy ? "GİRİŞ YAPILIYOR…" : "ATEŞİ TUTUŞTUR"}
            </button>
          </form>
          <div className="mt-6 text-center text-sm text-stone-400">
            Henüz hesabın yok mu?{" "}
            <Link to="/kayit" data-testid="login-register-link" className="text-orange-500 hover:text-orange-400">
              Kayıt Ol
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
