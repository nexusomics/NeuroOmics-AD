import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./store/AuthContext";
import "./styles/index.css";

// HashRouter is used so the SPA also runs inside sandboxed embedded previews
// (opaque origins block the History API). URLs look like /#/projects/… —
// deep links work the same in any browser.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </HashRouter>
  </React.StrictMode>
);
