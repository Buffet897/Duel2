import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { Copy, Share2, Check, ArrowRight, Sparkles } from "lucide-react";
import { toast } from "sonner";
import Shell from "@/components/Shell";
import ReportButton from "@/components/ReportButton";
import { api, buildAssetUrl } from "@/lib/api";

const ANIMATION_REVEAL_MS = 700;
const CTA_DELAY_MS = 3000;

const Duel = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const justCreated = params.get("created") === "1";

  const [duel, setDuel] = useState(null);
  const [error, setError] = useState(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [showCta, setShowCta] = useState(false);
  const [copied, setCopied] = useState(false);
  const [stats, setStats] = useState({ weekly: 47 });
  const [voting, setVoting] = useState(false);

  // Swipe state
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-10, 10]);
  const tintA = useTransform(x, [-200, 0], [1, 0]);
  const tintB = useTransform(x, [0, 200], [0, 1]);
  const swipeRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [duelRes, voteRes, statsRes] = await Promise.all([
          api.get(`/duels/${id}`),
          api.get(`/duels/${id}/check-vote`),
          api.get("/stats/weekly"),
        ]);
        if (cancelled) return;
        setDuel(duelRes.data);
        if (voteRes.data.has_voted || duelRes.data.is_expired) {
          setHasVoted(true);
        }
        setStats(statsRes.data);
      } catch (err) {
        if (!cancelled) setError(err?.response?.status === 404 ? "not_found" : "error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!hasVoted) return;
    const t = setTimeout(() => setShowCta(true), CTA_DELAY_MS);
    return () => clearTimeout(t);
  }, [hasVoted]);

  // If voted and duel exists, redirect to result page for the rich experience.
  // But we still show inline reveal first.

  const vote = async (choice) => {
    if (voting || hasVoted || !duel || duel.is_expired) return;
    setVoting(true);
    try {
      const form = new FormData();
      form.append("choice", choice);
      const { data } = await api.post(`/duels/${id}/vote`, form);
      setDuel((d) => ({ ...d, votes_a: data.votes_a, votes_b: data.votes_b }));
      setHasVoted(true);
    } catch (err) {
      if (err?.response?.status === 409) {
        // Already voted — treat as voted
        setHasVoted(true);
      } else {
        toast.error(err?.response?.data?.detail || "Stemmen mislukt");
      }
    } finally {
      setVoting(false);
    }
  };

  const shareUrl = useMemo(() => {
    if (typeof window === "undefined") return "";
    // Use the API share endpoint so WhatsApp/iMessage crawlers see proper
    // Open Graph tags. Human browsers are auto-redirected to /duel/{id}.
    return `${window.location.origin}/api/share/duel/${id}`;
  }, [id]);

  const onSwipeEnd = (_, info) => {
    if (Math.abs(info.offset.x) < 50) {
      x.set(0);
      return;
    }
    if (info.offset.x < 0) vote("a");
    else vote("b");
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("Link gekopieerd");
      setTimeout(() => setCopied(false), 1500);
    } catch (_) {
      toast.error("Kopiëren mislukt");
    }
  };

  const whatsapp = () => {
    const text = encodeURIComponent(
      `${duel?.question || "Welke outfit moet ik aan?"}\nStem hier: ${shareUrl}`,
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };

  if (error === "not_found") {
    return (
      <Shell>
        <div className="pt-12 text-center">
          <h1 className="text-2xl font-bold text-gray-950">Duel niet gevonden</h1>
          <p className="mt-2 text-gray-600">Deze link bestaat niet of is verwijderd.</p>
          <button
            onClick={() => nav("/")}
            className="mt-6 w-full bg-[#7F77DD] text-white py-3.5 px-6 rounded-full font-medium hover:bg-[#6B62D6] transition-all"
          >
            Terug naar home
          </button>
        </div>
      </Shell>
    );
  }

  if (!duel) {
    return (
      <Shell>
        <div className="pt-12 flex justify-center text-gray-400">Laden…</div>
      </Shell>
    );
  }

  const totalVotes = duel.votes_a + duel.votes_b;
  const pctA = totalVotes === 0 ? 50 : Math.round((duel.votes_a / totalVotes) * 100);
  const pctB = 100 - pctA;

  return (
    <Shell>
      {justCreated && (
        <div className="mb-4 rounded-2xl border border-[#7F77DD]/30 bg-[#F2F1FA] p-4">
          <div className="flex items-center gap-2 text-[#4A45A0] text-sm font-semibold">
            <Sparkles className="h-4 w-4" /> Je duel staat live!
          </div>
          <p className="mt-1 text-sm text-[#4A45A0]/80 leading-snug">
            Deel de link met je netwerk — anders krijg je geen stemmen.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={copy}
              data-testid="share-copy-button"
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-full bg-white border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-900 hover:border-[#7F77DD] transition"
            >
              {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
              {copied ? "Gekopieerd" : "Kopieer link"}
            </button>
            <button
              onClick={whatsapp}
              data-testid="share-whatsapp-button"
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-full bg-[#25D366] text-white px-4 py-2.5 text-sm font-medium hover:opacity-95 transition"
            >
              <Share2 className="h-4 w-4" /> WhatsApp
            </button>
          </div>
        </div>
      )}

      {duel.question && (
        <h1 className="text-xl sm:text-2xl font-display font-semibold text-gray-950 leading-snug mb-4">
          {duel.question}
        </h1>
      )}
      {!duel.question && (
        <h1 className="text-xl sm:text-2xl font-display font-semibold text-gray-950 leading-snug mb-4">
          Welke outfit wint?
        </h1>
      )}

      {duel.is_hidden ? (
        <div className="rounded-2xl bg-gray-50 border border-gray-100 p-6 text-center" data-testid="duel-hidden-state">
          <div className="mx-auto h-12 w-12 rounded-full bg-[#F2F1FA] flex items-center justify-center mb-3">
            <span className="text-[#7F77DD] text-xl">⚑</span>
          </div>
          <p className="text-base font-display font-semibold text-gray-900 mb-1">
            Dit duel is verborgen
          </p>
          <p className="text-sm text-gray-500">
            Het duel is meerdere keren gerapporteerd en wordt momenteel
            beoordeeld door OutfitDuel.
          </p>
          <button
            onClick={() => nav("/")}
            className="mt-5 w-full bg-[#7F77DD] text-white py-3 rounded-full font-medium hover:bg-[#6B62D6] transition"
          >
            Terug naar home
          </button>
        </div>
      ) : duel.is_expired ? (
        <div className="rounded-2xl bg-gray-50 border border-gray-100 p-5 text-center">
          <p className="text-sm text-gray-500 mb-2">Dit duel is afgelopen</p>
          <button
            onClick={() => nav(`/duel/${id}/resultaat`)}
            data-testid="view-result-button"
            className="mt-2 w-full bg-[#7F77DD] text-white py-3 rounded-full font-medium hover:bg-[#6B62D6] transition"
          >
            Bekijk eindresultaat
          </button>
        </div>
      ) : !hasVoted ? (
        <>
          <motion.div
            ref={swipeRef}
            drag="x"
            style={{ x, rotate }}
            dragConstraints={{ left: 0, right: 0 }}
            onDragEnd={onSwipeEnd}
            className="relative touch-pan-y"
            data-testid="swipe-container"
          >
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => vote("a")}
                data-testid="vote-button-a"
                className="relative group focus:outline-none"
              >
                <div className="aspect-[3/4] rounded-2xl overflow-hidden border-2 border-gray-100 group-hover:border-[#7F77DD] transition relative">
                  <img
                    src={buildAssetUrl(duel.photo_a_url)}
                    alt="Outfit A"
                    loading="lazy"
                    className="w-full h-full object-cover"
                  />
                  <motion.div
                    style={{ opacity: tintA }}
                    className="pointer-events-none absolute inset-0 bg-[#7F77DD]/40 flex items-center justify-center"
                  >
                    <span className="text-white text-3xl font-display font-bold drop-shadow">A</span>
                  </motion.div>
                </div>
                <div className="mt-3 w-full bg-white border-2 border-gray-100 py-3 rounded-2xl font-semibold text-sm group-hover:border-[#7F77DD] group-hover:bg-[#F2F1FA] transition">
                  Stem A
                </div>
              </button>
              <button
                onClick={() => vote("b")}
                data-testid="vote-button-b"
                className="relative group focus:outline-none"
              >
                <div className="aspect-[3/4] rounded-2xl overflow-hidden border-2 border-gray-100 group-hover:border-[#7F77DD] transition relative">
                  <img
                    src={buildAssetUrl(duel.photo_b_url)}
                    alt="Outfit B"
                    loading="lazy"
                    className="w-full h-full object-cover"
                  />
                  <motion.div
                    style={{ opacity: tintB }}
                    className="pointer-events-none absolute inset-0 bg-[#7F77DD]/40 flex items-center justify-center"
                  >
                    <span className="text-white text-3xl font-display font-bold drop-shadow">B</span>
                  </motion.div>
                </div>
                <div className="mt-3 w-full bg-white border-2 border-gray-100 py-3 rounded-2xl font-semibold text-sm group-hover:border-[#7F77DD] group-hover:bg-[#F2F1FA] transition">
                  Stem B
                </div>
              </button>
            </div>
          </motion.div>
          <p className="mt-4 text-center text-xs text-gray-400">
            📱 Of swipe links voor A · rechts voor B
          </p>
        </>
      ) : (
        <RevealedResult
          duel={duel}
          pctA={pctA}
          pctB={pctB}
          totalVotes={totalVotes}
          showCta={showCta}
          stats={stats}
          shareUrl={shareUrl}
          onResultPage={() => nav(`/duel/${id}/resultaat`)}
        />
      )}

      {!duel.is_hidden && <ReportButton duelId={id} />}
    </Shell>
  );
};

const RevealedResult = ({ duel, pctA, pctB, totalVotes, showCta, stats, onResultPage }) => {
  const [animated, setAnimated] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 80);
    return () => clearTimeout(t);
  }, []);
  const winA = pctA >= pctB;
  return (
    <div data-testid="result-revealed">
      <div className="grid grid-cols-2 gap-2">
        {[
          { letter: "A", pct: pctA, src: duel.photo_a_url, isWinner: winA, votes: duel.votes_a },
          { letter: "B", pct: pctB, src: duel.photo_b_url, isWinner: !winA, votes: duel.votes_b },
        ].map((side) => (
          <div key={side.letter} className="relative">
            <div className={`aspect-[3/4] rounded-2xl overflow-hidden border-2 ${side.isWinner ? "border-[#7F77DD]" : "border-gray-100"}`}>
              <img src={buildAssetUrl(side.src)} alt={side.letter} className="w-full h-full object-cover" />
            </div>
            <div className="mt-2">
              <div className="flex items-baseline justify-between text-sm">
                <span className="font-display font-bold text-lg text-gray-950" data-testid={`pct-${side.letter.toLowerCase()}`}>{side.pct}%</span>
                <span className="text-xs text-gray-500">{side.votes} stem{side.votes !== 1 ? "men" : ""}</span>
              </div>
              <div className="mt-1 h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="od-bar h-full bg-[#7F77DD] rounded-full"
                  style={{ width: animated ? `${side.pct}%` : "0%" }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-5 text-center text-sm text-gray-600">
        Totaal {totalVotes} stem{totalVotes !== 1 ? "men" : ""}
      </p>
      <button
        onClick={onResultPage}
        data-testid="goto-result-page"
        className="mt-5 w-full bg-[#7F77DD] text-white py-3.5 px-6 rounded-full font-medium hover:bg-[#6B62D6] transition active:scale-[0.98] flex items-center justify-center gap-2"
      >
        Download deelbaar kaartje <ArrowRight className="h-4 w-4" />
      </button>

      {showCta && (
        <div
          className="mt-8 rounded-2xl border border-gray-100 bg-white p-5 shadow-[0_4px_24px_rgba(0,0,0,0.04)] animate-in fade-in slide-in-from-bottom-2 duration-500"
          data-testid="post-vote-cta"
        >
          <p className="font-display font-semibold text-gray-950">
            Heb jij ook een outfit-dilemma?
          </p>
          <p className="mt-1 text-sm text-gray-600">Maak gratis een duel en krijg snel antwoord.</p>
          <a
            href="/nieuw"
            className="mt-3 inline-flex w-full items-center justify-center gap-2 bg-[#7F77DD] text-white py-3 rounded-full font-medium hover:bg-[#6B62D6] transition"
            data-testid="cta-create-duel"
          >
            Maak gratis een duel <ArrowRight className="h-4 w-4" />
          </a>
          <p className="mt-2 text-center text-xs text-gray-400" data-testid="cta-weekly-counter">
            {stats.weekly.toLocaleString("nl-NL")} duels deze week
          </p>
        </div>
      )}
    </div>
  );
};

export default Duel;
