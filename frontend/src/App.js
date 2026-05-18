import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import Create from "@/pages/Create";
import Duel from "@/pages/Duel";
import Result from "@/pages/Result";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import NotFound from "@/pages/NotFound";
import CookieBanner from "@/components/CookieBanner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Toaster position="top-center" richColors closeButton />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/nieuw" element={<Create />} />
          <Route path="/duel/:id" element={<Duel />} />
          <Route path="/duel/:id/resultaat" element={<Result />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/voorwaarden" element={<Terms />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        <CookieBanner />
      </BrowserRouter>
    </div>
  );
}

export default App;
