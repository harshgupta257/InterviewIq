// Public site details, configured through VITE_ variables so no link is ever a dead end.
// A social icon or contact address is only rendered when its value is set.
const v = (x: string | undefined) => (x ?? "").trim();

export const site = {
  contactEmail: v(import.meta.env.VITE_CONTACT_EMAIL),
  social: [
    { name: "GitHub", href: v(import.meta.env.VITE_SOCIAL_GITHUB) },
    { name: "LinkedIn", href: v(import.meta.env.VITE_SOCIAL_LINKEDIN) },
    { name: "X", href: v(import.meta.env.VITE_SOCIAL_X) },
  ].filter((s) => /^https:\/\//.test(s.href)),
};
