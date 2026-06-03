import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("kkm_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function formatApiErrorDetail(detail) {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : null))
      .filter(Boolean);
    if (msgs.length === 0) return null;
    return msgs.join(" ");
  }
  if (detail && typeof detail.msg === "string") return detail.msg;
  try {
    return JSON.stringify(detail);
  } catch {
    return null;
  }
}

export function extractErrorMessage(e) {
  // Prefer FastAPI's `detail`, fall back to axios message, then a generic
  const fromDetail = formatApiErrorDetail(e?.response?.data?.detail);
  if (fromDetail) return fromDetail;
  if (e?.response?.status === 401) return "E-posta veya şifre hatalı";
  if (e?.response?.status === 403) return "Bu eylem için yetkin yok";
  if (e?.response?.status >= 500) return "Sunucu hatası. Lütfen birazdan tekrar dene.";
  if (e?.message === "Network Error") return "Ağ hatası — bağlantıyı kontrol et.";
  if (e?.message) return e.message;
  return "Beklenmedik bir hata oluştu.";
}
