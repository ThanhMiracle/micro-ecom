import axios from "axios";

/**
 * Runtime-first config
 * - window.__ENV__   → production (env.js)
 * - import.meta.env → dev / fallback
 */
const runtimeEnv = (window as any).__ENV__ ?? {};

const AUTH_URL =
  runtimeEnv.VITE_AUTH_URL || import.meta.env.VITE_AUTH_URL;
const PRODUCT_URL =
  runtimeEnv.VITE_PRODUCT_URL || import.meta.env.VITE_PRODUCT_URL;
const ORDER_URL =
  runtimeEnv.VITE_ORDER_URL || import.meta.env.VITE_ORDER_URL;

function createApi(baseURL?: string) {
  if (!baseURL) {
    console.warn("API baseURL is empty");
  }

  return axios.create({
    baseURL,
  });
}

export const authApi = createApi(AUTH_URL);
export const productApi = createApi(PRODUCT_URL);
export const orderApi = createApi(ORDER_URL);

[authApi, productApi, orderApi].forEach((api) => {
  api.interceptors.request.use((config) => {
    const t = localStorage.getItem("token");
    if (t) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${t}`;
    }
    return config;
  });
});
