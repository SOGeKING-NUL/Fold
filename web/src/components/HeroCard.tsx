"use client"
import { motion } from "framer-motion"
import Link from "next/link"
import Image from "next/image"
import { Marquee } from "@/components/ui/marquee"

type ProductTeaserCardProps = {
  headline?: string
  subheadline?: string
  primaryButtonText?: string
  primaryButtonHref?: string
  videoSrc?: string
  posterSrc?: string
}

export const HeroCard = (props: ProductTeaserCardProps) => {
  const {
    headline = "Stop recording expenses manually.",
    subheadline = "Fold automatically categorizes your expenses. Upload receipts, record voice notes, or simply type. Focus on what matters.",
    primaryButtonText = "Start Tracking",
    primaryButtonHref = "/chat",
    videoSrc = "",
    posterSrc = "",
  } = props

  const chips = [
    "UPI screenshots",
    "Receipt OCR",
    "Hinglish voice notes",
    "Auto categorization",
    "Cash flow detection",
    "Merchant extraction",
    "Bank + wallet support",
    "Export anytime",
  ]

  return (
    <section className="w-full px-6 md:px-12 pt-32 pb-24 bg-transparent relative">
      <div className="pointer-events-none absolute -top-20 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-blue-500/10 blur-3xl" />
    <div className="pointer-events-none absolute -bottom-40 -right-24 h-96 w-96 rounded-full bg-blue-400/10 blur-3xl" />

      <div className="max-w-350 mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
          className="text-center mb-20"
        >
          <h2 className="text-[40px] md:text-[56px] leading-[1.1] tracking-tight text-white mb-6 font-light">
            It&apos;s just money, after-all.
          </h2>

          <p className="text-[17px] leading-relaxed text-gray-400 max-w-2xl mx-auto font-light">
            A few good habits, some awareness, and tools that don&apos;t make you feel dumb have the power to change everything.
          </p>

          <div className="mt-16 flex justify-center">
            <div className="relative w-48 h-48" style={{ perspective: '1200px' }}>
              <motion.div
                animate={{
                  rotateY: [0, 180, 360],
                  y: [0, -30, 0]
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: [0.45, 0.05, 0.55, 0.95],
                  times: [0, 0.5, 1]
                }}
                className="w-full h-full relative"
                style={{
                  transformStyle: 'preserve-3d',
                }}
              >
                <div
                  className="absolute inset-0 rounded-full overflow-hidden"
                  style={{
                    backfaceVisibility: 'hidden',
                  }}
                >
                  <Image
                    src="/coin1.png"
                    alt="Indian 1 Rupee Coin - Front"
                    fill
                    className="object-cover"
                  />
                </div>
                <div
                  className="absolute inset-0 rounded-full overflow-hidden"
                  style={{
                    backfaceVisibility: 'hidden',
                    transform: 'rotateY(180deg)',
                  }}
                >
                  <Image
                    src="/coin2.png"
                    alt="Indian 1 Rupee Coin - Back"
                    fill
                    className="object-cover"
                  />
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center mb-32 relative">

          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
            className="relative z-10"
          >
            <h1 className="text-[48px] md:text-[64px] leading-[1.1] tracking-tight text-white mb-6 font-light">
              {headline}
            </h1>

            <p className="text-[17px] leading-relaxed text-gray-400 mb-10 font-light">
              {subheadline}
            </p>

            <Link
              href={primaryButtonHref}
              className="inline-block text-white bg-[#1e3a8a] rounded-xl px-8 py-4 text-[15px] font-medium transition-all duration-200 hover:bg-[#1e3a8a] hover:shadow-lg hover:shadow-purple-900/30 hover:scale-105 cursor-pointer"
            >
              {primaryButtonText}
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
            className="relative z-10"
          >
            <div className="relative w-full aspect-video bg-white/5 backdrop-blur-sm rounded-[40px] overflow-hidden shadow-2xl border border-white/10">
              <div className="absolute inset-0 bg-linear-to-r from-transparent via-blue-400/10 to-transparent animate-shimmer"
                style={{
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 3s infinite'
                }}
              />

              {videoSrc ? (
                <video
                  src={videoSrc}
                  autoPlay
                  muted
                  loop
                  playsInline
                  poster={posterSrc}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center relative">
                  <div className="absolute inset-0 opacity-10">
                    <div className="w-full h-full" style={{
                      backgroundImage: `
                        linear-gradient(rgba(96, 165, 250, 0.25) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(96, 165, 250, 0.25) 1px, transparent 1px)
                      `,
                      backgroundSize: '30px 30px'
                    }} />
                  </div>

                  <motion.div
                    animate={{
                      y: [0, -20, 0],
                      opacity: [0.3, 0.6, 0.3]
                    }}
                    transition={{
                      duration: 3,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                    className="absolute top-1/4 left-1/4 w-16 h-16 rounded-full bg-blue-400/20 blur-xl"
                  />
                  <motion.div
                    animate={{
                      y: [0, 20, 0],
                      opacity: [0.3, 0.6, 0.3]
                    }}
                    transition={{
                      duration: 4,
                      repeat: Infinity,
                      ease: "easeInOut",
                      delay: 1
                    }}
                    className="absolute bottom-1/4 right-1/4 w-20 h-20 rounded-full bg-blue-500/20 blur-xl"
                  />

                  <div className="relative z-10 text-center">
                    <div className="text-gray-400 text-sm mb-4">Demo Coming Soon</div>
                    <div className="flex gap-2 justify-center">
                      <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
                      <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse delay-150" />
                      <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse delay-300" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>

        <div className="border-t border-white/10 pt-12">
          <div className="flex items-center justify-center gap-3 text-xs uppercase tracking-[0.22em] text-gray-500 mb-6">
            <span className="h-px w-10 bg-white/10" />
            Built for India
            <span className="h-px w-10 bg-white/10" />
          </div>

          <Marquee durationSeconds={18} className="py-2">
            <div className="flex items-center gap-3 pr-3">
              {chips.map((label) => (
                <div
                  key={label}
                  className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-gray-200 backdrop-blur-sm"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-[#1e3a8a]" />
                  <span className="whitespace-nowrap">{label}</span>
                </div>
              ))}
            </div>
          </Marquee>

          <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                title: "Multi-input",
                desc: "Type, upload, or speak — all in one place.",
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M7 7h10M7 12h6M7 17h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9l-4 3V6a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                  </svg>
                ),
              },
              {
                title: "Accurate extraction",
                desc: "Merchant, amount, method — pulled automatically.",
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M4 7h16M7 4v6M17 4v6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M6 11h5M6 15h9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M5 5h14a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                  </svg>
                ),
              },
              {
                title: "Smart categories",
                desc: "Clean charts and reports, without manual cleanup.",
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M4 20V10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M10 20V4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M16 20v-8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M22 20V8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                  </svg>
                ),
              },
              {
                title: "Private by default",
                desc: "Your data stays yours. Built with security in mind.",
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M7 11V8a5 5 0 0 1 10 0v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    <path d="M6 11h12a2 2 0 0 1 2 2v7H4v-7a2 2 0 0 1 2-2Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                  </svg>
                ),
              },
            ].map((card) => (
              <motion.div
                key={card.title}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="group relative rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm shadow-lg"
              >
                <div className="absolute inset-0 rounded-2xl bg-linear-to-br from-purple-500/10 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                <div className="relative">
                  <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-black/20 text-purple-400">
                    {card.icon}
                  </div>
                  <div className="text-[15px] font-normal text-white">{card.title}</div>
                  <div className="mt-2 text-sm leading-relaxed text-gray-400 font-light">{card.desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .animate-shimmer {
          animation: shimmer 3s infinite;
        }
        .delay-150 {
          animation-delay: 150ms;
        }
        .delay-300 {
          animation-delay: 300ms;
        }
        .delay-1000 {
          animation-delay: 1000ms;
        }
        .delay-2000 {
          animation-delay: 2000ms;
        }
      `}</style>
    </section>
  )
}
