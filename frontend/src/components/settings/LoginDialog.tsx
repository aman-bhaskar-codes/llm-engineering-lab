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
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    setEmail("");
    setPassword("");
  }, []);

  function getBaseUrl() {
    return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
  }

  async function loginWithBackend(emailValue: string, passwordValue: string = "password") {
    setLoading(true);
    try {
      // 1. Try Login
      let res = await fetch(`${getBaseUrl()}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailValue, password: passwordValue })
      });

      // 2. If fail (e.g. user not found), try Signup then Login
      if (res.status === 401 || res.status === 404) {
         await fetch(`${getBaseUrl()}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: emailValue, password: passwordValue })
        });
        
        res = await fetch(`${getBaseUrl()}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: emailValue, password: passwordValue })
        });
      }

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`Auth failed (${res.status}): ${text || "unknown error"}`);
      }

      const body = await res.json();
      const token: string = body.access_token;
      const refreshToken: string = body.refresh_token;
      const userId: string = body.user_id;
      const name = emailValue.split("@")[0] || "User";
      setAuthToken({ token, refreshToken, userId, name, email: emailValue });
      closeLogin();
      toast.success("Signed in successfully");
    } catch (e: any) {
      toast.error(e?.message ? String(e.message) : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => (!v ? closeLogin() : null)}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold tracking-tight">Welcome Back</DialogTitle>
          <DialogDescription>
            Enter your credentials to access your Elite extraction workspace.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <div className="text-sm font-medium text-slate-700 dark:text-slate-300">Email Address</div>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              type="email"
              disabled={loading}
              className="bg-slate-50 border-slate-200 dark:bg-slate-900 dark:border-slate-800"
            />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium text-slate-700 dark:text-slate-300">Password</div>
            <Input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              type="password"
              disabled={loading}
              className="bg-slate-50 border-slate-200 dark:bg-slate-900 dark:border-slate-800"
            />
          </div>

          <div className="flex flex-col gap-2 pt-2">
            <Button
              className="w-full font-semibold"
              disabled={loading || !email || !password}
              onClick={() => {
                const trimmed = email.trim();
                const pass = password.trim();
                if (!trimmed || !pass) {
                  toast.error("Please enter both email and password.");
                  return;
                }
                void loginWithBackend(trimmed, pass);
              }}
            >
              {loading ? "Authenticating..." : "Sign in / Register"}
            </Button>
            
            <div className="relative my-2">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-slate-200 dark:border-slate-800" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-slate-500">Or</span>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                if (loading) return;
                void loginWithBackend(`guest_${Math.random().toString(16).slice(2)}@local.test`, "guestpass");
              }}
              disabled={loading}
            >
              Continue as guest
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

