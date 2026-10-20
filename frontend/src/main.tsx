import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Toaster } from "sonner";
import App from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { ThemeProvider } from "./components/ThemeProvider";
import { ApiError } from "./lib/api";
import "./index.css";

const queryClient = new QueryClient({
  queryCache: new QueryCache(),
  mutationCache: new MutationCache(),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      // Retry transient failures only; never retry auth, validation or not-found errors.
      retry: (count, err) => {
        if (err instanceof ApiError && (err.status === 0 || err.status >= 500)) return count < 2;
        return false;
      },
    },
    mutations: { retry: false },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
          <Toaster
            position="bottom-right"
            closeButton
            toastOptions={{
              style: {
                borderRadius: 0,
                boxShadow: "none",
                border: "1px solid hsl(var(--foreground))",
                background: "hsl(var(--background))",
                color: "hsl(var(--foreground))",
                fontFamily: "Archivo, Helvetica, Arial, sans-serif",
              },
            }}
          />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
