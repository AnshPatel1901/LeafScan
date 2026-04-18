"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Leaf,
  Zap,
  Globe,
  Shield,
  ChevronRight,
  Microscope,
  Sprout,
} from "lucide-react";
import ThemeToggle from "@/components/ui/ThemeToggle";

const LANGUAGES = [
  "English",
  "हिंदी",
  "தமிழ்",
  "বাংলা",
  "Español",
  "Français",
  "中文",
  "اردو",
];
const DISEASES = [
  "Early Blight",
  "Late Blight",
  "Powdery Mildew",
  "Leaf Rust",
  "Mosaic Virus",
  "Downy Mildew",
];

export default function LandingPage() {
  const [langIdx, setLangIdx] = useState(0);
  const [diseaseIdx, setDiseaseIdx] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(true);
  }, []);

  useEffect(() => {
    const t1 = setInterval(
      () => setLangIdx((i) => (i + 1) % LANGUAGES.length),
      1800,
    );
    const t2 = setInterval(
      () => setDiseaseIdx((i) => (i + 1) % DISEASES.length),
      2200,
    );
    return () => {
      clearInterval(t1);
      clearInterval(t2);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg)] overflow-x-hidden">
      {/* ── Nav ─────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-md bg-[var(--bg)]/80 border-b border-[var(--border)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-forest-600 dark:bg-forest-500 rounded-lg flex items-center justify-center">
              <Leaf className="w-4 h-4 text-white" />
            </div>
            <span className="font-display font-semibold text-lg text-[var(--text)]">
              LeafScan
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/auth/login"
              className="btn-ghost text-sm py-2 px-4 hidden sm:inline-flex"
            >
              Sign in
            </Link>
            <Link href="/auth/signup" className="btn-primary text-sm py-2 px-4">
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="pt-32 pb-20 px-4 sm:px-6 max-w-6xl mx-auto">
        <div
          className={`transition-all duration-700 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}
        >
          {/* Eyebrow */}
          <div className="flex justify-center mb-6">
            <span className="badge bg-[var(--green-light)] text-[var(--green)] border border-[var(--green)]/20">
              <Zap className="w-3 h-3" /> AI-Powered Plant Diagnosis
            </span>
          </div>

          {/* Main headline */}
          <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-semibold text-center leading-[1.08] tracking-tight text-[var(--text)] mb-6">
            Detect crop diseases{" "}
            <span className="italic text-[var(--green)]">instantly</span>
          </h1>
          <p className="text-center text-[var(--text-muted)] text-lg sm:text-xl max-w-2xl mx-auto mb-4 leading-relaxed">
            Upload a photo of any plant. Our AI identifies diseases, pests, and
            deficiencies in seconds — with treatment advice in{" "}
            <span
              key={langIdx}
              className="inline-block font-semibold text-[var(--green)] animate-fade-in min-w-[80px]"
            >
              {LANGUAGES[langIdx]}
            </span>
            .
          </p>

          {/* CTA row */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-10">
            <Link
              href="/auth/signup"
              className="btn-primary flex items-center gap-2 text-base py-3.5 px-7"
            >
              Start for free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/auth/login"
              className="btn-ghost flex items-center gap-2 text-base py-3.5 px-7"
            >
              Sign in <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* ── Mock UI card ──────────────────────────────────────────────── */}
        <div
          className={`mt-16 transition-all duration-700 delay-200 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"}`}
        >
          <div className="card shadow-card-lg max-w-2xl mx-auto overflow-hidden">
            {/* Mock toolbar */}
            <div className="h-10 bg-[var(--bg-subtle)] border-b border-[var(--border)] flex items-center px-4 gap-2">
              <span className="w-3 h-3 rounded-full bg-red-400/70" />
              <span className="w-3 h-3 rounded-full bg-yellow-400/70" />
              <span className="w-3 h-3 rounded-full bg-green-400/70" />
              <span className="flex-1 mx-3 h-5 bg-[var(--border)] rounded-md text-xs flex items-center px-3 text-[var(--text-muted)] font-body">
                leafscan.app/dashboard
              </span>
            </div>
            {/* Mock content */}
            <div className="p-6 space-y-4">
              <div className="flex items-start gap-4">
                {/* Mock image preview */}
                <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-forest-400/30 to-leaf-400/20 flex-shrink-0 flex items-center justify-center border border-[var(--border)]">
                  <Sprout className="w-8 h-8 text-forest-500 dark:text-forest-400" />
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="badge bg-[var(--green-light)] text-[var(--green)]">
                      <Leaf className="w-3 h-3" /> Tomato Plant
                    </span>
                    <span className="badge bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400">
                      {DISEASES[diseaseIdx]}
                    </span>
                  </div>
                </div>
              </div>
              <div className="rounded-xl bg-[var(--bg-subtle)] p-4 text-sm text-[var(--text-muted)] leading-relaxed">
                <span className="font-semibold text-[var(--text)]">
                  Treatment advice:
                </span>{" "}
                Apply copper-based fungicide spray every 7–10 days. Remove
                infected leaves immediately and improve air circulation around
                the plant...
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────────────────── */}
      <section className="py-20 px-4 sm:px-6 max-w-6xl mx-auto">
        <h2 className="font-display text-3xl sm:text-4xl font-semibold text-center mb-3 text-[var(--text)]">
          Everything a farmer needs
        </h2>
        <p className="text-center text-[var(--text-muted)] mb-14 max-w-xl mx-auto">
          Built on state-of-the-art AI with an easy-to-use interface that works
          on any device.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            {
              icon: Microscope,
              title: "AI Disease Detection",
              desc: "Custom CNN model identifies 38+ crop diseases with high accuracy. Falls back to Gemini AI when uncertain.",
              color: "text-forest-600 dark:text-forest-400",
              bg: "bg-[var(--green-light)]",
            },
            {
              icon: Globe,
              title: "Multilingual Support",
              desc: "Get diagnosis and treatment advice in 15+ languages including Hindi, Tamil, Bengali, and more.",
              color: "text-blue-600 dark:text-blue-400",
              bg: "bg-blue-50 dark:bg-blue-900/20",
            },
            {
              icon: Zap,
              title: "Instant Results",
              desc: "Get your diagnosis in under 10 seconds. Upload, analyze, and read — all from your phone.",
              color: "text-amber-600 dark:text-amber-400",
              bg: "bg-amber-50 dark:bg-amber-900/20",
            },
            {
              icon: Shield,
              title: "Secure & Private",
              desc: "JWT-based authentication, encrypted data. Your farm data stays private and secure.",
              color: "text-purple-600 dark:text-purple-400",
              bg: "bg-purple-50 dark:bg-purple-900/20",
            },
            {
              icon: Leaf,
              title: "Crop History",
              desc: "Track all your plant analyses over time. Review past diagnoses and treatment outcomes.",
              color: "text-emerald-600 dark:text-emerald-400",
              bg: "bg-emerald-50 dark:bg-emerald-900/20",
            },
            {
              icon: Sprout,
              title: "Precaution Guide",
              desc: "Detailed step-by-step treatment plans and prevention strategies from our AI agronomist.",
              color: "text-teal-600 dark:text-teal-400",
              bg: "bg-teal-50 dark:bg-teal-900/20",
            },
          ].map(({ icon: Icon, title, desc, color, bg }) => (
            <div
              key={title}
              className="card p-6 hover:shadow-card-lg transition-shadow duration-300"
            >
              <div
                className={`w-11 h-11 rounded-xl ${bg} flex items-center justify-center mb-4`}
              >
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <h3 className="font-body font-semibold text-[var(--text)] mb-2">
                {title}
              </h3>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                {desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA Banner ──────────────────────────────────────────────────── */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="card p-10 shadow-leaf bg-gradient-to-br from-forest-600 to-forest-700 border-0">
            <h2 className="font-display text-3xl sm:text-4xl font-semibold text-white mb-3">
              Ready to protect your crops?
            </h2>
            <p className="text-forest-200 mb-8 max-w-md mx-auto">
              Join thousands of farmers using AI to detect and treat plant
              diseases early.
            </p>
            <Link
              href="/auth/signup"
              className="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-forest-700 rounded-xl font-semibold text-sm hover:bg-cream-100 transition-colors"
            >
              Create free account <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-[var(--border)] py-8 px-4 text-center text-sm text-[var(--text-muted)]">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Leaf className="w-4 h-4 text-forest-500" />
          <span className="font-display font-medium text-[var(--text)]">
            LeafScan
          </span>
        </div>
        <p>AI-powered crop disease detection. Built for farmers.</p>
      </footer>
    </div>
  );
}
