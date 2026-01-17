import { useEffect, useState } from "react";
import { productApi } from "../api";
import toast from "react-hot-toast";
import { ProductGridSkeleton } from "../components/Loaders";

type Product = { id: number; name: string; price: number; description: string };

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    productApi.get("/products")
      .then(res => setProducts(res.data))
      .catch((e) => toast.error(e?.response?.data?.detail || "Failed to load products"))
      .finally(() => setLoading(false));
  }, []);

  const addToCart = (p: Product) => {
    const cart = JSON.parse(localStorage.getItem("cart") || "[]");
    cart.push({ product_id: p.id, qty: 1 });
    localStorage.setItem("cart", JSON.stringify(cart));
    toast.success(`Added "${p.name}" 🍬`);
  };

  return (
    <div className="space-y-6">
      <section className="candy-card p-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              Pick your{" "}
              <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
                sweet
              </span>{" "}
              favorites
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Shiny products, fast checkout, email confirmations.
            </p>
          </div>
          <div className="flex gap-2">
            <span className="rounded-full bg-pink-100 px-3 py-1 text-xs font-semibold text-pink-700">New</span>
            <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700">Popular</span>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Verified</span>
          </div>
        </div>
      </section>

      {loading ? (
        <ProductGridSkeleton />
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((p) => (
            <div key={p.id} className="candy-card group overflow-hidden p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-extrabold leading-snug">{p.name}</h3>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-600">
                    {p.description || "A super glossy sweet treat."}
                  </p>
                </div>
                <div className="shrink-0 rounded-2xl bg-white px-3 py-2 text-sm font-extrabold">
                  <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
                    ${p.price}
                  </span>
                </div>
              </div>

              <div className="mt-4 h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full w-2/3 bg-gradient-to-r from-pink-400 via-orange-300 to-sky-400 opacity-80" />
              </div>

              <button className="candy-btn mt-4 w-full" onClick={() => addToCart(p)}>
                Add to cart
              </button>

              <div className="pointer-events-none mt-4 flex justify-between text-xs text-slate-500 opacity-0 transition group-hover:opacity-100">
                <span>✨ glossy</span><span>🍬 candy</span><span>💌 email</span>
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
