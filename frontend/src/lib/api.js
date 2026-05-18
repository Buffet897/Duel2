import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

function readCookie(name) {
  if (typeof document === "undefined") return null;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Inject Accept-Language header from the od_lang cookie so the backend can
// localise emails, OG previews and (future) flash messages.
api.interceptors.request.use((config) => {
  const lang = readCookie("od_lang");
  if (lang === "nl" || lang === "en") {
    config.headers = config.headers || {};
    config.headers["Accept-Language"] = lang;
  }
  return config;
});

export function buildAssetUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${BACKEND_URL}${path}`;
}
