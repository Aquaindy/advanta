import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/App";
import { initThemeWatcher } from "@/stores/theme-store";
import "@/styles/globals.css";

// Keep the theme in sync with OS changes while in "system" mode. First paint
// is already handled by the inline script in index.html.
initThemeWatcher();

const container = document.getElementById("root");
if (!container) throw new Error("#root not found");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
