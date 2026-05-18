import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Download, Share2, Image as ImageIcon, Hash, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { toPng } from "html-to-image";
import Shell from "@/components/Shell";
import { api, buildAssetUrl } from "@/lib/api";
import { useT, votesLabel } from "@/lib/i18n";

const CardCanvas = ({ duel, pctA, pctB, totalVotes, includePhotos, size, refEl, t }) => {
  const dims =
    size === "story" ? { w: 1080, h: 1920 } : { w: 1080, h: 1080 };
  const winA = pctA >= pctB;
  const pctWin = winA ? pctA : pctB;
  const pctLose = winA ? pctB : pctA;
  return (
    <div
      ref={refEl}
      style={{
        width: `${dims.w}px`,
        height: `${dims.h}px`,
        background: "#FFFFFF",
        position: "absolute",
        left: "-99999px",
        top: 0,
        padding: size === "story" ? "80px" : "64px",
        display: "flex",
        flexDirection: "column",
        fontFamily: "Outfit, Inter, sans-serif",
        color: "#050505",
        overflow: "hidden",
      }}
    >
      <div style={{ fontSize: 36, color: "#7F77DD", fontWeight: 700, letterSpacing: -0.5 }}>
        OutfitDuel
      </div>
      <div style={{ marginTop: 36, fontSize: size === "story" ? 64 : 52, fontWeight: 700, lineHeight: 1.1 }}>
        {duel.question || t("result.default_question")}
      </div>

      {includePhotos && (
        <div
          style={{
            marginTop: 60,
            display: "grid",
            gridTemplateColumns: size === "story" ? "1fr" : "1fr 1fr",
            gridTemplateRows: size === "story" ? "1fr 1fr" : "1fr",
            gap: 24,
            flex: 1,
            minHeight: 0,
          }}
        >
          {[
            { letter: "A", src: duel.photo_a_url, pct: pctA, isWin: winA },
            { letter: "B", src: duel.photo_b_url, pct: pctB, isWin: !winA },
          ].map((s) => (
            <div
              key={s.letter}
              style={{
                position: "relative",
                borderRadius: 32,
                overflow: "hidden",
                border: s.isWin ? "8px solid #7F77DD" : "4px solid #E5E5E5",
                background: "#FAFAFA",
              }}
            >
              <img
                src={s.src}
                alt={s.letter}
                crossOrigin="anonymous"
                style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              />
              <div
                style={{
                  position: "absolute",
                  bottom: 24,
                  left: 24,
                  background: s.isWin ? "#7F77DD" : "rgba(0,0,0,0.7)",
                  color: "#FFFFFF",
                  padding: "16px 28px",
                  borderRadius: 999,
                  fontSize: 48,
                  fontWeight: 700,
                }}
              >
                {s.pct}% · {s.letter}
              </div>
            </div>
          ))}
        </div>
      )}

      {!includePhotos && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", textAlign: "center" }}>
          <div style={{ fontSize: size === "story" ? 220 : 180, fontWeight: 800, color: "#7F77DD", lineHeight: 1 }}>
            {pctWin}%
          </div>
          <div style={{ marginTop: 24, fontSize: 56, fontWeight: 600 }}>
            {t("result.winner_chose")} {winA ? "A" : "B"}
          </div>
          <div style={{ marginTop: 16, fontSize: 36, color: "#A3A3A3" }}>
            vs {pctLose}% · {totalVotes} {votesLabel(totalVotes, t)}
          </div>
        </div>
      )}

      {includePhotos && (
        <div style={{ marginTop: 40, fontSize: 48, fontWeight: 700, color: "#050505" }}>
          {pctWin}% {t("result.winner_chose")} {winA ? "A" : "B"}
          <span style={{ fontSize: 30, color: "#A3A3A3", fontWeight: 500, marginLeft: 16 }}>
            · {totalVotes} {votesLabel(totalVotes, t)}
          </span>
        </div>
      )}

      <div style={{ marginTop: 32, fontSize: 28, color: "#A3A3A3", letterSpacing: 1 }}>
        outfitduel.com
      </div>
    </div>
  );
};

const Result = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { t } = useT();
  const [duel, setDuel] = useState(null);
  const [withPhotos, setWithPhotos] = useState(true);
  const [size, setSize] = useState("story");
  const [error, setError] = useState(null);
  const [ownToken, setOwnToken] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const storyPhotoRef = useRef(null);
  const storyCleanRef = useRef(null);
  const feedPhotoRef = useRef(null);
  const feedCleanRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get(`/duels/${id}`);
        setDuel(data);
      } catch (err) {
        setError(err?.response?.status === 404 ? "not_found" : "error");
      }
      try {
        const owned = JSON.parse(localStorage.getItem("od_owned") || "{}");
        if (owned[id]?.delete_token) setOwnToken(owned[id].delete_token);
      } catch (_) {}
    })();
  }, [id]);

  const totalVotes = duel ? duel.votes_a + duel.votes_b : 0;
  const pctA = duel ? (totalVotes === 0 ? 50 : Math.round((duel.votes_a / totalVotes) * 100)) : 50;
  const pctB = 100 - pctA;

  const preparedDuel = useMemo(() => {
    if (!duel) return null;
    return {
      ...duel,
      photo_a_url: buildAssetUrl(duel.photo_a_url),
      photo_b_url: buildAssetUrl(duel.photo_b_url),
    };
  }, [duel]);

  const download = async () => {
    if (!duel) return;
    const node =
      size === "story"
        ? (withPhotos ? storyPhotoRef.current : storyCleanRef.current)
        : (withPhotos ? feedPhotoRef.current : feedCleanRef.current);
    if (!node) return;
    try {
      // Refresh counts before exporting
      try {
        const { data } = await api.get(`/duels/${id}/count`);
        setDuel((d) => (d ? { ...d, votes_a: data.votes_a, votes_b: data.votes_b } : d));
      } catch (_) {}
      const dataUrl = await toPng(node, {
        cacheBust: true,
        pixelRatio: 1,
        skipFonts: false,
      });
      const link = document.createElement("a");
      const filename = `outfitduel-${id}-${size}.png`;
      link.download = filename;
      link.href = dataUrl;
      // iOS Safari fallback
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      if (isIOS) {
        window.open(dataUrl, "_blank");
      } else {
        link.click();
      }
      toast.success(t("card.downloaded"));
    } catch (err) {
      toast.error(t("card.download_failed"));
      // eslint-disable-next-line no-console
      console.error(err);
    }
  };

  const shareWhatsapp = () => {
    const text = encodeURIComponent(
      `${t("result.share_text")}\n${window.location.origin}/duel/${id}/resultaat`,
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };

  const deleteDuel = async () => {
    if (!ownToken) return;
    if (!window.confirm(t("result.delete_confirm"))) return;
    setDeleting(true);
    try {
      await api.delete(`/duels/${id}`, { params: { token: ownToken } });
      try {
        const owned = JSON.parse(localStorage.getItem("od_owned") || "{}");
        delete owned[id];
        localStorage.setItem("od_owned", JSON.stringify(owned));
      } catch (_) {}
      toast.success(t("result.deleted"));
      nav("/");
    } catch (err) {
      toast.error(t("errors.delete_failed"));
    } finally {
      setDeleting(false);
    }
  };

  if (error === "not_found") {
    return (
      <Shell>
        <div className="pt-12 text-center">
          <h1 className="text-2xl font-bold text-gray-950">{t("common.not_found_title")}</h1>
          <button onClick={() => nav("/")} className="mt-6 w-full bg-[#7F77DD] text-white py-3 rounded-full font-medium">
            {t("duel.back_home")}
          </button>
        </div>
      </Shell>
    );
  }
  if (!duel || !preparedDuel) {
    return (
      <Shell>
        <div className="pt-12 text-center text-gray-400">{t("common.loading")}</div>
      </Shell>
    );
  }

  const winA = pctA >= pctB;
  const pctWin = winA ? pctA : pctB;

  return (
    <Shell>
      <h1 className="text-2xl font-bold tracking-tight text-gray-950">
        {duel.is_expired ? t("result.title_final") : t("result.title_running")}
      </h1>
      <p className="mt-1 text-sm text-gray-600">
        {duel.question || t("result.default_question")}
      </p>

      <div className="mt-5 rounded-2xl bg-[#F2F1FA] p-5 text-center">
        <div className="text-5xl font-display font-bold text-[#7F77DD]" data-testid="result-headline-pct">
          {pctWin}%
        </div>
        <div className="text-base text-gray-700 mt-1">
          {t("result.winner_chose")} {winA ? "A" : "B"}
        </div>
        <div className="text-xs text-gray-500 mt-1" data-testid="result-vote-count">
          · {totalVotes} {votesLabel(totalVotes, t)}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        {[
          { letter: "A", pct: pctA, src: duel.photo_a_url, isWin: winA, votes: duel.votes_a },
          { letter: "B", pct: pctB, src: duel.photo_b_url, isWin: !winA, votes: duel.votes_b },
        ].map((s) => (
          <div key={s.letter} className="relative">
            <div className={`aspect-[3/4] rounded-2xl overflow-hidden border-2 ${s.isWin ? "border-[#7F77DD]" : "border-gray-100"}`}>
              <img src={buildAssetUrl(s.src)} alt={s.letter} className="w-full h-full object-cover" />
            </div>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-display font-bold text-gray-900">{s.pct}% · {s.letter}</span>
              <span className="text-xs text-gray-500">{s.votes}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-display font-semibold text-gray-900">{t("result.share_card_title")}</h2>
        <p className="mt-1 text-sm text-gray-500">{t("result.share_card_subtitle")}</p>

        <div className="mt-4 inline-flex p-1 bg-gray-100 rounded-full" role="tablist">
          <button
            type="button"
            onClick={() => setWithPhotos(true)}
            data-testid="toggle-with-photos"
            className={`px-4 py-1.5 text-sm font-medium rounded-full transition ${withPhotos ? "bg-white shadow text-gray-900" : "text-gray-500"}`}
          >
            <ImageIcon className="h-3.5 w-3.5 inline mr-1.5" /> {t("card.toggle_with_photos")}
          </button>
          <button
            type="button"
            onClick={() => setWithPhotos(false)}
            data-testid="toggle-only-result"
            className={`px-4 py-1.5 text-sm font-medium rounded-full transition ${!withPhotos ? "bg-white shadow text-gray-900" : "text-gray-500"}`}
          >
            <Hash className="h-3.5 w-3.5 inline mr-1.5" /> {t("card.toggle_without_photos")}
          </button>
        </div>

        <div className="mt-3 inline-flex p-1 bg-gray-100 rounded-full ml-2" role="tablist">
          <button
            type="button"
            onClick={() => setSize("story")}
            data-testid="toggle-size-story"
            className={`px-4 py-1.5 text-sm font-medium rounded-full transition ${size === "story" ? "bg-white shadow text-gray-900" : "text-gray-500"}`}
          >
            {t("card.download_stories")}
          </button>
          <button
            type="button"
            onClick={() => setSize("feed")}
            data-testid="toggle-size-feed"
            className={`px-4 py-1.5 text-sm font-medium rounded-full transition ${size === "feed" ? "bg-white shadow text-gray-900" : "text-gray-500"}`}
          >
            {t("card.download_feed")}
          </button>
        </div>

        {/* Preview (visible, scaled) */}
        <div className="mt-4 rounded-2xl overflow-hidden border border-gray-100 bg-white">
          <PreviewCard
            duel={preparedDuel}
            includePhotos={withPhotos}
            pctA={pctA}
            pctB={pctB}
            totalVotes={totalVotes}
            size={size}
            t={t}
          />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            onClick={download}
            data-testid="download-card-button"
            className="inline-flex items-center justify-center gap-1.5 bg-[#7F77DD] text-white py-3 rounded-full font-medium hover:bg-[#6B62D6] transition"
          >
            <Download className="h-4 w-4" /> {t("result.download")}
          </button>
          <button
            onClick={shareWhatsapp}
            data-testid="share-result-whatsapp"
            className="inline-flex items-center justify-center gap-1.5 bg-[#25D366] text-white py-3 rounded-full font-medium hover:opacity-95 transition"
          >
            <Share2 className="h-4 w-4" /> {t("result.share_whatsapp")}
          </button>
        </div>
      </div>

      {ownToken && (
        <button
          onClick={deleteDuel}
          disabled={deleting}
          data-testid="delete-duel-button"
          className="mt-8 w-full inline-flex items-center justify-center gap-1.5 text-red-500 text-sm font-medium hover:text-red-600 transition"
        >
          <Trash2 className="h-4 w-4" /> {t("result.delete_button")}
        </button>
      )}

      {/* Off-screen canvases for ALL four variants — instant toggle, no recompute */}
      <CardCanvas duel={preparedDuel} pctA={pctA} pctB={pctB} totalVotes={totalVotes} includePhotos={true} size="story" refEl={storyPhotoRef} t={t} />
      <CardCanvas duel={preparedDuel} pctA={pctA} pctB={pctB} totalVotes={totalVotes} includePhotos={false} size="story" refEl={storyCleanRef} t={t} />
      <CardCanvas duel={preparedDuel} pctA={pctA} pctB={pctB} totalVotes={totalVotes} includePhotos={true} size="feed" refEl={feedPhotoRef} t={t} />
      <CardCanvas duel={preparedDuel} pctA={pctA} pctB={pctB} totalVotes={totalVotes} includePhotos={false} size="feed" refEl={feedCleanRef} t={t} />
    </Shell>
  );
};

/* Visible scaled preview — uses CSS only, not exported */
const PreviewCard = ({ duel, includePhotos, pctA, pctB, totalVotes, size, t }) => {
  const winA = pctA >= pctB;
  const pctWin = winA ? pctA : pctB;
  const ratio = size === "story" ? "aspect-[9/16]" : "aspect-square";
  return (
    <div className={`${ratio} w-full bg-white p-4 flex flex-col`} data-testid="card-preview">
      <div className="text-[10px] uppercase tracking-widest text-[#7F77DD] font-bold">OutfitDuel</div>
      <div className="mt-2 font-display font-bold text-gray-950 text-base leading-tight line-clamp-2">
        {duel.question || t("result.default_question")}
      </div>
      {includePhotos ? (
        <div className={`mt-3 grid ${size === "story" ? "grid-cols-1 grid-rows-2" : "grid-cols-2"} gap-2 flex-1 min-h-0`}>
          {[
            { letter: "A", pct: pctA, src: duel.photo_a_url, isWin: winA },
            { letter: "B", pct: pctB, src: duel.photo_b_url, isWin: !winA },
          ].map((s) => (
            <div
              key={s.letter}
              className={`relative rounded-lg overflow-hidden border-2 ${s.isWin ? "border-[#7F77DD]" : "border-gray-200"}`}
            >
              <img src={s.src} alt={s.letter} className="w-full h-full object-cover" />
              <div className={`absolute bottom-1.5 left-1.5 ${s.isWin ? "bg-[#7F77DD] text-white" : "bg-black/70 text-white"} text-[10px] font-bold px-2 py-0.5 rounded-full`}>
                {s.pct}% · {s.letter}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="text-5xl font-display font-bold text-[#7F77DD] leading-none">{pctWin}%</div>
          <div className="mt-2 text-sm font-semibold text-gray-900">{t("result.winner_chose")} {winA ? "A" : "B"}</div>
          <div className="mt-1 text-[10px] text-gray-400">· {totalVotes} {votesLabel(totalVotes, t)}</div>
        </div>
      )}
      {includePhotos && (
        <div className="mt-2 text-sm font-bold text-gray-900">
          {pctWin}% {t("result.winner_chose")} {winA ? "A" : "B"}{" "}
          <span className="text-xs text-gray-400 font-medium">· {totalVotes} {votesLabel(totalVotes, t)}</span>
        </div>
      )}
      <div className="mt-1 text-[9px] uppercase tracking-widest text-gray-400">outfitduel.com</div>
    </div>
  );
};

export default Result;
