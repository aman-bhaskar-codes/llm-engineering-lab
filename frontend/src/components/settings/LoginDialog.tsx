"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAppStore } from "@/state/useAppStore";
import { toast } from "sonner";

export function LoginDialog() {
  const open = useAppStore((s) => s.ui.loginOpen);
  const closeLogin = useAppStore((s) => s.closeLogin);
  const setAuthToken = useAppStore((s) => s.setAuthToken);

  const [email, setEmail] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    setEmail("");
  }, []);

  function getBaseUrl() {
    return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  }

  async function loginWithBackend(emailValue: string) {
    setLoading(true);
    try {
      const res = await fetch(`${getBaseUrl()}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailValue })
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`Login failed (${res.status}): ${text || "unknown error"}`);
      }
      const body = await res.json();
      const token: string = body.access_token;
      const userId: string = body.user_id;
      const name = emailValue.split("@")[0] || "User";
      setAuthToken({ token, userId, name, email: emailValue });
      closeLogin();
    } catch (e: any) {
      toast.error(e?.message ? String(e.message) : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => (!v ? closeLogin() : null)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sign in</DialogTitle>
          <DialogDescription>Optional placeholder authentication (local-only).</DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-3">
          <div className="space-y-2">
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-50">Email</div>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g., rohit@company.com"
              type="email"
              disabled={loading}
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                if (loading) return;
                void loginWithBackend(`guest_${Math.random().toString(16).slice(2)}@local.test`);
              }}
              disabled={loading}
            >
              Continue as guest
            </Button>
            <Button
              disabled={loading}
              onClick={() => {
                const trimmed = email.trim();
                if (!trimmed) {
                  toast.error("Please enter your email.");
                  return;
                }
                void loginWithBackend(trimmed);
              }}
            >
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

