import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Clock, FlaskConical, MailCheck } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { useAuth } from "@/auth/AuthProvider";
import { SwissComposition, Wordmark } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Alert, FieldError, Input, Label } from "@/components/ui/primitives";
import { useConfig } from "@/hooks/queries";
import { errorMessage } from "@/lib/api";
import { supabaseConfigured } from "@/lib/env";
import { supabase } from "@/lib/supabase";

function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[1fr_1.05fr]">
      <aside className="hidden flex-col border-r border-foreground bg-beige p-12 text-ink lg:flex">
        <Wordmark />
        <div className="my-auto w-full max-w-[420px] text-ink">
          <SwissComposition />
        </div>
        <div className="max-w-md">
          <p className="eyebrow text-ink/70">Interview practice</p>
          <p className="display mt-4 text-5xl">
            Practise the interview you'll <em>actually face.</em>
          </p>
          <p className="mt-4 text-[15px] leading-relaxed text-ink/75">
            Questions grounded in your resume and the role, scored on four transparent dimensions.
          </p>
        </div>
      </aside>
      <div className="flex flex-col px-5 py-8 sm:px-10">
        <Wordmark className="lg:hidden" />
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
          <div className="mb-8 space-y-2">
            <h1 className="display text-[2.6rem]">{title}</h1>
            {subtitle && <p className="text-[15px] text-muted-foreground">{subtitle}</p>}
          </div>
          {children}
          {footer && <div className="mt-8 border-t pt-6 text-sm text-muted-foreground">{footer}</div>}
        </div>
      </div>
    </div>
  );
}

function DemoButton() {
  const { data: config } = useConfig();
  const { startDemo } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!config?.demo_mode) return null;
  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        className="w-full"
        loading={loading}
        onClick={async () => {
          setLoading(true);
          setError(null);
          try {
            await startDemo();
            navigate("/dashboard");
          } catch (e) {
            setError(errorMessage(e));
          } finally {
            setLoading(false);
          }
        }}
      >
        {!loading && <FlaskConical />} Explore the demo (no sign-up)
      </Button>
      <p className="text-center text-xs text-muted-foreground">A temporary account with clearly labelled sample data.</p>
      <FieldError message={error ?? undefined} />
    </div>
  );
}

function AuthUnavailable() {
  const { data: config, isLoading } = useConfig();
  if (supabaseConfigured || isLoading || config?.demo_mode) return null;
  return (
    <Alert tone="warning" icon={<AlertCircle className="text-warning" />} title="Authentication is not configured">
      Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY for the frontend, or enable DEMO_MODE on the backend. See the README.
    </Alert>
  );
}

const credentials = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(8, "Use at least 8 characters."),
});

export function LoginPage() {
  const { signIn, sessionExpired, clearExpired } = useAuth();
  const [params] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof credentials>>({ resolver: zodResolver(credentials) });
  const { errors, isSubmitting } = form.formState;

  const expired = sessionExpired || params.get("expired") === "1";

  const onSubmit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await signIn(v.email, v.password);
      clearExpired();
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <AuthShell
      title="Log in"
      subtitle="Welcome back. Continue your interview practice."
      footer={
        supabaseConfigured && (
          <>
            New here?{" "}
            <Link to="/signup" className="font-medium text-foreground underline-offset-4 hover:underline">
              Create an account
            </Link>
          </>
        )
      }
    >
      <div className="space-y-4">
        {expired && (
          <Alert tone="warning" icon={<Clock className="text-warning" />} title="Your session expired">
            Please sign in again. Your saved progress is safe.
          </Alert>
        )}
        {params.get("confirmed") && (
          <Alert tone="success" icon={<CheckCircle2 className="text-success" />} title="Email confirmed">
            You can now log in.
          </Alert>
        )}
        {params.get("reset") && (
          <Alert tone="success" icon={<CheckCircle2 className="text-success" />} title="Password updated">
            Log in with your new password.
          </Alert>
        )}
        <AuthUnavailable />
        {supabaseConfigured && (
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...form.register("email")} />
              <FieldError message={errors.email?.message} />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link to="/forgot-password" className="text-xs text-muted-foreground hover:text-foreground">
                  Forgot password?
                </Link>
              </div>
              <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!errors.password} {...form.register("password")} />
              <FieldError message={errors.password?.message} />
            </div>
            {error && <Alert tone="error" icon={<AlertCircle className="text-destructive" />}>{error}</Alert>}
            <Button type="submit" className="w-full" loading={isSubmitting}>
              Log in
            </Button>
          </form>
        )}
        <DemoButton />
      </div>
    </AuthShell>
  );
}

const signupSchema = credentials
  .extend({
    displayName: z.string().trim().max(120).optional(),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Passwords don't match." });

export function SignupPage() {
  const { signUp } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const form = useForm<z.infer<typeof signupSchema>>({ resolver: zodResolver(signupSchema) });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      const { needsConfirmation } = await signUp(v.email, v.password, v.displayName || undefined);
      if (needsConfirmation) setSentTo(v.email);
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  if (sentTo) {
    return (
      <AuthShell title="Check your email">
        <div className="space-y-4 text-sm text-muted-foreground">
          <MailCheck className="size-8 text-primary" aria-hidden />
          <p>
            We sent a confirmation link to <span className="font-medium text-foreground">{sentTo}</span>. Open it to
            activate your account, then log in.
          </p>
          <Button asChild variant="outline" className="w-full">
            <Link to="/login">Back to log in</Link>
          </Button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start practicing interviews tailored to your resume."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <div className="space-y-4">
        <AuthUnavailable />
        {supabaseConfigured && (
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="displayName">
                Name <span className="font-normal text-muted-foreground">(optional)</span>
              </Label>
              <Input id="displayName" autoComplete="name" {...form.register("displayName")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...form.register("email")} />
              <FieldError message={errors.email?.message} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="new-password" aria-invalid={!!errors.password} {...form.register("password")} />
              <FieldError message={errors.password?.message} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input id="confirm" type="password" autoComplete="new-password" aria-invalid={!!errors.confirm} {...form.register("confirm")} />
              <FieldError message={errors.confirm?.message} />
            </div>
            {error && <Alert tone="error" icon={<AlertCircle className="text-destructive" />}>{error}</Alert>}
            <Button type="submit" className="w-full" loading={isSubmitting}>
              Create account
            </Button>
            <p className="text-xs text-muted-foreground">
              Your resume and answers are processed by our AI provider to generate questions and feedback.
            </p>
          </form>
        )}
        <DemoButton />
      </div>
    </AuthShell>
  );
}

export function ForgotPasswordPage() {
  const { requestPasswordReset } = useAuth();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<{ email: string }>({ resolver: zodResolver(z.object({ email: credentials.shape.email })) });

  const onSubmit = form.handleSubmit(async ({ email }) => {
    setError(null);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <AuthShell
      title="Reset your password"
      subtitle="We'll email you a link to choose a new password."
      footer={
        <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
          Back to log in
        </Link>
      }
    >
      {sent ? (
        <Alert tone="success" icon={<MailCheck className="text-success" />} title="Check your inbox">
          If an account exists for that email, a reset link is on its way.
        </Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <AuthUnavailable />
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" aria-invalid={!!form.formState.errors.email} {...form.register("email")} />
            <FieldError message={form.formState.errors.email?.message} />
          </div>
          {error && <Alert tone="error">{error}</Alert>}
          <Button type="submit" className="w-full" loading={form.formState.isSubmitting} disabled={!supabaseConfigured}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}

const resetSchema = z
  .object({ password: credentials.shape.password, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { path: ["confirm"], message: "Passwords don't match." });

export function ResetPasswordPage() {
  const { updatePassword, signOut } = useAuth();
  const navigate = useNavigate();
  const [ready, setReady] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof resetSchema>>({ resolver: zodResolver(resetSchema) });

  // The recovery link signs the user in with a short-lived session.
  useEffect(() => {
    if (!supabase) return setReady(false);
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" || session) setReady(true);
    });
    supabase.auth.getSession().then(({ data }) => setReady((r) => r || !!data.session));
    const t = window.setTimeout(() => setReady((r) => r ?? false), 4000);
    return () => {
      sub.subscription.unsubscribe();
      window.clearTimeout(t);
    };
  }, []);

  const onSubmit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await updatePassword(v.password);
      await signOut();
      navigate("/login?reset=1");
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <AuthShell title="Choose a new password">
      {ready === false ? (
        <Alert tone="error" title="This reset link is invalid or has expired" action={<Button asChild size="sm" variant="outline"><Link to="/forgot-password">Request a new link</Link></Button>} />
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="password">New password</Label>
            <Input id="password" type="password" autoComplete="new-password" {...form.register("password")} />
            <FieldError message={form.formState.errors.password?.message} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm">Confirm new password</Label>
            <Input id="confirm" type="password" autoComplete="new-password" {...form.register("confirm")} />
            <FieldError message={form.formState.errors.confirm?.message} />
          </div>
          {error && <Alert tone="error">{error}</Alert>}
          <Button type="submit" className="w-full" loading={form.formState.isSubmitting} disabled={!ready}>
            Update password
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
