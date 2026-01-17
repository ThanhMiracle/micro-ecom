/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AUTH_URL: string;
  readonly VITE_PRODUCT_URL: string;
  readonly VITE_ORDER_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
