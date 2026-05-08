"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { Marquee } from "@/components/ui/marquee";

export function LandingDefinitionSections() {
  const [activeStep, setActiveStep] = useState(0);

  const chips = [
    "UPI screenshots",
    "Receipt OCR",
    "Hinglish voice notes",
    "Auto categorization",
    "Cash flow detection",
    "Merchant extraction",
    "Bank + wallet support",
    "Export anytime",
  ];

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
            className="text-center mb-20"
          >
            <h2 className="text-[40px] md:text-[52px] leading-[1.1] tracking-tight text-white mb-5 font-light">
              Track spending in 30 seconds.
            </h2>
            <p className="text-[17px] leading-relaxed text-gray-400 font-light max-w-2xl mx-auto">
              Fold turns messy receipts, UPI screenshots, and quick voice notes into clean, categorized transactions.
            </p>
          </motion.div>

          {/* Zigzag Flow with Images */}
          <div className="relative space-y-12 md:space-y-0">
            {/* Step 1: Add an expense - Left aligned */}
            <div className="relative md:grid md:grid-cols-2 md:gap-16 items-center mb-12 md:mb-32">
              <motion.div
                initial={{ opacity: 0, x: -40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                className="relative rounded-3xl border border-white/10 overflow-hidden group hover:border-[#0d9488]/50 transition-all duration-500 mb-8 md:mb-0"
                style={{ minHeight: "400px" }}
              >
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/60" />
                <div className="absolute inset-0 flex items-center justify-center p-8">
                  <img
                    src="/expense.png"
                    alt="Add an expense"
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-700"
                  />
                </div>
                <div className="absolute top-6 left-6 z-10">
                  <span className="text-xs font-semibold tracking-wider text-[#0d9488] bg-[#0d9488]/20 px-3 py-1 rounded-full border border-[#0d9488]/30">
                    01
                  </span>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-4"
              >
                <h3 className="text-[28px] md:text-[36px] font-semibold tracking-tight text-white">
                  Add an expense
                </h3>
                <p className="text-[16px] md:text-[18px] leading-relaxed text-white/80 font-light">
                  Type, upload an image, or record audio. Hinglish is supported.
                </p>
              </motion.div>

              {/* Connector Line - Desktop only */}
              <div className="hidden md:block absolute -bottom-16 left-1/2 w-px h-32">
                <div 
                  className="w-full h-full border-l-2 border-dashed border-[#0d9488]"
                  style={{ 
                    borderColor: '#0d9488',
                    opacity: 0.8,
                    animation: 'dash 20s linear infinite'
                  }}
                />
              </div>
            </div>

            {/* Step 2: AI extracts - Right aligned */}
            <div className="relative md:grid md:grid-cols-2 md:gap-16 items-center mb-12 md:mb-32">
              <motion.div
                initial={{ opacity: 0, x: -40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-4 md:order-1 mb-8 md:mb-0"
              >
                <h3 className="text-[28px] md:text-[36px] font-semibold tracking-tight text-white">
                  AI extracts the details
                </h3>
                <p className="text-[16px] md:text-[18px] leading-relaxed text-white/80 font-light">
                  Amount, merchant, payment method, cash-flow — automatically.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                className="relative rounded-3xl border border-white/10 overflow-hidden group hover:border-[#0d9488]/50 transition-all duration-500 md:order-2"
                style={{ minHeight: "400px" }}
              >
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/60" />
                <div className="absolute inset-0 flex items-center justify-center p-8">
                  <img
                    src="/ai_extraction.png"
                    alt="AI extracts details"
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-700"
                  />
                </div>
                <div className="absolute top-6 left-6 z-10">
                  <span className="text-xs font-semibold tracking-wider text-[#0d9488] bg-[#0d9488]/20 px-3 py-1 rounded-full border border-[#0d9488]/30">
                    02
                  </span>
                </div>
              </motion.div>

              {/* Connector Line - Desktop only */}
              <div className="hidden md:block absolute -bottom-16 left-1/2 w-px h-32">
                <div 
                  className="w-full h-full border-l-2 border-dashed border-[#0d9488]"
                  style={{ 
                    borderColor: '#0d9488',
                    opacity: 0.8,
                    animation: 'dash 20s linear infinite'
                  }}
                />
              </div>
            </div>

            {/* Step 3: Get instant clarity - Left aligned */}
            <div className="relative md:grid md:grid-cols-2 md:gap-16 items-center">
              <motion.div
                initial={{ opacity: 0, x: -40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                className="relative rounded-3xl border border-white/10 overflow-hidden group hover:border-[#0d9488]/50 transition-all duration-500 mb-8 md:mb-0"
                style={{ minHeight: "400px" }}
              >
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/60" />
                <div className="absolute inset-0 flex items-center justify-center p-8">
                  <img
                    src="/detailed_records.png"
                    alt="Get instant clarity"
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-700"
                  />
                </div>
                <div className="absolute top-6 left-6 z-10">
                  <span className="text-xs font-semibold tracking-wider text-[#0d9488] bg-[#0d9488]/20 px-3 py-1 rounded-full border border-[#0d9488]/30">
                    03
                  </span>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
                className="space-y-4"
              >
                <h3 className="text-[28px] md:text-[36px] font-semibold tracking-tight text-white">
                  Get instant clarity
                </h3>
                <p className="text-[16px] md:text-[18px] leading-relaxed text-white/80 font-light">
                  See categories, trends, and top spends across weekly or monthly views.
                </p>
              </motion.div>
            </div>
          </div>
        </div>

        {/* Add keyframe animation for dashed line */}
        <style jsx>{`
          @keyframes dash {
            to {
              stroke-dashoffset: -100;
            }
          }
        `}</style>
      </section>


      {/* Built for India Section */}
      <section className="w-full px-8 md:px-16 lg:px-20 py-20 bg-transparent relative">
        <div className="w-full">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="flex items-center justify-center gap-3 text-xs uppercase tracking-[0.22em] text-gray-500 mb-8">
              <span className="h-px w-10 bg-white/10" />
              Built for India
              <span className="h-px w-10 bg-white/10" />
            </div>

            <Marquee durationSeconds={18} className="py-2 mb-14">
              <div className="flex items-center gap-3 pr-3">
                {chips.map((label) => (
                  <div
                    key={label}
                    className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-gray-200 backdrop-blur-sm"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-[#0d9488]" />
                    <span className="whitespace-nowrap">{label}</span>
                  </div>
                ))}
              </div>
            </Marquee>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  title: "Multi-input",
                  desc: "Type, upload, or speak — all in one place.",
                  extendedDesc: "Seamlessly add expenses through text, voice notes in Hinglish, or by uploading receipt images. Choose the method that works best for you in the moment.",
                  image: "/multi_input.png",
                },
                {
                  title: "Accurate extraction",
                  desc: "Merchant, amount, method — pulled automatically.",
                  extendedDesc: "Our AI intelligently extracts merchant names, transaction amounts, payment methods, and categories from any input format without manual entry.",
                  image: "/input_extraction.png",
                },
                {
                  title: "Smart categories",
                  desc: "Clean charts and reports, without manual cleanup.",
                  extendedDesc: "Automatically organize expenses into meaningful categories. Get instant insights through visual charts and detailed reports that help you understand spending patterns.",
                  image: "/categorization.png",
                },
                {
                  title: "Private by default",
                  desc: "Your data stays yours. Built with security in mind.",
                  extendedDesc: "Your financial data is encrypted and stored securely. You have complete control to review, edit, export, or delete your information at any time.",
                  image: "/privacy.png",
                },
              ].map((card, index) => (
                <motion.div
                  key={card.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ duration: 0.6, delay: 0.1 * index, ease: [0.22, 1, 0.36, 1] }}
                  whileHover={{ y: -6 }}
                  className="group relative rounded-3xl border border-white/10 overflow-hidden backdrop-blur-sm shadow-lg hover:border-[#0d9488]/50 transition-all duration-500"
                  style={{ minHeight: "480px" }}
                >
                  {/* Transparent background with subtle gradient */}
                  <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/40" />
                  
                  {/* Hover glow effect */}
                  <div className="absolute inset-0 bg-gradient-to-br from-[#0d9488]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  
                  {/* Content */}
                  <div className="relative h-full flex flex-col items-center justify-center p-8 text-center">
                    {/* Large centered image */}
                    <div className="mb-8 w-28 h-28 flex items-center justify-center">
                      <img
                        src={card.image}
                        alt={card.title}
                        className="w-full h-full object-contain group-hover:scale-110 transition-transform duration-500"
                      />
                    </div>
                    
                    {/* Title */}
                    <h4 className="text-[22px] md:text-[24px] font-bold text-white mb-4 tracking-tight">
                      {card.title}
                    </h4>
                    
                    {/* Short Description */}
                    <p className="text-[15px] leading-relaxed text-white/90 font-medium mb-3">
                      {card.desc}
                    </p>
                    
                    {/* Extended Description */}
                    <p className="text-[13px] leading-relaxed text-gray-400 font-light">
                      {card.extendedDesc}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>


      <section
        id="who-can-use"
        className="w-full px-6 md:px-12 py-28 bg-transparent relative"
      >
        <div className="max-w-[1600px] mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="text-center mb-16"
          >
            <h2 className="text-[40px] md:text-[52px] leading-[1.1] tracking-tight text-white mb-5 font-light">
              Built for everyone
            </h2>
          </motion.div>

          {/* Bento Grid - 3 Vertical Columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                image: "/studet_image.png",
                title: "STUDENTS",
                description: "Track daily expenses, manage pocket money, and stay on budget effortlessly",
              },
              {
                image: "/everyday_person.png",
                title: "EVERYDAY USERS",
                description: "Monitor household spending, bills, and personal finances in one place",
              },
              {
                image: "/account_tracker.png",
                title: "ACCOUNT TRACKERS",
                description: "Maintain detailed records, analyze patterns, and export data for reporting",
              },
            ].map((card, index) => (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.6, delay: 0.1 * index, ease: [0.22, 1, 0.36, 1] }}
                className="relative rounded-3xl border border-white/10 overflow-hidden group hover:border-[#0d9488]/50 transition-all duration-500"
                style={{ height: "65vh", minHeight: "550px" }}
              >
                {/* Background with subtle gradient */}
                <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-black/20 to-black/60" />
                
                {/* Image - positioned higher with more bottom margin */}
                <div className="absolute inset-0 flex items-center justify-center pb-32">
                  <img
                    src={card.image}
                    alt={card.title}
                    className="w-full h-full object-contain p-8 group-hover:scale-105 transition-transform duration-700"
                  />
                </div>

                {/* Text Content - Pinned to Bottom with more padding */}
                <div className="absolute bottom-0 left-0 right-0 p-10 z-10">
                  <div className="space-y-4">
                    <h3 className="text-[24px] md:text-[28px] font-semibold tracking-tight text-white">
                      {card.title}
                    </h3>
                    <p className="text-[15px] md:text-[16px] leading-relaxed text-white/90 font-light">
                      {card.description}
                    </p>
                  </div>
                </div>

                {/* Subtle glow effect on hover */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
                  <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-[#0d9488]/20 to-transparent" />
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
