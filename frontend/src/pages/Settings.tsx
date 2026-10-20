import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bot, LogOut, Monitor, Moon, Sun, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/auth/AuthProvider";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/layout";
import { useTheme, type Theme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/button";
import { Alert, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, Skeleton } from "@/components/ui/primitives";
import { keys, useConfig, useMe } from "@/hooks/queries";
import { api, ApiError, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const THEMES: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

export default function Settings() {
  const { user, signOut } = useAuth();
  const me = useMe();
  const config = useConfig();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (me.data) setName(me.data.display_name ?? "");
  }, [me.data]);

  const save = useMutation({
    mutationFn: () => api.updateMe(name.trim() || null),
    onSuccess: (p) => {
      qc.setQueryData(keys.me(user?.id), p);
      toast.success("Profile saved");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const del = useMutation({
    mutationFn: api.deleteMe,
    onSuccess: async () => {
      setDeleteOpen(false);
      await signOut({ local: true });
      toast.success("Your account and all data were deleted");
      navigate("/");
    },
    onError: async (e) => {
      // Data deleted but auth user removal failed: be explicit rather than pretending success.
      if (e instanceof ApiError && e.code.startsWith("auth_deletion")) {
        setDeleteOpen(false);
        toast.error(e.message, { duration: 12000 });
        await signOut({ local: true });
        navigate("/");
      }
    },
  });

  const providerLabel = config.data
    ? config.data.ai_is_demo
      ? "Offline demo heuristic (no AI model)"
      : `${config.data.ai_provider === "gemini" ? "Google Gemini" : config.data.ai_provider === "openai" ? "OpenAI" : config.data.ai_provider} · ${config.data.ai_model}`
    : "—";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader eyebrow="Account" title="Settings" description="Manage your profile, appearance and account." />

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>{user?.isDemo ? "Temporary demo account." : "Your account details."}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {me.isLoading ? (
            <Skeleton className="h-24" />
          ) : (
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                save.mutate();
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={me.data?.email ?? (user?.isDemo ? "Demo account (no email)" : "")} disabled readOnly />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="display_name">Display name</Label>
                <Input id="display_name" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} placeholder="How should we greet you?" />
              </div>
              <Button type="submit" loading={save.isPending} disabled={name === (me.data?.display_name ?? "")}>
                Save changes
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Theme">
            {THEMES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                role="radio"
                aria-checked={theme === value}
                onClick={() => setTheme(value)}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-md border p-3 text-sm transition-colors",
                  theme === value ? "border-primary bg-primary/5 font-medium" : "hover:bg-secondary",
                )}
              >
                <Icon className="size-4" aria-hidden /> {label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI processing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2 text-sm">
            <Bot className="size-4 text-muted-foreground" aria-hidden /> {providerLabel}
          </div>
          <p className="text-sm text-muted-foreground">
            Your resume, job descriptions and answers are sent to this provider to generate questions, evaluations and
            example answers. Email addresses, phone numbers and links are stripped first. Overall scores are calculated by
            InterviewIQ, not by the AI.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            onClick={async () => {
              await signOut();
              navigate("/login");
            }}
          >
            <LogOut /> Sign out
          </Button>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Delete account</CardTitle>
          <CardDescription>
            Permanently delete your account, all interview sessions, answers, feedback and usage records.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={() => { del.reset(); setDeleteOpen(true); }}>
            <Trash2 /> Delete my account
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete your account permanently?"
        description={
          <Alert tone="error" className="mt-1">
            This removes all of your sessions, answers and feedback and cannot be undone.
          </Alert>
        }
        confirmLabel="Delete everything"
        requireText="DELETE"
        pending={del.isPending}
        error={del.isError ? errorMessage(del.error) : null}
        onConfirm={() => del.mutate()}
      />
    </div>
  );
}
