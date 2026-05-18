import { Link } from "react-router-dom";
import { useT } from "@/lib/i18n";

const LanguageSwitch = () => {
  const { lang, setLang } = useT();
  const change = (next) => () => {
    if (lang === next) return;
    setLang(next);
    // Reload so any server-rendered fragments (OG, etc.) pick up the change.
    setTimeout(() => window.location.reload(), 80);
  };
  const cls = (active) =>
    active
      ? "text-gray-900 font-semibold cursor-default"
      : "text-gray-400 hover:text-gray-600 transition";
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] tracking-wider" data-testid="language-switch">
      <button
        type="button"
        onClick={change("nl")}
        aria-pressed={lang === "nl"}
        className={cls(lang === "nl")}
        data-testid="lang-nl"
      >
        NL
      </button>
      <span className="text-gray-300">|</span>
      <button
        type="button"
        onClick={change("en")}
        aria-pressed={lang === "en"}
        className={cls(lang === "en")}
        data-testid="lang-en"
      >
        EN
      </button>
    </span>
  );
};

export const Shell = ({ children, hideFooter = false }) => {
  const { t } = useT();
  return (
    <div className="od-shell flex flex-col" data-testid="app-shell">
      <header className="px-5 pt-5 pb-3 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2" data-testid="brand-link">
          <span className="inline-block h-7 w-7 rounded-full bg-[#7F77DD]" aria-hidden />
          <span className="font-display font-bold text-lg tracking-tight text-gray-950">
            OutfitDuel
          </span>
        </Link>
        <Link
          to="/nieuw"
          className="text-sm font-medium text-[#7F77DD] hover:text-[#6B62D6] transition"
          data-testid="header-new-duel-link"
        >
          {t("header.new_duel")}
        </Link>
      </header>
      <main className="flex-1 px-5 pb-24">{children}</main>
      {!hideFooter && (
        <footer className="px-5 py-6 border-t border-gray-100 text-xs text-gray-400 flex items-center justify-between gap-3 flex-wrap">
          <span>{t("footer.copyright", { year: new Date().getFullYear() })}</span>
          <div className="flex items-center gap-4">
            <Link to="/voorwaarden" className="underline-offset-4 hover:underline" data-testid="footer-terms-link">
              {t("footer.terms")}
            </Link>
            <Link to="/privacy" className="underline-offset-4 hover:underline" data-testid="footer-privacy-link">
              {t("footer.privacy")}
            </Link>
            <LanguageSwitch />
          </div>
        </footer>
      )}
    </div>
  );
};

export default Shell;
