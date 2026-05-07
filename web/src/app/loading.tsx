"use client";

import { useEffect, useMemo, useState } from "react";
import { OrbitalLoader } from "@/components/ui/OrbitalLoader";
import { AsciiWave } from "@/components/ui/AsciiWave";

export default function Loading() {
  const steps = useMemo(
    () => [
      "Securing your session…",
      "Warming up AI extraction…",
      "Preparing your ledger…",
      "Building charts and insights…",
    ],
    [],
  );

  const [index, setIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false);
      window.setTimeout(() => {
        setIndex((prev) => (prev + 1) % steps.length);
        setVisible(true);
      }, 250);
    }, 2600);

    return () => clearInterval(interval);
  }, [steps.length]);

  const progress = ((index + 1) / steps.length) * 100;

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-linear-to-br from-black via-gray-900 to-black relative overflow-hidden">
      <div className="fixed inset-0 opacity-15 pointer-events-none overflow-hidden z-0">
        <AsciiWave className="w-full h-full" />
      </div>

      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute -top-32 -left-24 h-96 w-96 rounded-full bg-[#0d9488]/10 blur-3xl" />
        <div className="absolute top-1/3 -right-24 h-80 w-80 rounded-full bg-[#0f766e]/10 blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 h-96 w-96 rounded-full bg-[#0d9488]/10 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-xl">
        <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-sm shadow-2xl overflow-hidden">
          <div className="p-6 border-b border-white/10 bg-linear-to-r from-[#0d9488] to-[#0f766e]">
            <div className="text-xs uppercase tracking-[0.22em] text-white/85">Fold</div>
            <div className="mt-2 text-2xl md:text-3xl font-semibold text-white">Getting things ready</div>
            <div className="mt-2 text-sm text-white/85">
              We’re preparing your workspace and loading the latest insights.
            </div>
          </div>

          <div className="p-7">
            <div className="flex items-start gap-5">
              <OrbitalLoader />
              <div className="flex-1 min-w-0">
                <div
                  className={`text-base md:text-lg font-medium text-white transition-all duration-250 ${
                    visible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-2"
                  }`}
                >
                  {steps[index]}
                </div>

                <div className="mt-4 flex items-center gap-3">
                  <span className="text-xs text-gray-500 font-mono min-w-14">
                    {index + 1}/{steps.length}
                  </span>
                  <div className="h-1.5 flex-1 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full bg-linear-to-r from-[#0d9488] to-[#0f766e] transition-all duration-500 ease-out"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>

                <div className="mt-3 text-xs text-gray-500">
                  Tip: You can upload receipts, UPI screenshots, or voice notes in the Chat.
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              {[
                "Receipt OCR",
                "UPI detection",
                "Auto categorization",
                "Cash flow insights",
              ].map((label) => (
                <div
                  key={label}
                  className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-gray-200 font-light"
                >
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-linear-to-r from-[#0d9488] to-[#0f766e]" />
                    <span className="truncate">{label}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
