import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import Create from "@/pages/Create";
import Duel from "@/pages/Duel";
import Result from "@/pages/Result";
import Privacy from "@/pages/Privacy";
import NotFound from "@/pages/NotFound";

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
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
