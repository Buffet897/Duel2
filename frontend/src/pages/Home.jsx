import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Users, Clock } from "lucide-react";
import Shell from "@/components/Shell";
import { api, buildAssetUrl } from "@/lib/api";

const FALLBACK_FEED = [
  {
    id: "demo1",
    question: "Welke past bij een zomerdate?",
    photo_a_url: "https://images.unsplash.com/photo-1768825136230-34fb80291f19?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHw0fHxmYXNoaW9uJTIwc3RyZWV0JTIwc3R5bGUlMjBmdWxsJTIwYm9keXxlbnwwfHx8fDE3NzkwOTY2Nzh8MA&ixlib=rb-4.1.0&q=85",
    photo_b_url: "https://images.unsplash.com/photo-1624353656309-8be1a6c457be?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTB8MHwxfHNlYXJjaHwxfHxmYXNoaW9uJTIwc3RyZWV0JTIwc3R5bGUlMjBmdWxsJTIwYm9keXxlbnwwfHx8fDE3NzkwOTY2Nzh8MA&ixlib=rb-4.1.0&q=85",
    votes_a: 312,
    votes_b: 188,
    total: 500,
    is_demo: true,
  },
  {
    id: "demo2",
    question: "Welke is professioneler voor de sollicitatie?",
    photo_a_url: "https://images.unsplash.com/photo-1602757643909-1ca043f4b862?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwyfHxjYXN1YWwlMjBvdXRmaXQlMjBtaXJyb3IlMjBzZWxmaWV8ZW58MHx8fHwxNzc5MDk2Njc4fDA&ixlib=rb-4.1.0&q=85",
    photo_b_url: "https://images.unsplash.com/photo-1741939483735-6923b430ca89?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwxfHxjYXN1YWwlMjBvdXRmaXQlMjBtaXJyb3IlMjBzZWxmaWV8ZW58MHx8fHwxNzc5MDk2Njc4fDA&ixlib=rb-4.1.0&q=85",
    votes_a: 89,
    votes_b: 134,
    total: 223,
    is_demo: true,
  },
];

const Home = () => {
  const [feed, setFeed] = useState([]);
  const [stats, setStats] = useState({ weekly: 47, total: 0 });

  useEffect(() => {
    (async () => {
      try {
        const [popularRes, statsRes] = await Promise.all([
          api.get("/duels/popular?limit=6"),
          api.get("/stats/weekly"),
        ]);
        const live = popularRes.data || [];
        setFeed(live.length ? live : FALLBACK_FEED);
        setStats(statsRes.data || { weekly: 47, total: 0 });
      } catch (err) {
        setFeed(FALLBACK_FEED);
      }
    })();
  }, []);

  return (
    <Shell>
      <section className="pt-2 pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F2F1FA] text-[#6B62D6] text-xs font-semibold tracking-wide mb-5">
          <Sparkles className="h-3.5 w-3.5" />
          Nieuw · stem in 1 tik
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-950 leading-[1.1]">
          Welke outfit
          <br />
          <span className="text-[#7F77DD]">moet ik aan?</span>
        </h1>
        <p className="mt-4 text-base text-gray-600 leading-relaxed">
          Upload twee foto's. Stuur de link naar je vrienden. Krijg een winnaar
          binnen minuten — zonder account, zonder gedoe.
        </p>
        <Link
          to="/nieuw"
          data-testid="hero-create-duel-button"
          className="mt-6 w-full bg-[#7F77DD] text-white py-3.5 px-6 rounded-full font-medium hover:bg-[#6B62D6] transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-[0_2px_12px_rgba(127,119,221,0.35)]"
        >
          Maak gratis een duel <ArrowRight className="h-4 w-4" />
        </Link>
        <div className="mt-4 flex items-center justify-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1.5" data-testid="weekly-stats">
            <Users className="h-3.5 w-3.5" /> {stats.weekly.toLocaleString("nl-NL")} duels deze week
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" /> 48u looptijd
          </span>
        </div>
      </section>

      <section className="pt-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-display font-semibold text-gray-900">
            Populair op het platform
          </h2>
          <span className="text-xs uppercase tracking-wider text-gray-400 font-semibold">
            Live
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3" data-testid="popular-feed">
          {feed.map((d) => {
            const total = d.total ?? (d.votes_a || 0) + (d.votes_b || 0);
            const photoA = d.is_demo ? d.photo_a_url : buildAssetUrl(d.photo_a_url);
            const photoB = d.is_demo ? d.photo_b_url : buildAssetUrl(d.photo_b_url);
            const Wrapper = d.is_demo ? "div" : Link;
            const props = d.is_demo
              ? { className: "group" }
              : { to: `/duel/${d.id}`, className: "group" };
            return (
              <Wrapper key={d.id} {...props}>
                <div className="relative aspect-[3/4] rounded-xl overflow-hidden border border-gray-100 bg-gray-50">
                  <div className="grid grid-cols-2 h-full">
                    <img
                      src={photoA}
                      alt="A"
                      loading="lazy"
                      className="w-full h-full object-cover"
                    />
                    <img
                      src={photoB}
                      alt="B"
                      loading="lazy"
                      className="w-full h-full object-cover border-l border-white"
                    />
                  </div>
                  <div className="absolute inset-x-0 bottom-0 px-2 py-1.5 bg-gradient-to-t from-black/70 to-transparent text-[11px] text-white">
                    {total} stem{total !== 1 ? "men" : ""}
                  </div>
                </div>
                <p className="mt-2 text-sm text-gray-800 line-clamp-2 leading-snug">
                  {d.question || "Welke outfit wint?"}
                </p>
              </Wrapper>
            );
          })}
        </div>
        {feed.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-8">
            Nog geen duels. Wees de eerste!
          </p>
        )}
      </section>

      <section className="mt-12 rounded-2xl bg-[#FAFAFA] border border-gray-100 p-5">
        <h3 className="font-display text-base font-semibold text-gray-900">
          Zo werkt het
        </h3>
        <ol className="mt-3 space-y-2 text-sm text-gray-600">
          <li className="flex gap-3">
            <span className="text-[#7F77DD] font-bold">1.</span> Upload twee outfitfoto's
          </li>
          <li className="flex gap-3">
            <span className="text-[#7F77DD] font-bold">2.</span> Krijg een unieke link
          </li>
          <li className="flex gap-3">
            <span className="text-[#7F77DD] font-bold">3.</span> Deel met wie jij wilt
          </li>
        </ol>
      </section>
    </Shell>
  );
};

export default Home;
