"use client"
import { motion } from "framer-motion"
import Link from "next/link"
import Image from "next/image"

type ProductTeaserCardProps = {
  dailyVolumeLabel?: string
  headline?: string
  subheadline?: string
  primaryButtonText?: string
  primaryButtonHref?: string
  videoSrc?: string
  posterSrc?: string
}

export const HeroCard = (props: ProductTeaserCardProps) => {
  const {
    dailyVolumeLabel = "No Email scraping\n\nNo SMS scraping",
    headline = "Stop recording expenses manually.",
    subheadline = "It's easy to forget, fall off the wagon, and miss. It's hard to be diligent with expense tracking when you have to do it manually. Fold automatically pulls your expenses from your Bank accounts and categorises them. So you can relax and focus on things that are more important than tracking expenses.",
    primaryButtonText = "Start Tracking",
    primaryButtonHref = "/chat",
    videoSrc = "",
    posterSrc = "",
  } = props

  return (
    <section className="w-full px-6 md:px-12 pt-32 pb-24 bg-white">
      <div className="max-w-[1400px] mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
          className="text-center"
        >
          <h2 className="text-[40px] md:text-[56px] leading-[1.1] tracking-tight text-black mb-6 font-light">
            You know,<br />
            It's just money, after-all.
          </h2>

          <p className="text-[17px] leading-relaxed text-[#666] max-w-3xl mx-auto font-light">
            An equal source of stress, and joy. Exhilaration and anxiety, a centrepiece for most of our spinning around in lives. A belief ingrained from childhood, that money is complex, you're not enough to handle it. But a few good habits, some restraint, awareness, and tools that don't make you feel dumb have the power to change that.
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center mb-32">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
          >
           

            <h1 className="text-[48px] md:text-[64px] leading-[1.1] tracking-tight text-black mb-6 font-light">
              {headline}
            </h1>

            <p className="text-[17px] leading-relaxed text-[#666] mb-4 font-light whitespace-pre-line">
              {dailyVolumeLabel}
            </p>

            <p className="text-[17px] leading-relaxed text-[#666] mb-10 font-light">
              {subheadline}
            </p>

            <Link
              href={primaryButtonHref}
              className="inline-block text-white bg-[#156d95] rounded-xl px-8 py-4 text-[15px] font-medium transition-all duration-200 hover:bg-[#156d95]/90 cursor-pointer"
            >
              {primaryButtonText}
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.4 }}
            className="relative"
          >
            <div className="relative w-full aspect-video bg-linear-to-br from-gray-100 to-gray-200 rounded-[40px] overflow-hidden shadow-2xl">
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
                <div className="w-full h-full flex items-center justify-center text-[#999] text-sm">
                  Video Demo Placeholder
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
