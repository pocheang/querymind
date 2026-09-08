import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "@/App";
import { applyAmberTheme } from "@/lib/theme";
import "@/i18n/config";
import "@/styles/main.css";

applyAmberTheme();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
