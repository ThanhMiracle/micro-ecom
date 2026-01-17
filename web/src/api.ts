import axios from "axios";

export const authApi = axios.create({ baseURL: import.meta.env.VITE_AUTH_URL });
export const productApi = axios.create({ baseURL: import.meta.env.VITE_PRODUCT_URL });
export const orderApi = axios.create({ baseURL: import.meta.env.VITE_ORDER_URL });

[authApi, productApi, orderApi].forEach((api) => {
  api.interceptors.request.use((config) => {
    const t = localStorage.getItem("token");
    if (t) config.headers.Authorization = `Bearer ${t}`;
    return config;
  });
});
