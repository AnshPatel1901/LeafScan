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
import { getApiErrorMessage, login } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuth();

  const [form, setForm] = useState({ username: "", password: "" });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(form.username, form.password);
      setAuth(data.user, data.tokens.access_token, data.tokens.refresh_token);
      toast.success(`Welcome back, ${data.user.username}! 🌿`);
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = getApiErrorMessage(err, "Invalid username or password");
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
        <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-leaf-400/10 blur-3xl" />
        <div className="absolute -bottom-20 -left-10 w-64 h-64 rounded-full bg-forest-500/20 blur-3xl" />
        <div className="relative z-10 text-center">
          <div className="w-20 h-20 bg-white/10 backdrop-blur rounded-2xl flex items-center justify-center mx-auto mb-6 border border-white/20">
            <Leaf className="w-10 h-10 text-white" />
          </div>
          <h2 className="font-display text-4xl font-semibold text-white mb-4 leading-tight">
            Welcome
            <br />
            <span className="italic text-leaf-400">back</span>
          </h2>
          <p className="text-forest-200 text-base max-w-xs mx-auto leading-relaxed">
            Sign in to continue diagnosing and treating your crops with AI.
          </p>
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
              Sign in
            </h1>
            <p className="text-[var(--text-muted)] mb-8">
              New to LeafScan?{" "}
              <Link
                href="/auth/signup"
                className="text-forest-600 dark:text-forest-400 hover:underline font-medium"
              >
                Create account
              </Link>
            </p>

            {error && (
              <div className="mb-5 flex items-start gap-3 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-1.5">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    className="input pl-10"
                    type="text"
                    placeholder="your_username"
                    value={form.username}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, username: e.target.value }))
                    }
                    required
                    autoComplete="username"
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--text)] mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
                  <input
                    className="input pl-10 pr-10"
                    type={showPass ? "text" : "password"}
                    placeholder="Your password"
                    value={form.password}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, password: e.target.value }))
                    }
                    required
                    autoComplete="current-password"
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
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3.5"
              >
                {loading ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Sign in <ArrowRight className="w-4 h-4" />
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
