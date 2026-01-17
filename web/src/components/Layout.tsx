import { Link, useNavigate } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  const nav = useNavigate();
  const authed = !!localStorage.getItem("token");

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-white/50 bg-white/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="group flex items-center gap-3">
            <div className="sparkle" />
            <div>
              <div className="text-lg font-extrabold tracking-tight">
                <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
                  MicroShop
                </span>
              </div>
              <div className="text-xs text-slate-500">candy vibes • shiny checkout</div>
            </div>
          </Link>

          <nav className="flex items-center gap-2">
            <Link to="/"><button className="candy-btn-outline">Home</button></Link>
            <Link to="/cart"><button className="candy-btn-outline">Cart</button></Link>
            <Link to="/admin/products"><button className="candy-btn-outline">Admin</button></Link>

            {!authed ? (
              <>
                <Link to="/login"><button className="candy-btn">Login</button></Link>
                <Link to="/register"><button className="candy-btn-outline">Register</button></Link>
              </>
            ) : (
              <button
                className="candy-btn-outline"
                onClick={() => { localStorage.removeItem("token"); nav("/"); }}
              >
                Logout
              </button>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>

      <footer className="mx-auto max-w-6xl px-4 pb-10 text-center text-xs text-slate-500">
        Built with 🍭 FastAPI microservices + React Vite
      </footer>
    </div>
  );
}
