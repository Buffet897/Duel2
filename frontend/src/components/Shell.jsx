import { Link } from "react-router-dom";

export const Shell = ({ children, hideFooter = false }) => (
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
        + Nieuw duel
      </Link>
    </header>
    <main className="flex-1 px-5 pb-24">{children}</main>
    {!hideFooter && (
      <footer className="px-5 py-6 border-t border-gray-100 text-xs text-gray-400 flex items-center justify-between">
        <span>© {new Date().getFullYear()} OutfitDuel</span>
        <Link to="/privacy" className="underline-offset-4 hover:underline" data-testid="footer-privacy-link">
          Privacybeleid
        </Link>
      </footer>
    )}
  </div>
);

export default Shell;
