import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/AuthContext";
import { GameProvider } from "@/lib/GameContext";
import { Loader2 } from "lucide-react";
import "@/App.css";

import Login from "@/pages/Login";
import Register from "@/pages/Register";
import NewGame from "@/pages/NewGame";
import GameLayout from "@/pages/GameLayout";
import WorldMap from "@/pages/WorldMap";
import CityDetail from "@/pages/CityDetail";
import CharacterSheet from "@/pages/CharacterSheet";
import Inventory from "@/pages/Inventory";
import NPCList from "@/pages/NPCList";
import NPCDetail from "@/pages/NPCDetail";
import Relationships from "@/pages/Relationships";
import Chronicle from "@/pages/Chronicle";
import Quests from "@/pages/Quests";
import Battle from "@/pages/Battle";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading || user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-stone-950 text-stone-500">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/giris" replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/oyun" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <GameProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/oyun" replace />} />
            <Route path="/giris" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/kayit" element={<PublicOnly><Register /></PublicOnly>} />
            <Route path="/yeni-oyun" element={<Protected><NewGame /></Protected>} />
            <Route path="/oyun" element={<Protected><GameLayout /></Protected>}>
              <Route index element={<WorldMap />} />
              <Route path="sehir/:id" element={<CityDetail />} />
              <Route path="karakter" element={<CharacterSheet />} />
              <Route path="envanter" element={<Inventory />} />
              <Route path="npcler" element={<NPCList />} />
              <Route path="npc/:id" element={<NPCDetail />} />
              <Route path="iliskiler" element={<Relationships />} />
              <Route path="tarih" element={<Chronicle />} />
              <Route path="gorevler" element={<Quests />} />
              <Route path="savas" element={<Battle />} />
            </Route>
            <Route path="*" element={<Navigate to="/oyun" replace />} />
          </Routes>
        </GameProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
