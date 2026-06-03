import { createContext, useContext, useState, useCallback } from "react";
import { api } from "@/lib/api";

const GameContext = createContext(null);

export function GameProvider({ children }) {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchState = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/game/state");
      setState(data);
      return data;
    } catch (e) {
      if (e?.response?.status === 404) {
        setState(false);
        return null;
      }
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const newGame = useCallback(async () => {
    const { data } = await api.post("/game/new");
    setState(data);
    return data;
  }, []);

  const deleteGame = useCallback(async () => {
    await api.delete("/game/state");
    setState(false);
  }, []);

  const advance = useCallback(async (days = 7) => {
    const { data } = await api.post(`/game/advance?days=${days}`);
    setState(data);
    return data;
  }, []);

  const action = useCallback(async (path, body = null) => {
    const { data } = await api.post(path, body);
    if (data?.state) {
      setState(data.state);
      return data;
    }
    if (data && data.world) {
      setState(data);
    }
    return data;
  }, []);

  return (
    <GameContext.Provider
      value={{ state, setState, loading, fetchState, newGame, deleteGame, advance, action }}
    >
      {children}
    </GameContext.Provider>
  );
}

export const useGame = () => useContext(GameContext);
