"use client"
import { motion } from "framer-motion"
import Link from "next/link"
import Image from "next/image"

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

  return (
    <section className="w-full px-6 md:px-12 pt-32 pb-24 bg-transparent relative overflow-hidden">
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
                    priority
                    sizes="192px"
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
                    priority
                    sizes="192px"
                    className="object-cover"
                  />
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-20 items-center mb-32 relative">

          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
            className="relative z-10 lg:col-span-5"
          >
            <h1 className="text-[48px] md:text-[64px] leading-[1.1] tracking-tight text-white mb-6 font-light">
              {headline}
            </h1>

            <p className="text-[17px] leading-relaxed text-gray-400 mb-10 font-light">
              {subheadline}
            </p>

            <Link
              href={primaryButtonHref}
              className="inline-block text-white bg-[#0d9488] rounded-xl px-8 py-4 text-[15px] font-medium transition-all duration-200 hover:bg-[#0f766e] hover:shadow-lg hover:shadow-[#0d9488]/30 hover:scale-105 cursor-pointer"
            >
              {primaryButtonText}
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
            className="relative z-10 lg:col-span-7"
          >
            <div className="relative w-full aspect-video bg-white/5 backdrop-blur-sm rounded-[40px] overflow-hidden shadow-2xl border border-white/10">
              {videoSrc ? (
                <video
                  src={videoSrc}
                  autoPlay
                  muted
                  loop
                  playsInline
                  poster={posterSrc || undefined}
                  className="w-full h-full object-cover"
                />
              ) : (
                <Image
                  src="/hero-demo.png"
                  alt="Fold App Demo"
                  fill
                  priority
                  sizes="(max-width: 1024px) 100vw, 60vw"
                  className="object-cover"
                />
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
