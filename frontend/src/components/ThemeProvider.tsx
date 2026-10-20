import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { storage } from "@/lib/utils";

export type Theme = "light" | "dark" | "system";
const KEY = "iq_theme";

const ThemeContext = createContext<{ theme: Theme; setTheme(t: Theme): void }>({ theme: "system", setTheme: () => undefined });

function apply(theme: Theme) {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => (storage.get(KEY) as Theme) || "system");

  useEffect(() => {
    apply(theme);
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => apply("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = (t: Theme) => {
    storage.set(KEY, t);
    setThemeState(t);
  };
  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export const useTheme = () => useContext(ThemeContext);
