"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

export interface Branding {
  name: string;
  logo_url: string;
  favicon_url: string;
  /** True after the client effect has run; consumers should gate any
   *  branch that varies between SSR and client (logo vs no-logo) on this
   *  flag to avoid React hydration mismatches. */
  hydrated: boolean;
}

const DEFAULT: Branding = {
  name: process.env.NEXT_PUBLIC_APP_NAME ?? "Orbiteus",
  logo_url: process.env.NEXT_PUBLIC_APP_LOGO_URL ?? "",
  favicon_url: process.env.NEXT_PUBLIC_APP_FAVICON_URL ?? "",
  hydrated: false,
};

const BrandingContext = createContext<Branding>(DEFAULT);

export function BrandingProvider({ children }: { children: React.ReactNode }) {
  // Initial state must match SSR exactly. After the first effect (client
  // only), we set `hydrated: true` so consumers can switch on richer data.
  const [branding, setBranding] = useState<Branding>(DEFAULT);

  useEffect(() => {
    let cancelled = false;
    api.get("/base/branding")
      .then(({ data }) => {
        if (cancelled) return;
        setBranding({
          name: data.name || DEFAULT.name,
          logo_url: data.logo_url || DEFAULT.logo_url,
          favicon_url: data.favicon_url || DEFAULT.favicon_url,
          hydrated: true,
        });
      })
      .catch(() => {
        if (!cancelled) setBranding({ ...DEFAULT, hydrated: true });
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}
