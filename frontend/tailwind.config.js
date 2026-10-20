import animate from "tailwindcss-animate";

/**
 * Minimalism & Swiss Style.
 * Monochrome (black / white), beige surfaces, a single taupe accent, square corners,
 * no shadows, no gradients, one grotesque typeface on a strict grid.
 */
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: { DEFAULT: "1.25rem", sm: "2rem" }, screens: { "2xl": "1200px" } },
    // --border-radius: 0px. `full` stays round for intentional geometric circles only.
    borderRadius: {
      none: "0px",
      sm: "0px",
      DEFAULT: "0px",
      md: "0px",
      lg: "0px",
      xl: "0px",
      "2xl": "0px",
      full: "9999px",
    },
    // --shadow: none.
    boxShadow: { none: "none", DEFAULT: "none", sm: "none", md: "none", lg: "none", xl: "none", "2xl": "none" },
    extend: {
      fontFamily: {
        sans: ["Archivo", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
        display: ["Archivo", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        success: { DEFAULT: "hsl(var(--success))", foreground: "hsl(var(--success-foreground))" },
        warning: { DEFAULT: "hsl(var(--warning))", foreground: "hsl(var(--warning-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        // Fixed (theme-independent) brand values.
        ink: { DEFAULT: "#000000", 800: "#141414", 700: "#262626" },
        paper: { DEFAULT: "#FFFFFF" },
        beige: { DEFAULT: "#F5F1E8", 300: "#E8E1D2" },
        // Single accent. Graphic use only on light surfaces (3:1); text use needs taupe-dark.
        taupe: { DEFAULT: "#B38B6D", light: "#D9C3B0", dark: "#6B4F3A" },
      },
      letterSpacing: {
        eyebrow: "0.12em",
        tightest: "-0.045em",
      },
      transitionDuration: { DEFAULT: "200ms" },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        indeterminate: {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(400%)" },
        },
        "spin-slow": { to: { transform: "rotate(360deg)" } },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both",
        indeterminate: "indeterminate 1.4s cubic-bezier(0.65, 0, 0.35, 1) infinite",
        "spin-slow": "spin-slow 40s linear infinite",
      },
    },
  },
  plugins: [animate],
};
