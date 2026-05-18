import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import nl from "@/locales/nl.json";
import en from "@/locales/en.json";

const STRINGS = { nl, en };
const COOKIE_NAME = "od_lang";

function readCookie(name) {
  if (typeof document === "undefined") return null;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function writeCookie(name, value, days = 365) {
  const exp = new Date();
  exp.setTime(exp.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value}; expires=${exp.toUTCString()}; path=/; SameSite=Lax`;
}

function detectInitialLang() {
  if (typeof window === "undefined") return "nl";
  const fromCookie = readCookie(COOKIE_NAME);
  if (fromCookie === "nl" || fromCookie === "en") return fromCookie;
  const nav = (navigator.language || "en").toLowerCase();
  return nav.startsWith("nl") ? "nl" : "en";
}

function resolveDotted(obj, path) {
  return path.split(".").reduce((acc, key) => (acc == null ? undefined : acc[key]), obj);
}

const LanguageContext = createContext({
  lang: "nl",
  setLang: () => {},
  t: (k) => k,
});

export const LanguageProvider = ({ children }) => {
  const [lang, setLangState] = useState(detectInitialLang);

  // Persist cookie at first render so backend can see it on subsequent requests
  useEffect(() => {
    if (readCookie(COOKIE_NAME) !== lang) {
      writeCookie(COOKIE_NAME, lang);
    }
    if (typeof document !== "undefined" && document.documentElement) {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  const setLang = useCallback((next) => {
    if (next !== "nl" && next !== "en") return;
    writeCookie(COOKIE_NAME, next);
    setLangState(next);
  }, []);

  const t = useCallback(
    (key, vars) => {
      const dict = STRINGS[lang] || STRINGS.en;
      const value = resolveDotted(dict, key);
      if (value == null) return key;
      if (typeof value === "string" && vars) {
        return Object.entries(vars).reduce(
          (acc, [k, v]) => acc.replace(new RegExp(`\\{${k}\\}`, "g"), String(v)),
          value,
        );
      }
      return value;
    },
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useT = () => useContext(LanguageContext);

export function votesLabel(count, t) {
  return count === 1 ? t("duel.vote_count_singular") : t("duel.votes_count");
}
