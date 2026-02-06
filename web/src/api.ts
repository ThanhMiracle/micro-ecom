import axios, { AxiosInstance } from "axios";

type RuntimeEnv = {
  VITE_AUTH_URL?: string;
  VITE_PRODUCT_URL?: string;
  VITE_ORDER_URL?: string;
};

function getRuntimeEnv(): RuntimeEnv {
  return ((window as any).__ENV__ as RuntimeEnv) ?? {};
}

function normalizeBaseUrl(url?: string): string | undefined {
  if (!url) return undefined;
  // trim whitespace and remove trailing slash for consistency
  const u = url.trim();
  return u.endsWith("/") ? u.slice(0, -1) : u;
}

/**
 * Runtime-first config (env.js), fallback to Vite build env.
 * Note: we re-check runtime env inside a request interceptor too,
 * in case env.js loads after bundle execution.
 */
function resolveBaseUrl(key: keyof RuntimeEnv, fallback?: string): string | undefined {
  const rt = getRuntimeEnv()[key];
  return normalizeBaseUrl(rt || fallback);
}

function createApi(getBaseURL: () => string | undefined): AxiosInstance {
  const api = axios.create({
    // set initial baseURL (may be undefined)
    baseURL: getBaseURL(),
  });

  api.interceptors.request.use((config) => {
    // Re-resolve baseURL at request time (handles late env.js load)
    const b = getBaseURL();
    if (b) config.baseURL = b;

    const t = localStorage.getItem("token");
    if (t) {
      config.headers = config.headers ?? {};
      (config.headers as any).Authorization = `Bearer ${t}`;
    }
    return config;
  });

  return api;
}

// Build-time fallbacks (dev)
const AUTH_FALLBACK = import.meta.env.VITE_AUTH_URL as string | undefined;
const PRODUCT_FALLBACK = import.meta.env.VITE_PRODUCT_URL as string | undefined;
const ORDER_FALLBACK = import.meta.env.VITE_ORDER_URL as string | undefined;

// APIs
export const authApi = createApi(() => resolveBaseUrl("VITE_AUTH_URL", AUTH_FALLBACK));
export const productApi = createApi(() => resolveBaseUrl("VITE_PRODUCT_URL", PRODUCT_FALLBACK));
export const orderApi = createApi(() => resolveBaseUrl("VITE_ORDER_URL", ORDER_FALLBACK));
