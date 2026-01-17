import { useState } from "react";
import { authApi } from "../api";
import toast from "react-hot-toast";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = async () => {
    try {
      const res = await authApi.post("/auth/login", { email, password });
      localStorage.setItem("token", res.data.access_token);
      toast.success("Logged in ✨");
      window.location.href = "/";
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Login failed");
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <div className="candy-card p-6">
        <h2 className="text-2xl font-extrabold">
          Welcome back{" "}
          <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
            ✨
          </span>
        </h2>
        <p className="mt-1 text-sm text-slate-600">Login to order sweet stuff.</p>

        <div className="mt-6 space-y-3">
          <input className="candy-input" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input className="candy-input" type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
          <button className="candy-btn w-full" onClick={submit}>Login</button>
        </div>

        <div className="mt-4 text-xs text-slate-500">
          Tip: verify email first or login may be blocked 💌
        </div>
      </div>
    </div>
  );
}
