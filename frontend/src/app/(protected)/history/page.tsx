"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Leaf,
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Zap,
  Search,
  Filter,
  ExternalLink,
} from "lucide-react";
import toast from "react-hot-toast";
import { getHistory } from "@/lib/api";
import type { HistoryItem } from "@/types";

const PAGE_SIZE = 12;

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchHistory(page);
  }, [page]);

  async function fetchHistory(p: number) {
    setLoading(true);
    try {
      const data = await getHistory(p, PAGE_SIZE);
      setItems(data.items);
      setTotal(data.total);
      setHasNext(data.has_next);
    } catch {
      toast.error("Failed to load history");
    } finally {
      setLoading(false);
    }
  }

  const filtered = search.trim()
    ? items.filter(
        (i) =>
          i.plant_name?.toLowerCase().includes(search.toLowerCase()) ||
          i.disease_name?.toLowerCase().includes(search.toLowerCase()),
      )
    : items;

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl sm:text-3xl font-semibold text-[var(--text)]">
            Scan history
          </h1>
          <p className="text-[var(--text-muted)] text-sm mt-0.5">
            {total > 0
              ? `${total} total scan${total !== 1 ? "s" : ""}`
              : "No scans yet"}
          </p>
        </div>

        {/* Search */}
        <div className="relative sm:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
          <input
            className="input pl-9 py-2 text-sm"
            placeholder="Search by plant or disease..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Stats strip */}
      {total > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {[
            {
              label: "Total scans",
              value: total,
              icon: Filter,
              color: "text-[var(--green)]",
              bg: "bg-[var(--green-light)]",
            },
            {
              label: "Diseases found",
              value: items.filter(
                (i) =>
                  i.is_plant && i.disease_name?.toLowerCase() !== "healthy",
              ).length,
              icon: AlertTriangle,
              color: "text-amber-600 dark:text-amber-400",
              bg: "bg-amber-50 dark:bg-amber-900/20",
            },
            {
              label: "Healthy plants",
              value: items.filter(
                (i) => i.disease_name?.toLowerCase() === "healthy",
              ).length,
              icon: CheckCircle2,
              color: "text-emerald-600 dark:text-emerald-400",
              bg: "bg-emerald-50 dark:bg-emerald-900/20",
            },
          ].map(({ label, value, icon: Icon, color, bg }) => (
            <div key={label} className="card p-4 flex items-center gap-3">
              <div
                className={`w-9 h-9 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}
              >
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-[var(--text)] leading-none">
                  {value}
                </p>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">
                  {label}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card p-4 space-y-3 animate-pulse">
              <div className="aspect-video rounded-xl bg-[var(--bg-subtle)]" />
              <div className="h-4 bg-[var(--bg-subtle)] rounded w-3/4" />
              <div className="h-3 bg-[var(--bg-subtle)] rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          search={search}
          total={total}
          onClear={() => setSearch("")}
        />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item, idx) => (
            <HistoryCard
              key={item.upload_id}
              item={item}
              delay={idx * 0.04}
              onClick={() =>
                item.prediction_id &&
                router.push(`/history/${item.prediction_id}`)
              }
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !search && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="w-9 h-9 rounded-xl border border-[var(--border)] flex items-center justify-center
              hover:bg-[var(--bg-subtle)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4 text-[var(--text)]" />
          </button>

          {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
            const p = i + 1;
            return (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-9 h-9 rounded-xl text-sm font-medium transition-colors
                  ${
                    p === page
                      ? "bg-forest-600 dark:bg-forest-500 text-white"
                      : "border border-[var(--border)] text-[var(--text)] hover:bg-[var(--bg-subtle)]"
                  }`}
              >
                {p}
              </button>
            );
          })}

          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasNext}
            className="w-9 h-9 rounded-xl border border-[var(--border)] flex items-center justify-center
              hover:bg-[var(--bg-subtle)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4 text-[var(--text)]" />
          </button>
        </div>
      )}
    </div>
  );
}

function HistoryCard({
  item,
  delay,
  onClick,
}: {
  item: HistoryItem;
  delay: number;
  onClick: () => void;
}) {
  const isHealthy = item.disease_name?.toLowerCase() === "healthy";
  const hasDisease = item.is_plant && !isHealthy && item.disease_name;
  const confidence = Math.round((item.confidence_score || 0) * 100);

  return (
    <div
      className="card overflow-hidden hover:shadow-card-lg transition-all duration-300 cursor-pointer group animate-fade-up h-full flex flex-col"
      style={{ animationDelay: `${delay}s`, animationFillMode: "both" }}
      onClick={onClick}
    >
      {/* Image / placeholder header */}
      <div className="aspect-video bg-gradient-to-br from-forest-400/20 to-leaf-400/10 flex items-center justify-center relative overflow-hidden flex-shrink-0">
        <div className="w-16 h-16 rounded-2xl bg-[var(--green-light)] flex items-center justify-center">
          <Leaf className="w-8 h-8 text-[var(--green)]" />
        </div>

        {/* Status badge */}
        <div
          className={`absolute top-3 right-3 badge text-xs font-semibold px-3 py-1.5 ${
            !item.is_plant
              ? "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
              : isHealthy
                ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
                : "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
          }`}
        >
          {!item.is_plant ? "Not plant" : isHealthy ? "✓ Healthy" : "⚠ Disease"}
        </div>

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-forest-900/0 group-hover:bg-forest-900/20 transition-all duration-300 flex items-center justify-center">
          <div className="bg-white/20 backdrop-blur-sm rounded-full p-2">
            <ExternalLink className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </div>

      {/* Card content */}
      <div className="p-4 space-y-3 flex-grow flex flex-col">
        {/* Plant name and disease */}
        <div className="space-y-1.5">
          <p className="font-bold text-[var(--text)] text-sm line-clamp-2">
            {item.plant_name ?? "Unknown plant"}
          </p>
          <p
            className={`text-xs line-clamp-2 font-medium ${
              hasDisease
                ? "text-amber-600 dark:text-amber-400"
                : isHealthy
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-[var(--text-muted)]"
            }`}
          >
            {item.disease_name ??
              (item.is_plant ? "No disease detected" : "Invalid image")}
          </p>
        </div>

        {/* Confidence bar if available */}
        {item.confidence_score && item.is_plant && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-[var(--text-muted)]">
                Confidence
              </p>
              <span className="text-xs font-bold text-[var(--text)]">
                {confidence}%
              </span>
            </div>
            <div className="h-1.5 bg-[var(--bg-subtle)] rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  confidence >= 80
                    ? "bg-emerald-500"
                    : confidence >= 60
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${confidence}%` }}
              />
            </div>
          </div>
        )}

        {/* Footer with timestamp and model indicator */}
        <div className="flex items-center justify-between text-xs text-[var(--text-muted)] pt-2 mt-auto border-t border-[var(--border)]">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {new Date(item.uploaded_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })}
          </div>
          {item.fallback_used && (
            <div
              title="Analyzed with Gemini AI"
              className="flex items-center gap-1 text-blue-500"
            >
              <Zap className="w-3 h-3" />
              Gemini
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({
  search,
  total,
  onClear,
}: {
  search: string;
  total: number;
  onClear: () => void;
}) {
  const router = useRouter();

  if (search)
    return (
      <div className="text-center py-16">
        <p className="text-[var(--text-muted)] mb-3">
          No results for &ldquo;{search}&rdquo;
        </p>
        <button onClick={onClear} className="btn-ghost text-sm py-2 px-4">
          Clear search
        </button>
      </div>
    );

  return (
    <div className="text-center py-20">
      <div className="w-16 h-16 rounded-2xl bg-[var(--green-light)] flex items-center justify-center mx-auto mb-4">
        <Leaf className="w-7 h-7 text-[var(--green)]" />
      </div>
      <h3 className="font-display text-xl font-semibold text-[var(--text)] mb-2">
        No scans yet
      </h3>
      <p className="text-[var(--text-muted)] text-sm mb-6 max-w-xs mx-auto">
        Upload your first plant photo to get an AI-powered disease diagnosis.
      </p>
      <button onClick={() => router.push("/dashboard")} className="btn-primary">
        Start scanning
      </button>
    </div>
  );
}
