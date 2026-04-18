"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Leaf,
  CheckCircle2,
  AlertTriangle,
  Globe,
  Zap,
  Info,
  Clock,
  Droplets,
  Shield,
  AlertCircle,
  Microscope,
} from "lucide-react";
import toast from "react-hot-toast";
import { getPrediction } from "@/lib/api";

export default function PredictionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getPrediction(id)
      .then(setData)
      .catch(() => {
        toast.error("Prediction not found");
        router.push("/history");
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading)
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-2 border-forest-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );

  if (!data) return null;

  const isHealthy = data.disease_name?.toLowerCase() === "healthy";
  const aiResponse = data.ai_responses?.[0];
  const confidence = Math.round((data.confidence_score || 0) * 100);

  return (
    <div className="bg-gradient-to-b from-[var(--bg)]/50 to-[var(--bg)]">
      <div className="max-w-3xl mx-auto px-4 sm:px-8 py-8 space-y-6">
        {/* Back button */}
        <button
          onClick={() => router.push("/history")}
          className="inline-flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          Back to history
        </button>

        {/* Hero section with disease info */}
        <div className="card overflow-hidden animate-fade-up">
          {/* Background pattern */}
          <div className="absolute inset-0 bg-gradient-to-br from-forest-500/5 via-transparent to-transparent pointer-events-none" />

          <div className="relative p-8 space-y-6">
            {/* Top bar with status */}
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-2 flex-1">
                <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-widest">
                  PREDICTION #{id.slice(0, 8).toUpperCase()}
                </p>
                <h1 className="font-display text-4xl font-bold text-[var(--text)]">
                  {data.disease_name ?? "Unknown result"}
                </h1>
                <p className="text-lg text-[var(--text-muted)] font-medium">
                  on{" "}
                  <span className="text-forest-600 dark:text-forest-400">
                    {data.plant_name ?? "Unknown plant"}
                  </span>
                </p>
              </div>

              {/* Status badge */}
              <div
                className={`px-4 py-3 rounded-2xl flex items-center gap-2 font-semibold text-sm whitespace-nowrap ${
                  !data.is_plant
                    ? "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    : isHealthy
                      ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
                      : "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                }`}
              >
                {!data.is_plant ? (
                  <>
                    <AlertCircle className="w-5 h-5" />
                    Not a plant
                  </>
                ) : isHealthy ? (
                  <>
                    <CheckCircle2 className="w-5 h-5" />
                    Healthy
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-5 h-5" />
                    Disease
                  </>
                )}
              </div>
            </div>

            {/* Metadata grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {/* Confidence */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                  Confidence
                </p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-[var(--bg-subtle)] rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        confidence >= 80
                          ? "bg-emerald-500"
                          : confidence >= 60
                            ? "bg-amber-500"
                            : "bg-red-500"
                      }`}
                      style={{ width: `${confidence}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold text-[var(--text)]">
                    {confidence}%
                  </span>
                </div>
              </div>

              {/* Date */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                  Scanned
                </p>
                <p className="text-sm font-medium text-[var(--text)]">
                  {new Date(data.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </p>
              </div>

              {/* Time */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                  Time
                </p>
                <p className="text-sm font-medium text-[var(--text)]">
                  {new Date(data.created_at).toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>

              {/* Model source */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                  Model
                </p>
                <div className="flex items-center gap-1.5 text-sm font-medium text-[var(--text)]">
                  <Microscope className="w-4 h-4" />
                  {data.fallback_used ? "Gemini AI" : "CNN"}
                </div>
              </div>
            </div>

            {/* Fallback notice */}
            {data.fallback_used && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <Zap className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-blue-900 dark:text-blue-300 text-sm">
                    Gemini AI Analysis Used
                  </p>
                  <p className="text-xs text-blue-800 dark:text-blue-400 mt-1">
                    The primary CNN model had lower confidence, so Gemini AI was
                    used for more detailed analysis.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Treatment advice section */}
        {aiResponse && (
          <div className="card p-8 animate-fade-up stagger-1">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-forest-100 dark:bg-forest-900/30 flex items-center justify-center flex-shrink-0">
                <Shield className="w-5 h-5 text-forest-600 dark:text-forest-400" />
              </div>
              <div>
                <h2 className="font-bold text-lg text-[var(--text)]">
                  {isHealthy ? "Plant Care Guide" : "Treatment Advice"}
                </h2>
                {aiResponse.language && (
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    In {aiResponse.language.toUpperCase()}
                  </p>
                )}
              </div>
            </div>

            {/* Format treatment text with better styling */}
            <div className="space-y-4 text-[var(--text)]">
              {aiResponse.precautions_text
                .split("\n")
                .map((line: string, idx: number) => {
                  if (!line.trim()) return null;
                  if (line.startsWith("- ")) {
                    return (
                      <div key={idx} className="flex gap-3">
                        <span className="text-forest-500 dark:text-forest-400 font-bold flex-shrink-0 mt-0.5">
                          •
                        </span>
                        <p className="text-sm leading-relaxed">
                          {line.substring(2)}
                        </p>
                      </div>
                    );
                  }
                  if (line.startsWith("**") && line.includes("**")) {
                    const matched = line.match(/\*\*(.*?)\*\*/);
                    if (matched) {
                      return (
                        <div key={idx}>
                          <p className="font-bold text-sm mb-2 text-forest-600 dark:text-forest-400">
                            {matched[1]}
                          </p>
                        </div>
                      );
                    }
                  }
                  return (
                    <p key={idx} className="text-sm leading-relaxed">
                      {line}
                    </p>
                  );
                })}
            </div>
          </div>
        )}

        {/* Alternative responses */}
        {data.ai_responses?.length > 1 && (
          <div className="card p-8 animate-fade-up stagger-2">
            <h3 className="font-bold text-lg text-[var(--text)] mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5 text-forest-600 dark:text-forest-400" />
              Advice in other languages
            </h3>
            <div className="grid sm:grid-cols-2 gap-4">
              {data.ai_responses.slice(1).map((r: any) => (
                <div
                  key={r.id}
                  className="p-4 rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)]/50 hover:bg-[var(--bg-subtle)] transition-colors space-y-3"
                >
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-[var(--text-muted)]" />
                    <span className="font-bold text-sm text-[var(--text)]">
                      {r.language.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text)] leading-relaxed line-clamp-3">
                    {r.precautions_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
