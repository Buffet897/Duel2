import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Camera, Lock, Mail, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

const PLACEHOLDERS = [
  "Welke outfit past beter bij een zomerdate?",
  "Welke is professioneler voor mijn sollicitatie?",
  "Welke neem ik mee naar het festival?",
];

async function compressClientSide(file, maxWidth = 1200, quality = 0.8) {
  const bitmap = await createImageBitmap(file);
  const ratio = Math.min(1, maxWidth / bitmap.width);
  const w = Math.round(bitmap.width * ratio);
  const h = Math.round(bitmap.height * ratio);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bitmap, 0, 0, w, h);
  return new Promise((resolve) => {
    canvas.toBlob(
      (blob) => resolve(new File([blob], file.name.replace(/\.\w+$/, ".jpg"), { type: "image/jpeg" })),
      "image/jpeg",
      quality,
    );
  });
}

const SlotUploader = ({ slot, label, onPick, preview }) => {
  const inputRef = useRef(null);
  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        data-testid={`upload-photo-${slot}-input`}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onPick(f);
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="aspect-[3/4] w-full border-2 border-dashed border-gray-200 rounded-2xl flex flex-col items-center justify-center bg-gray-50 text-gray-400 hover:bg-gray-100 transition-colors overflow-hidden relative"
        data-testid={`upload-photo-${slot}-button`}
      >
        {preview ? (
          <>
            <img src={preview} alt={`Outfit ${label}`} className="absolute inset-0 w-full h-full object-cover" />
            <span className="absolute top-2 left-2 inline-flex items-center gap-1 bg-white/95 rounded-full px-2 py-1 text-[11px] font-semibold text-gray-800 shadow-sm">
              <RefreshCw className="h-3 w-3" /> Wijzig
            </span>
          </>
        ) : (
          <>
            <Camera className="h-6 w-6 mb-2" />
            <span className="text-sm font-medium text-gray-600">Foto {label}</span>
            <span className="text-xs text-gray-400 mt-1">Tik om te uploaden</span>
          </>
        )}
        <span className="absolute bottom-2 right-2 inline-flex items-center justify-center h-7 w-7 rounded-full bg-[#7F77DD] text-white text-xs font-bold shadow">
          {label}
        </span>
      </button>
    </div>
  );
};

const Create = () => {
  const nav = useNavigate();
  const [fileA, setFileA] = useState(null);
  const [fileB, setFileB] = useState(null);
  const [previewA, setPreviewA] = useState(null);
  const [previewB, setPreviewB] = useState(null);
  const [question, setQuestion] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const placeholder = PLACEHOLDERS[Math.floor(Date.now() / 5000) % PLACEHOLDERS.length];

  const handlePick = async (slot, file) => {
    const compressed = await compressClientSide(file).catch(() => file);
    const url = URL.createObjectURL(compressed);
    if (slot === "a") {
      setFileA(compressed);
      setPreviewA(url);
    } else {
      setFileB(compressed);
      setPreviewB(url);
    }
  };

  const submit = async () => {
    if (!fileA || !fileB) {
      toast.error("Upload eerst beide foto's");
      return;
    }
    if (question.length > 80) {
      toast.error("Vraag mag max 80 tekens zijn");
      return;
    }
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("photo_a", fileA);
      form.append("photo_b", fileB);
      form.append("question", question);
      if (email) form.append("email", email);
      const { data } = await api.post("/duels", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // Persist delete token + share URL locally for the maker
      try {
        const owned = JSON.parse(localStorage.getItem("od_owned") || "{}");
        owned[data.id] = { delete_token: data.delete_token, created_at: data.created_at };
        localStorage.setItem("od_owned", JSON.stringify(owned));
      } catch (_) {}
      toast.success("Duel aangemaakt!");
      nav(`/duel/${data.id}?created=1`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Aanmaken mislukt");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Shell>
      <div className="pt-2 pb-6">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-950">
          Maak een duel
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Upload twee outfits en laat je vrienden kiezen.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3" data-testid="upload-grid">
        <SlotUploader slot="a" label="A" preview={previewA} onPick={(f) => handlePick("a", f)} />
        <SlotUploader slot="b" label="B" preview={previewB} onPick={(f) => handlePick("b", f)} />
      </div>

      <div className="mt-6">
        <label className="text-xs font-semibold tracking-[0.05em] uppercase text-gray-500 block mb-2">
          Stelvraag (optioneel)
        </label>
        <input
          type="text"
          value={question}
          maxLength={80}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={placeholder}
          data-testid="question-input"
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-[#7F77DD]/30 focus:border-[#7F77DD] transition-all placeholder:text-gray-400 bg-gray-50/50"
        />
        <div className="flex justify-between mt-1.5 text-[11px] text-gray-400">
          <span>Tip: hou het kort en vriendelijk</span>
          <span data-testid="question-counter">{question.length}/80</span>
        </div>
      </div>

      <div className="mt-5">
        <label className="text-xs font-semibold tracking-[0.05em] uppercase text-gray-500 block mb-2">
          E-mail (optioneel)
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="jouw@mail.nl — voor het eindresultaat"
            data-testid="email-input"
            className="w-full border border-gray-200 rounded-xl pl-10 pr-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-[#7F77DD]/30 focus:border-[#7F77DD] transition-all placeholder:text-gray-400 bg-gray-50/50"
          />
        </div>
      </div>

      <div className="mt-5 flex items-start gap-2 rounded-xl bg-[#F2F1FA] p-3 text-[12px] text-[#4A45A0] leading-snug">
        <Lock className="h-4 w-4 mt-0.5 shrink-0" />
        <span>
          Jij bepaalt wie stemt — deel de link alleen met wie jij wilt. Foto's
          verdwijnen 7 dagen na het verlopen van het duel.
        </span>
      </div>

      <button
        type="button"
        onClick={submit}
        disabled={submitting}
        data-testid="create-duel-submit"
        className="mt-6 w-full bg-[#7F77DD] disabled:bg-[#B6B0EE] text-white py-3.5 px-6 rounded-full font-medium hover:bg-[#6B62D6] transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-[0_2px_12px_rgba(127,119,221,0.35)]"
      >
        {submitting ? "Bezig..." : (<>Duel aanmaken <ArrowRight className="h-4 w-4" /></>)}
      </button>
    </Shell>
  );
};

export default Create;
