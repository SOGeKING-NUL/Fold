"use client";

import { motion } from "framer-motion";
import { useState } from "react";

export function LandingDefinitionSections() {
  const [activeStep, setActiveStep] = useState(0);

  return (
    <>
      <section
        id="how-it-works"
        className="w-full px-6 md:px-12 py-28 bg-transparent relative"
      >
        <div className="max-w-350 mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="text-center mb-16"
          >
            <h2 className="text-[40px] md:text-[52px] leading-[1.1] tracking-tight text-white mb-5 font-light">
              Track spending in 30 seconds.
            </h2>
            <p className="text-[17px] leading-relaxed text-gray-400 font-light max-w-2xl mx-auto">
              Fold turns messy receipts, UPI screenshots, and quick voice notes into clean, categorized transactions.
            </p>
          </motion.div>

          {/* Interactive Visual Flow */}
          <div className=" gap-12 items-center mb-20">
            {/* Left: Step Cards */}
            <div className="space-y-4">
              {[
                {
                  step: "01",
                  title: "Add an expense",
                  desc: "Type, upload an image, or record audio. Hinglish is supported.",
                  icon: (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  ),
                },
                {
                  step: "02",
                  title: "AI extracts the details",
                  desc: "Amount, merchant, payment method, cash-flow — automatically.",
                  icon: (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                      <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ),
                },
                {
                  step: "03",
                  title: "Get instant clarity",
                  desc: "See categories, trends, and top spends across weekly or monthly views.",
                  icon: (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M3 3v18h18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                      <path d="M7 16l4-4 3 3 5-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ),
                },
              ].map((item, index) => (
                <motion.div
                  key={item.step}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ duration: 0.55, delay: 0.1 * index, ease: [0.22, 1, 0.36, 1] }}
                  onMouseEnter={() => setActiveStep(index)}
                  className={`group relative rounded-2xl border transition-all duration-300 cursor-pointer p-6 ${
                    activeStep === index
                      ? "border-[#0d9488] bg-[#0d9488]/10 shadow-lg shadow-[#0d9488]/20"
                      : "border-white/10 bg-white/5 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`h-12 w-12 rounded-xl flex items-center justify-center border transition-all duration-300 ${
                      activeStep === index
                        ? "border-[#0d9488] bg-[#0d9488] text-white"
                        : "border-white/10 bg-black/20 text-[#0d9488]"
                    }`}>
                      {item.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold tracking-wider text-gray-500">{item.step}</span>
                        <div className="h-px flex-1 bg-white/10" />
                      </div>
                      <div className="text-[18px] font-normal text-white mb-1">{item.title}</div>
                      <div className="text-sm leading-relaxed text-gray-400 font-light">
                        {item.desc}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

          </div>
        </div>
      </section>


      <section
        id="security"
        className="w-full px-6 md:px-12 py-28 bg-transparent relative"
      >
        <div className="max-w-350 mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-110px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8"
          >
            <div className="max-w-2xl">
              <h3 className="text-[34px] md:text-[42px] leading-[1.15] tracking-tight text-white mb-4 font-light">
                Private by default. You stay in control.
              </h3>
              <p className="text-[16px] leading-relaxed text-gray-400 font-light">
                Fold is designed to keep your financial history yours. You can review, correct, export, or delete your
                data anytime.
              </p>
            </div>

            <div className="h-1 w-44 rounded-full bg-linear-to-r from-[#0d9488] to-[#0f766e] opacity-80" />
          </motion.div>

          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                title: "Secure sessions",
                desc: "Sign in with Clerk and keep access scoped to your account.",
              },
              {
                title: "Edit anything",
                desc: "Fix categories or merchants — your reports update instantly.",
              },
              {
                title: "Export anytime",
                desc: "Download your transactions for backups and budgeting.",
              },
              {
                title: "Delete data",
                desc: "Remove entries you don’t want to keep — you decide.",
              },
            ].map((card, index) => (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.55, delay: 0.04 * index, ease: [0.22, 1, 0.36, 1] }}
                className="relative rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6 shadow-lg overflow-hidden"
              >
                <div className="absolute -top-12 -right-12 h-28 w-28 rounded-full blur-2xl opacity-30 bg-linear-to-r from-[#0d9488] to-[#0f766e]" />
                <div className="relative">
                  <div className="h-10 w-10 rounded-xl border border-white/10 bg-black/20 flex items-center justify-center">
                    <div className="h-2.5 w-2.5 rounded-full bg-linear-to-r from-[#0d9488] to-[#0f766e]" />
                  </div>
                  <div className="mt-4 text-[15px] font-normal text-white">{card.title}</div>
                  <div className="mt-2 text-sm leading-relaxed text-gray-400 font-light">
                    {card.desc}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="help" className="sr-only" />
      <section id="docs" className="sr-only" />
      <section id="api" className="sr-only" />
      <section id="telegram" className="sr-only" />
      <section id="privacy" className="sr-only" />
      <section id="terms" className="sr-only" />
      <section id="data" className="sr-only" />
    </>
  );
}
