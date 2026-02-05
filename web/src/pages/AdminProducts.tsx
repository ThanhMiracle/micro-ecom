import { useEffect, useMemo, useState } from "react";
import { productApi } from "../api";
import toast from "react-hot-toast";
import { TableSkeleton } from "../components/Loaders";

type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  published: boolean;
  image_url?: string | null;
};

function resolveImageUrl(imageUrl: string | null | undefined) {
  if (!imageUrl) return null;

  // absolute URL from backend
  if (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")) return imageUrl;

  // use axios baseURL (runtime env aware)
  const base = productApi.defaults.baseURL || "";
  return `${base}${imageUrl.startsWith("/") ? "" : "/"}${imageUrl}`;
}


export default function AdminProducts() {
  const [rows, setRows] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState<number>(9.99);

  // track uploading by product id
  const [uploadingId, setUploadingId] = useState<number | null>(null);

  const canCreate = useMemo(() => {
    return !!name.trim() && price > 0;
  }, [name, price]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await productApi.get("/admin/products");
      setRows(r.data);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Admin load failed (login as admin?)");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    try {
      await productApi.post("/admin/products", {
        name: name.trim(),
        description,
        price,
        published: true,
      });
      toast.success("Created & published ✨");
      setName("");
      setDescription("");
      setPrice(9.99);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Create failed");
    }
  };

  const togglePublish = async (p: Product) => {
    try {
      await productApi.patch(`/admin/products/${p.id}`, { published: !p.published });
      toast.success(p.published ? "Unpublished" : "Published");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Update failed");
    }
  };

  const remove = async (p: Product) => {
    try {
      await productApi.delete(`/admin/products/${p.id}`);
      toast.success("Deleted 🧹");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const uploadImage = async (p: Product, file: File) => {
    // light validation
    if (!file.type.startsWith("image/")) {
      toast.error("Please choose an image file");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image is too large (max 5MB)");
      return;
    }

    const fd = new FormData();
    fd.append("file", file);

    setUploadingId(p.id);
    try {
      await productApi.post(`/admin/products/${p.id}/image`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Image uploaded 🖼️");
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Image upload failed");
    } finally {
      setUploadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="candy-card p-6">
        <h2 className="text-2xl font-extrabold tracking-tight">
          Admin Dashboard{" "}
          <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
            🍭
          </span>
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Create products, upload images & publish them to the homepage.
        </p>
      </div>

      {/* CREATE */}
      <div className="candy-card p-6">
        <h3 className="text-lg font-extrabold">Create new product ✨</h3>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div>
            <div className="text-xs font-semibold text-slate-600">Name</div>
            <input
              className="candy-input mt-1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Rainbow Donut"
            />
          </div>

          <div>
            <div className="text-xs font-semibold text-slate-600">Price</div>
            <input
              className="candy-input mt-1"
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
            />
          </div>

          <div className="md:col-span-3">
            <div className="text-xs font-semibold text-slate-600">Description</div>
            <textarea
              className="candy-input mt-1 min-h-[90px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Super glossy, candy-like, colorful treat…"
            />
          </div>
        </div>

        <button
          className="candy-btn mt-4 disabled:opacity-60"
          disabled={!canCreate}
          onClick={create}
        >
          Create & Publish
        </button>
      </div>

      {/* TABLE */}
      <div className="candy-card p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-extrabold">All products</h3>
          <button className="candy-btn-outline" onClick={load} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {loading ? (
          <TableSkeleton />
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-600">
                  <th className="py-2">Product</th>
                  <th className="py-2">Price</th>
                  <th className="py-2">Published</th>
                  <th className="py-2 text-right">Actions</th>
                </tr>
              </thead>

              <tbody>
                {rows.map((p) => {
                  const img = resolveImageUrl(p.image_url);
                  const isUploading = uploadingId === p.id;

                  return (
                    <tr key={p.id} className="border-t border-white/60">
                      {/* PRODUCT CELL */}
                      <td className="py-3">
                        <div className="flex items-center gap-3">
                          {img ? (
                            <img
                              src={img}
                              alt={p.name}
                              className="h-12 w-12 rounded-xl object-cover border"
                            />
                          ) : (
                            <div className="h-12 w-12 rounded-xl border bg-gradient-to-br from-pink-200 via-yellow-100 to-sky-200" />
                          )}

                          <div className="min-w-0">
                            <div className="font-extrabold">{p.name}</div>
                            <div className="text-xs text-slate-600 line-clamp-1">
                              {p.description || "—"}
                            </div>

                            <label
                              className={
                                "mt-1 inline-block cursor-pointer text-xs font-bold hover:underline " +
                                (isUploading ? "text-slate-400 cursor-not-allowed" : "text-pink-600")
                              }
                            >
                              {isUploading ? "Uploading…" : "Upload image"}
                              <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                disabled={isUploading}
                                onChange={(e) => {
                                  const f = e.target.files?.[0];
                                  if (f) uploadImage(p, f);
                                  e.currentTarget.value = "";
                                }}
                              />
                            </label>
                          </div>
                        </div>
                      </td>

                      {/* PRICE */}
                      <td className="py-3 font-bold">
                        <span className="bg-gradient-to-r from-pink-500 via-orange-400 to-sky-500 bg-clip-text text-transparent">
                          ${p.price}
                        </span>
                      </td>

                      {/* PUBLISHED */}
                      <td className="py-3">
                        <span
                          className={
                            "rounded-full px-3 py-1 text-xs font-bold " +
                            (p.published
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-slate-100 text-slate-700")
                          }
                        >
                          {p.published ? "Yes" : "No"}
                        </span>
                      </td>

                      {/* ACTIONS */}
                      <td className="py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button className="candy-btn-outline" onClick={() => togglePublish(p)}>
                            {p.published ? "Unpublish" : "Publish"}
                          </button>
                          <button className="candy-btn-outline" onClick={() => remove(p)}>
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {rows.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-10 text-center text-slate-600">
                      No products yet. Create one above ✨
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
