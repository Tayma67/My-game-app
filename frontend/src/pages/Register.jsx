import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/AuthContext";
import { extractErrorMessage } from "@/lib/api";
import { Flame } from "lucide-react";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(email, password, name);
      navigate("/oyun");
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-stone-950">
      <div className="absolute inset-0 bg-gradient-to-b from-stone-950 via-stone-900 to-stone-950" />
      <div className="relative z-10 flex min-h-screen items-center justify-center p-6">
        <div className="card-frame w-full max-w-md p-8 rise-in">
          <div className="flex items-center gap-3 mb-6">
            <Flame className="w-7 h-7 text-orange-600 ember-flicker" />
            <div>
              <div className="label-tiny">Yeni Yolculuk</div>
              <h1 className="font-heading text-2xl text-stone-100">Hesap Aç</h1>
            </div>
          </div>
          <div className="divider-ash mb-6" />
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="label-tiny block mb-2">İsim</label>
              <input
                required
                data-testid="register-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-stone-950 border border-stone-800 px-3 py-2 text-stone-200 focus:border-orange-700 outline-none rounded-sm"
              />
            </div>
            <div>
              <label className="label-tiny block mb-2">E-Posta</label>
              <input
                type="email"
                required
                data-testid="register-email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-stone-950 border border-stone-800 px-3 py-2 text-stone-200 focus:border-orange-700 outline-none rounded-sm"
              />
            </div>
            <div>
              <label className="label-tiny block mb-2">Şifre (en az 6 karakter)</label>
              <input
                type="password"
                required
                minLength={6}
                data-testid="register-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-stone-950 border border-stone-800 px-3 py-2 text-stone-200 focus:border-orange-700 outline-none rounded-sm"
              />
            </div>
            {error && (
              <div className="text-sm text-red-400 border border-red-900/60 px-3 py-2 rounded-sm bg-red-950/30" data-testid="register-error">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={busy}
              data-testid="register-submit"
              className="w-full btn-ember py-2.5 font-heading tracking-widest text-sm disabled:opacity-50"
            >
              {busy ? "OLUŞTURULUYOR…" : "MUHRÜ KAZI"}
            </button>
          </form>
          <div className="mt-6 text-center text-sm text-stone-400">
            Zaten hesabın var mı?{" "}
            <Link to="/giris" data-testid="register-login-link" className="text-orange-500 hover:text-orange-400">
              Giriş Yap
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
