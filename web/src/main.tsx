import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import AppRoutes from "./routes";
import "./index.css";
import { Toaster } from "react-hot-toast";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppRoutes />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3500,
          style: {
            borderRadius: "18px",
            background: "rgba(255,255,255,0.85)",
            backdropFilter: "blur(10px)",
            boxShadow: "0 18px 45px rgba(15,23,42,0.12)",
            border: "1px solid rgba(236,72,153,0.25)",
            color: "#0f172a",
            fontWeight: 800,
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
);
