// Public build-time configuration only. Never read secrets here.
export const env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000",
  supabaseUrl: (import.meta.env.VITE_SUPABASE_URL as string | undefined) || "",
  supabaseAnonKey: (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) || "",
};

export const supabaseConfigured = Boolean(env.supabaseUrl && env.supabaseAnonKey);
