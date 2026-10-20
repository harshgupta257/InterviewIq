import { BriefcaseBusiness, FlaskConical, Github, History, LayoutDashboard, Linkedin, LogOut, Menu, Plus, Settings, Twitter, WifiOff, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { useConfig } from "@/hooks/queries";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";
import { Wordmark } from "./brand";
import { Button } from "./ui/button";

/** Kept for existing imports. */
export const Logo = Wordmark;

function useOnline() {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

function OfflineBanner() {
  const online = useOnline();
  if (online) return null;
  return (
    <div role="status" className="flex items-center justify-center gap-2 bg-warning px-4 py-2 text-sm text-warning-foreground">
      <WifiOff className="size-4" aria-hidden /> You're offline. Drafts are kept on this device; submit when you're back online.
    </div>
  );
}

const PUBLIC_NAV = [
  { href: "/#features", label: "Features" },
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#pricing", label: "Pricing" },
  { href: "/#faq", label: "FAQ" },
];

/** Swiss navbar: white bar, black rule, logo / links / CTA on one baseline. */
export function PublicHeader() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-foreground bg-background">
      <div className="container flex h-16 items-center justify-between gap-6">
        <Wordmark />
        <nav className="hidden items-center gap-8 md:flex" aria-label="Main">
          {PUBLIC_NAV.map((n) => (
            <a key={n.href} href={n.href} className="text-[13px] font-medium text-foreground underline-offset-[6px] transition-all duration-200 hover:underline">
              {n.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-5 md:flex">
          {user ? (
            <Button asChild size="sm">
              <Link to="/dashboard">Open dashboard</Link>
            </Button>
          ) : (
            <>
              <Link to="/login" className="text-[13px] font-medium underline-offset-[6px] transition-all duration-200 hover:underline">
                Sign in
              </Link>
              <Button asChild size="sm">
                <Link to="/signup">Start practicing</Link>
              </Button>
            </>
          )}
        </div>
        <button
          className="grid size-10 cursor-pointer place-items-center transition-all duration-200 hover:bg-secondary md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-foreground bg-background md:hidden">
          <nav className="container flex flex-col" aria-label="Main">
            {PUBLIC_NAV.map((n) => (
              <a key={n.href} href={n.href} onClick={() => setOpen(false)} className="border-b py-4 text-lg font-semibold tracking-[-0.02em]">
                {n.label}
              </a>
            ))}
            <div className="flex gap-2 py-5">
              {user ? (
                <Button asChild className="flex-1">
                  <Link to="/dashboard">Open dashboard</Link>
                </Button>
              ) : (
                <>
                  <Button asChild variant="outline" className="flex-1">
                    <Link to="/login">Sign in</Link>
                  </Button>
                  <Button asChild className="flex-1">
                    <Link to="/signup">Start practicing</Link>
                  </Button>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}

const socialIcons: Record<string, typeof Github> = { GitHub: Github, LinkedIn: Linkedin, X: Twitter };

export function Footer() {
  const columns: { title: string; links: { label: string; to: string }[] }[] = [
    {
      title: "Product",
      links: [
        { label: "Features", to: "/#features" },
        { label: "How it works", to: "/#how-it-works" },
        { label: "Pricing", to: "/#pricing" },
        { label: "FAQ", to: "/#faq" },
      ],
    },
    {
      title: "Practice",
      links: [
        { label: "Mock interview questions", to: "/#features" },
        { label: "Answer scoring rubric", to: "/#rubric" },
        { label: "Resume-based interview prep", to: "/#how-it-works" },
        { label: "Behavioural interview practice", to: "/#features" },
      ],
    },
    {
      title: "Account",
      links: [
        { label: "Create an account", to: "/signup" },
        { label: "Sign in", to: "/login" },
        { label: "Dashboard", to: "/dashboard" },
        { label: "Interview history", to: "/history" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "Privacy policy", to: "/privacy" },
        { label: "Terms of use", to: "/terms" },
        { label: "Contact", to: "/contact" },
      ],
    },
  ];

  return (
    <footer className="bg-ink text-paper">
      <div className="container grid gap-12 py-16 lg:grid-cols-12">
        <div className="space-y-5 lg:col-span-4">
          <Wordmark light />
          <p className="max-w-xs text-sm leading-relaxed text-paper/75">
            Interview practice built from your resume and the role you want. Eight questions, four scores, one next step.
          </p>
          {site.social.length > 0 && (
            <ul className="flex gap-2" aria-label="Social media">
              {site.social.map((s) => {
                const Icon = socialIcons[s.name];
                return (
                  <li key={s.name}>
                    <a
                      href={s.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`InterviewIQ on ${s.name}`}
                      className="grid size-10 cursor-pointer place-items-center border border-paper/40 transition-all duration-200 hover:bg-paper hover:text-ink"
                    >
                      <Icon className="size-4" aria-hidden />
                    </a>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <nav className="grid grid-cols-2 gap-10 sm:grid-cols-4 lg:col-span-8" aria-label="Footer">
          {columns.map((c) => (
            <div key={c.title} className="space-y-4">
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-paper/60">{c.title}</p>
              <ul className="space-y-2.5 text-sm">
                {c.links.map((l) => (
                  <li key={l.label}>
                    {l.to.startsWith("/#") ? (
                      <a href={l.to} className="text-paper/85 underline-offset-4 transition-all duration-200 hover:text-paper hover:underline">
                        {l.label}
                      </a>
                    ) : (
                      <Link to={l.to} className="text-paper/85 underline-offset-4 transition-all duration-200 hover:text-paper hover:underline">
                        {l.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </div>
      <div className="border-t border-paper/20">
        <div className="container flex flex-col gap-2 py-6 text-xs text-paper/60 sm:flex-row sm:justify-between">
          <p>© 2026 InterviewIQ. All rights reserved.</p>
          <p>Feedback is generated automatically and may be imperfect. Use it as practice, not as a verdict.</p>
        </div>
      </div>
    </footer>
  );
}

export function PublicLayout({ children }: { children?: ReactNode; overDark?: boolean }) {
  return (
    <div className="flex min-h-screen flex-col">
      <OfflineBanner />
      <PublicHeader />
      <main className="flex-1">{children ?? <Outlet />}</main>
      <Footer />
    </div>
  );
}

const NAV = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/interviews/new", label: "New interview", icon: Plus },
  { to: "/jobs", label: "Job finder", icon: BriefcaseBusiness },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];

function DemoBanner() {
  const { user } = useAuth();
  const { data: config } = useConfig();
  if (!user?.isDemo && !config?.ai_is_demo) return null;
  return (
    <div className="border-b border-accent-foreground/10 bg-accent px-4 py-2 text-center text-xs text-accent-foreground">
      <FlaskConical className="mr-1.5 inline size-3.5 align-[-2px]" aria-hidden />
      {config?.ai_is_demo
        ? "Demo mode: questions and scores come from a simple offline heuristic, not an AI model. "
        : "Demo account: "}
      {user?.isDemo && "Sample history is fictional and your demo data is temporary."}
    </div>
  );
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/dashboard"}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-md px-3 py-2.5 text-[13.5px] transition-colors",
              isActive ? "bg-paper/[0.09] text-paper" : "text-paper/60 hover:bg-paper/[0.05] hover:text-paper",
            )
          }
        >
          {({ isActive }) => (
            <>
              <span className={cn("h-4 w-px transition-colors", isActive ? "bg-taupe-light" : "bg-transparent")} aria-hidden />
              <Icon className="size-4" aria-hidden />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function SidebarFooter({ onSignOut }: { onSignOut: () => void }) {
  const { user } = useAuth();
  const label = user?.isDemo ? "Demo user" : user?.email ?? "";
  return (
    <div className="space-y-3 border-t border-paper/10 pt-4">
      <div className="flex items-center gap-3 px-1">
        <span className="grid size-8 shrink-0 place-items-center bg-paper text-xs font-bold uppercase text-ink">
          {label.slice(0, 1) || "?"}
        </span>
        <span className="min-w-0 truncate text-xs text-paper/70">{label}</span>
      </div>
      <button onClick={onSignOut} className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-[13px] text-paper/60 transition-colors hover:bg-paper/[0.05] hover:text-paper">
        <LogOut className="size-4" aria-hidden /> Sign out
      </button>
    </div>
  );
}

export function AppLayout() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [location.pathname]);

  const doSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col bg-ink dark:border-r dark:border-border px-4 py-6 lg:flex">
        <Wordmark light to="/dashboard" className="px-2" />
        <Button asChild variant="inverse" className="mb-6 mt-8 w-full justify-start">
          <Link to="/interviews/new">
            <Plus /> Start new interview
          </Link>
        </Button>
        <SidebarNav />
        <div className="mt-auto">
          <SidebarFooter onSignOut={doSignOut} />
        </div>
      </aside>

      {/* Mobile / tablet top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background/90 px-4 backdrop-blur-md lg:hidden">
        <Wordmark to="/dashboard" />
        <Button variant="ghost" size="icon" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          {open ? <X /> : <Menu />}
        </Button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button className="absolute inset-0 bg-ink/50" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col bg-ink px-4 py-5 animate-in slide-in-from-left duration-300">
            <div className="flex items-center justify-between px-2">
              <Wordmark light to="/dashboard" />
              <button className="grid size-9 place-items-center text-paper" aria-label="Close menu" onClick={() => setOpen(false)}>
                <X className="size-5" />
              </button>
            </div>
            <Button asChild variant="inverse" className="mb-5 mt-6 w-full justify-start">
              <Link to="/interviews/new">
                <Plus /> Start new interview
              </Link>
            </Button>
            <SidebarNav onNavigate={() => setOpen(false)} />
            <div className="mt-auto">
              <SidebarFooter onSignOut={doSignOut} />
            </div>
          </div>
        </div>
      )}

      <div className="lg:pl-60">
        <OfflineBanner />
        <DemoBanner />
        <main className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8 lg:px-12 lg:py-12">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 border-b pb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="space-y-2">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="display text-[2.4rem] text-foreground sm:text-[2.9rem]">{title}</h1>
        {description && <p className="max-w-2xl text-[15px] leading-relaxed text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
