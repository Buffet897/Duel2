import { Link } from "react-router-dom";
import Shell from "@/components/Shell";
import { useT } from "@/lib/i18n";

const NotFound = () => {
  const { t } = useT();
  return (
    <Shell>
      <div className="pt-16 text-center">
        <div className="text-6xl font-display font-bold text-[#7F77DD]">404</div>
        <h1 className="mt-3 text-xl font-semibold text-gray-950">
          {t("common.not_found_title")}
        </h1>
        <p className="mt-2 text-sm text-gray-500">{t("common.not_found_body")}</p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center justify-center w-full bg-[#7F77DD] text-white py-3 rounded-full font-medium hover:bg-[#6B62D6] transition"
        >
          {t("duel.back_home")}
        </Link>
      </div>
    </Shell>
  );
};

export default NotFound;
