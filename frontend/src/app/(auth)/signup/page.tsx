"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Leaf,
  Eye,
  EyeOff,
  User,
  Lock,
  ArrowRight,
  AlertCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import ThemeToggle from "@/components/ui/ThemeToggle";
import { getApiErrorMessage, signup } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function SignupPage() {
  const router = useRouter();
  const { setAuth } = useAuth();

  const [form, setForm] = useState({ username: "", password: "", confirm: "" });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const strength = (() => {
    const p = form.password;
    if (!p) return 0;
    let s = 0;
    if (p.length >= 8) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/[0-9]/.test(p)) s++;
    if (/[^a-zA-Z0-9]/.test(p)) s++;
    return s;
  })();

  const strengthLabel = ["", "Weak", "Fair", "Good", "Strong"][strength];
  const strengthColor = [
    "",
    "bg-red-400",
    "bg-amber-400",
    "bg-blue-400",
    "bg-forest-500",
  ][strength];

  function validatePasswordRules(password: string): string | null {
    const errors: string[] = [];
    if (!/[A-Z]/.test(password)) errors.push("one uppercase letter");
    if (!/[a-z]/.test(password)) errors.push("one lowercase letter");
    if (!/[0-9]/.test(password)) errors.push("one digit");
    return errors.length ? `Password must contain: ${errors.join(", ")}` : null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const passwordError = validatePasswordRules(form.password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (form.password !== form.confirm) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      const data = await signup(form.username, form.password);
      setAuth(data.user, data.tokens.access_token, data.tokens.refresh_token);
      toast.success(`Welcome, ${data.user.username}! 🌿`);
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Signup failed. Please try again.");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left decorative panel */}
      <div className="hidden lg:flex lg:w-5/12 bg-gradient-to-br from-forest-700 to-forest-900 relative overflow-hidden flex-col items-center justify-center p-12">
        <div className="absolute inset-0 bg-leaf-pattern opacity-30" />
        {/* Decorative circles */}
        <div className="absolute -top-20 -left-20 w-80 h-80 rounded-full bg-forest-500/20 blur-3xl" />
        <div className="absolute -bottom-20 -right-10 w-64 h-64 rounded-full bg-leaf-400/10 blur-3xl" />
        <div className="relative z-10 text-center">
          <div className="w-20 h-20 bg-white/10 backdrop-blur rounded-2xl flex items-center justify-center mx-auto mb-6 border border-white/20">
            <Leaf className="w-10 h-10 text-white" />
          </div>
          <h2 className="font-display text-4xl font-semibold text-white mb-4 leading-tight">
            Protect your
            <br />
            <span className="italic text-leaf-400">harvest</span>
          </h2>
          <p className="text-forest-200 text-base max-w-xs mx-auto leading-relaxed">
            AI-powered plant disease detection and multilingual treatment
            guidance, right from your phone.
          </p>
          <div className="mt-10 flex flex-col gap-3 text-left max-w-xs mx-auto">
            {[
              "Diagnose 38+ crop diseases",
              "Advice in 15+ languages",
              "Track your field history",
            ].map((f) => (
              <div
                key={f}
                className="flex items-center gap-3 text-forest-200 text-sm"
              >
                <div className="w-5 h-5 rounded-full bg-leaf-400/20 border border-leaf-400/40 flex items-center justify-center flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-leaf-400" />
                </div>
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-6 py-5">
          <Link href="/" className="flex items-center gap-2 text-[var(--text)]">
            <div className="w-7 h-7 bg-forest-600 dark:bg-forest-500 rounded-lg flex items-center justify-center">
              <Leaf className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-display font-semibold">LeafScan</span>
          </Link>
          <ThemeToggle />
        </div>

        <div className="flex-1 flex items-center justify-center px-6 py-10">
          <div className="w-full max-w-md animate-fade-up">
            <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[var(--text)] mb-1.5">
              Create account
            </h1>
            <p className="text-[var(--text-muted)] mb-8">
              Already have one?{" "}
              <Link
                href="/auth/login"
                className="text-forest-600 dark:text-forest-400 hover:underline font-medium"
              >
                Sign in
              </Link>
            </p>

            {error && (
              <div className="mb-5 flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Username */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-1.5">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    className="input pl-10"
                    type="text"
                    placeholder="farmer_raj"
                    value={form.username}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, username: e.target.value }))
                    }
                    required
                    minLength={3}
                    maxLength={64}
                    pattern="[a-zA-Z0-9_]+"
                    autoComplete="username"
                  />
                </div>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Letters, numbers and underscores only
                </p>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    className="input pl-10 pr-10"
                    type={showPass ? "text" : "password"}
                    placeholder="Min. 8 characters"
                    value={form.password}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, password: e.target.value }))
                    }
                    required
                    minLength={8}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(!showPass)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text)]"
                  >
                    {showPass ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                {/* Strength bar */}
                {form.password && (
                  <div className="mt-2">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map((i) => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full transition-all duration-300 ${i <= strength ? strengthColor : "bg-[var(--border)]"}`}
                        />
                      ))}
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      {strengthLabel}
                    </p>
                  </div>
                )}
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-1.5">
                  Confirm password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    className={`input pl-10 ${form.confirm && form.confirm !== form.password ? "ring-2 ring-red-400" : ""}`}
                    type={showPass ? "text" : "password"}
                    placeholder="Re-enter password"
                    value={form.confirm}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, confirm: e.target.value }))
                    }
                    required
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2 mt-2 py-3.5"
              >
                {loading ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Create account <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
