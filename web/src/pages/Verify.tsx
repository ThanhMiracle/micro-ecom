import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { authApi } from "../api";
import toast from "react-hot-toast";
import { candyConfetti } from "../lib/confetti";

export default function Verify() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "ok" | "fail">("loading");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setStatus("fail");
      setMsg("Missing token.");
      toast.error("Missing token");
      return;
    }

    authApi
      .get(`/auth/verify?token=${encodeURIComponent(token)}`)
      .then(() => {
        setStatus("ok");
        candyConfetti();
        toast.success("Email verified 🎉");
      })
      .catch((e) => {
        setStatus("fail");
        const d = e?.response?.data?.detail || "Invalid or expired token.";
        setMsg(d);
        toast.error(d);
      });
  }, []);

  return (
    <div className="mx-auto max-w-lg">
      <div className="candy-card p-8 text-center">
        {status === "loading" && (
          <>
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-gradient-to-r from-pink-400 via-orange-300 to-sky-400 opacity-80" />
            <h2 className="text-2xl font-extrabold">Verifying…</h2>
            <p className="mt-2 text-sm text-slate-600">Sprinkling magic ✨</p>
          </>
        )}

        {status === "ok" && (
          <>
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-emerald-200" />
            <h2 className="text-2xl font-extrabold text-emerald-700">Email verified 🎉</h2>
            <p className="mt-2 text-sm text-slate-600">You can login and start ordering.</p>
            <div className="mt-6">
              <Link to="/login"><button className="candy-btn w-full">Go to Login</button></Link>
            </div>
          </>
        )}

        {status === "fail" && (
          <>
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-pink-200" />
            <h2 className="text-2xl font-extrabold text-pink-700">Verification failed 😵‍💫</h2>
            <p className="mt-2 text-sm text-slate-600">{msg}</p>
            <div className="mt-6">
              <Link to="/register"><button className="candy-btn-outline w-full">Register again</button></Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
