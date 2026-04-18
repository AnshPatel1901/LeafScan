"use client";

import { SUPPORTED_LANGUAGES as LANGUAGES } from "@/types";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  Leaf,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Globe,
  BookOpen,
  FileText,
  ImagePlus,
  RefreshCw,
  ChevronDown,
} from "lucide-react";
import toast from "react-hot-toast";
import Image from "next/image";
import { getApiErrorMessage, predict } from "@/lib/api";
import type { PredictResponse } from "@/types";

type Stage = "idle" | "uploading" | "analyzing" | "done" | "error";

export default function DashboardPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [language, setLanguage] = useState("en");
  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [errMsg, setErrMsg] = useState("");
  const [langOpen, setLangOpen] = useState(false);

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setStage("idle");
    setErrMsg("");
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/jpeg": [], "image/png": [] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    onDropRejected: () =>
      toast.error("Only JPG/PNG files up to 10 MB are accepted"),
  });

  async function handleAnalyze() {
    if (!file) return;
    setStage("uploading");
    setResult(null);
    setErrMsg("");
    try {
      await new Promise((r) => setTimeout(r, 600));
      setStage("analyzing");
      const data = await predict(file, language);
      setResult(data);
      setStage("done");
      if (!data.is_plant) toast.error("This doesn't look like a plant image.");
      else toast.success("Analysis complete! 🌿");
    } catch (err: any) {
      const msg = getApiErrorMessage(err, "Analysis failed. Please try again.");
      setErrMsg(msg);
      setStage("error");
      toast.error(msg);
    }
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setStage("idle");
    setErrMsg("");
  }

  const currentLang = LANGUAGES.find((l) => l.code === language)!;
  const isProcessing = stage === "uploading" || stage === "analyzing";

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-8 py-8 space-y-6">
      <div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold text-[var(--text)]">
          Diagnose a plant
        </h1>
        <p className="text-[var(--text-muted)] text-sm mt-1">
          Upload a clear photo of the plant or affected leaf
        </p>
      </div>

      {/* Upload card */}
      <div className="card p-5 space-y-5">
        {/* Language picker */}
        <div>
          <label className="flex items-center gap-1.5 text-sm font-medium text-[var(--text)] mb-2">
            <Globe className="w-3.5 h-3.5 text-[var(--text-muted)]" />
            Response language
          </label>
          <div className="relative">
            <button
              onClick={() => setLangOpen((v) => !v)}
              className="input flex items-center justify-between text-left"
            >
              <span>
                {currentLang.native}
                <span className="text-[var(--text-muted)] ml-2 text-xs">
                  ({currentLang.label})
                </span>
              </span>
              <ChevronDown
                className={`w-4 h-4 text-[var(--text-muted)] transition-transform ${langOpen ? "rotate-180" : ""}`}
              />
            </button>
            {langOpen && (
              <div className="absolute z-30 top-full left-0 right-0 mt-1.5 card shadow-card-lg max-h-52 overflow-y-auto">
                {LANGUAGES.map((l) => (
                  <button
                    key={l.code}
                    onClick={() => {
                      setLanguage(l.code);
                      setLangOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-[var(--bg-subtle)] transition-colors
                      ${l.code === language ? "text-[var(--green)] font-medium" : "text-[var(--text)]"}`}
                  >
                    <span>{l.native}</span>
                    <span className="text-[var(--text-muted)] text-xs">
                      {l.label}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Dropzone / preview */}
        {!preview ? (
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200
              ${
                isDragActive
                  ? "border-forest-500 bg-[var(--green-light)]"
                  : "border-[var(--border)] hover:border-forest-400 hover:bg-[var(--bg-subtle)]"
              }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-[var(--green-light)] flex items-center justify-center">
                <ImagePlus className="w-6 h-6 text-[var(--green)]" />
              </div>
              <div>
                <p className="font-medium text-[var(--text)] text-sm">
                  {isDragActive
                    ? "Drop the image here"
                    : "Drag & drop or click to upload"}
                </p>
                <p className="text-[var(--text-muted)] text-xs mt-1">
                  JPG or PNG · max 10 MB
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="relative rounded-2xl overflow-hidden border border-[var(--border)] aspect-video bg-[var(--bg-subtle)]">
              <Image
                src={preview}
                alt="Preview"
                fill
                className="object-contain"
              />
              {isProcessing && (
                <div className="absolute inset-0 bg-[var(--bg)]/40 backdrop-blur-[1px] flex flex-col items-center justify-center gap-3">
                  <div className="scan-line" />
                  <div className="w-10 h-10 border-2 border-forest-400 border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm font-medium text-[var(--text)] bg-[var(--bg-card)]/90 px-4 py-1.5 rounded-full">
                    {stage === "uploading"
                      ? "Uploading..."
                      : "AI is analysing..."}
                  </p>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={reset}
                className="btn-ghost flex-1 flex items-center justify-center gap-2 py-2.5 text-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Change image
              </button>
              <button
                onClick={handleAnalyze}
                disabled={isProcessing || stage === "done"}
                className="btn-primary flex-1 flex items-center justify-center gap-2 py-2.5 text-sm"
              >
                {isProcessing ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : stage === "done" ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" /> Done
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" /> Analyse
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {stage === "error" && (
        <div className="card p-5 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-400 text-sm">
              Analysis failed
            </p>
            <p className="text-red-600 dark:text-red-300 text-sm mt-0.5">
              {errMsg}
            </p>
          </div>
        </div>
      )}

      {/* Result */}
      {result && stage === "done" && <ResultCard result={result} />}
    </div>
  );
}

function ResultCard({ result }: { result: PredictResponse }) {
  const isHealthy = result.disease_name?.toLowerCase() === "healthy";
  const langCode = normalizeLanguageCode(result.language);
  const langDisplay =
    LANGUAGES.find((l) => l.code === langCode)?.native ?? result.language;
  const hasRag = Boolean(result.rag_answer) || Boolean(result.rag_sources?.length);

  return (
    <div className="space-y-4 animate-fade-up">
      {!result.is_plant ? (
        <div className="card p-5 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-amber-700 dark:text-amber-400 text-sm">
              Not a plant image
            </p>
            <p className="text-amber-600 dark:text-amber-300 text-sm mt-0.5">
              Please upload a clear photo of a plant or its affected leaf.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Diagnosis */}
          <div className="card p-5">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <p className="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">
                  Diagnosis
                </p>
                <h2 className="font-display text-2xl font-semibold text-[var(--text)]">
                  {result.disease_name ?? "Unknown"}
                </h2>
                <p className="text-sm mt-0.5">
                  <span className="text-forest-600 dark:text-forest-400 font-medium">
                    {result.plant_name}
                  </span>
                </p>
              </div>
              <span
                className={`badge text-sm px-3 py-2 ${
                  isHealthy
                    ? "bg-[var(--green-light)] text-[var(--green)]"
                    : "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400"
                }`}
              >
                {isHealthy ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5" /> Disease
                  </>
                )}
              </span>
            </div>
          </div>

          {/* Precautions */}
          {result.precautions && (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-lg bg-[var(--green-light)] flex items-center justify-center">
                  <Leaf className="w-3.5 h-3.5 text-[var(--green)]" />
                </div>
                <h3 className="font-semibold text-[var(--text)] text-sm">
                  Treatment advice
                </h3>
                <span className="ml-auto badge bg-[var(--bg-subtle)] text-[var(--text-muted)] text-xs">
                  <Globe className="w-3 h-3" />
                  {langDisplay}
                </span>
              </div>
              <div className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-line">
                {result.precautions}
              </div>
            </div>
          )}

          {/* RAG grounded advice */}
          {hasRag && (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                  <BookOpen className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="font-semibold text-[var(--text)] text-sm">
                  RAG knowledge support
                </h3>
              </div>

              {result.rag_answer && (
                <p className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-line">
                  {result.rag_answer}
                </p>
              )}

              {!!result.rag_sources?.length && (
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
                    Sources
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {result.rag_sources.slice(0, 5).map((source) => (
                      <span
                        key={source}
                        className="badge bg-[var(--bg-subtle)] text-[var(--text-muted)] text-xs"
                      >
                        <FileText className="w-3 h-3" />
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {!!result.rag_documents?.length && (
                <div className="mt-4 space-y-2">
                  {result.rag_documents.slice(0, 3).map((doc, idx) => (
                    <div
                      key={`${doc.source}-${doc.page ?? idx}`}
                      className="rounded-xl border border-[var(--border)] p-3 bg-[var(--bg-subtle)]/40"
                    >
                      <p className="text-xs font-medium text-[var(--text)]">
                        {doc.source}
                        {doc.page ? ` • p.${doc.page}` : ""}
                      </p>
                      {doc.preview && (
                        <p className="text-xs text-[var(--text-muted)] mt-1 leading-relaxed">
                          {doc.preview}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function normalizeLanguageCode(code?: string | null): string {
  if (!code) return "en";
  return code.trim().toLowerCase().split("-")[0];
}
