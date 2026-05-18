import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cookie } from "lucide-react";
import { useT } from "@/lib/i18n";

const COOKIE_NAME = "od_cookie_consent";

function readCookie(name) {
  if (typeof document === "undefined") return null;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function setCookie(name, value, days) {
  const exp = new Date();
  exp.setTime(exp.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value}; expires=${exp.toUTCString()}; path=/; SameSite=Lax`;
}

const CookieBanner = () => {
  const { t } = useT();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (readCookie(COOKIE_NAME) === "1") return;
    const t2 = setTimeout(() => setVisible(true), 600);
    return () => clearTimeout(t2);
  }, []);

  const accept = () => {
    setCookie(COOKIE_NAME, "1", 365);
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-3 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-1.5rem)] max-w-md"
      data-testid="cookie-banner"
      role="region"
      aria-label="Cookie notice"
    >
      <div className="rounded-2xl bg-white border border-gray-100 shadow-[0_8px_32px_rgba(0,0,0,0.12)] px-4 py-3 flex items-center gap-3">
        <div className="hidden sm:flex h-9 w-9 shrink-0 rounded-full bg-[#F2F1FA] items-center justify-center">
          <Cookie className="h-4 w-4 text-[#7F77DD]" />
        </div>
        <p className="text-[12px] leading-snug text-gray-700 flex-1">
          {t("cookie.message")}{" "}
          <Link to="/privacy" className="text-[#7F77DD] underline-offset-4 hover:underline">
            {t("cookie.privacy_link")}
          </Link>
          .
        </p>
        <button
          type="button"
          onClick={accept}
          data-testid="cookie-banner-accept"
          className="shrink-0 bg-[#7F77DD] hover:bg-[#6B62D6] text-white text-xs font-semibold px-4 py-2 rounded-full transition active:scale-[0.98]"
        >
          {t("cookie.accept")}
        </button>
      </div>
    </div>
  );
};

export default CookieBanner;
