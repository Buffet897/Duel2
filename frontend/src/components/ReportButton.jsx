import { useEffect, useRef, useState } from "react";
import { Flag, X } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const REASONS = [
  { code: "offensive", label: "Ongepaste of aanstootgevende inhoud" },
  { code: "no_consent", label: "Ik sta hier niet op (zonder toestemming)" },
  { code: "spam", label: "Spam of nep" },
];

const ReportButton = ({ duelId }) => {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const popRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e) => {
      if (popRef.current && !popRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const submit = async (code) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("reason", code);
      await api.post(`/duels/${duelId}/report`, form);
      toast.success("Bedankt voor je melding. We bekijken dit binnen 24 uur.");
      setOpen(false);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Rapporteren mislukt");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative mt-8 flex justify-end" ref={popRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 transition"
        data-testid="report-duel-trigger"
      >
        <Flag className="h-3 w-3" />
        Rapporteer dit duel
      </button>

      {open && (
        <div
          className="absolute bottom-full right-0 mb-2 w-72 rounded-2xl border border-gray-100 bg-white shadow-[0_8px_32px_rgba(0,0,0,0.08)] p-3 z-20 animate-in fade-in slide-in-from-bottom-2 duration-200"
          data-testid="report-duel-popover"
          role="dialog"
        >
          <div className="flex items-center justify-between px-1 pb-2 border-b border-gray-100">
            <span className="text-xs font-semibold text-gray-700">
              Waarom rapporteer je dit?
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Sluiten"
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="mt-2 flex flex-col">
            {REASONS.map((r) => (
              <button
                key={r.code}
                type="button"
                onClick={() => submit(r.code)}
                disabled={submitting}
                data-testid={`report-reason-${r.code}`}
                className="text-left text-sm px-3 py-2.5 rounded-xl hover:bg-[#F2F1FA] text-gray-800 disabled:opacity-50 transition"
              >
                {r.label}
              </button>
            ))}
          </div>
          <p className="mt-2 px-3 text-[10px] text-gray-400 leading-snug">
            Na 3 rapportages wordt dit duel automatisch verborgen voor moderatie.
          </p>
        </div>
      )}
    </div>
  );
};

export default ReportButton;
