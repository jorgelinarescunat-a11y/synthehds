import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./index.css";
import { Landing } from "./pages/Landing";
import { Wizard } from "./pages/Wizard";
import { JobProgress } from "./pages/JobProgress";
import { Results } from "./pages/Results";
import { History } from "./pages/History";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/wizard" element={<Wizard />} />
        <Route path="/job/:jobId" element={<JobProgress />} />
        <Route path="/results/:jobId" element={<Results />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
