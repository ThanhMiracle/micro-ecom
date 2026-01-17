import { useState } from "react";
import { authApi } from "../api";
import toast from "react-hot-toast";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);

  const submit = async () => {
    try {
      await authApi.post("/auth/register", { email, password });
      setDone(true);
      toast.success("Registered! Check your email 💌");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Register failed");
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <div className="candy-card p-6">
        <h2 className="text-2xl font-extrabold tracking-tight">
          Create your{" "}
          <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
            candy
          </span>{" "}
          account 🍭
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          After signup, you’ll get a verification email link.
        </p>

        {!done ? (
          <div className="mt-6 space-y-3">
            <input className="candy-input" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <input className="candy-input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button className="candy-btn w-full" onClick={submit}>Register</button>
          </div>
        ) : (
          <div className="mt-6 rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
            <div className="text-lg font-extrabold text-emerald-700">Signed up! 💌</div>
            <div className="mt-1 text-sm text-emerald-700/90">
              Check your email to verify your account, then login.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
