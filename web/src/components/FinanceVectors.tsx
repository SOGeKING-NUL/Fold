"use client"

import { motion } from "framer-motion"

type VectorItem = {
  label: string
  icon: React.ReactNode
}

export function FinanceVectors() {
  const items: VectorItem[] = [
    {
      label: "Wallet",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 8.5a3 3 0 0 1 3-3h11a2 2 0 0 1 2 2v9a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-8Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M20 10.5h-4a2 2 0 0 0 0 4h4"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M16.5 12.5h.01" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      label: "Receipt",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M7 3h10v18l-2-1-3 1-3-1-2 1V3Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path d="M9 8h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M9 12h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M9 16h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      label: "Rupee",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M7 6h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M7 10h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path
            d="M7 6c3.5 0 9 0 9 4 0 3-3 4-6 4H7l9 8"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    },
    {
      label: "Categories",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M12 14a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-4Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M4 16a4 4 0 0 1 4-4h2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <path
            d="M20 8a4 4 0 0 0-4 4h-2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      ),
    },
    {
      label: "Trends",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 19V5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M4 19h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path
            d="M7 14l3-3 3 3 5-6"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M18 8h-3v3"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ),
    },
    {
      label: "Export",
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M7 10V7a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v3"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <path
            d="M12 12v8"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <path
            d="M8.5 16.5 12 20l3.5-3.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M6 12h12"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      ),
    },
  ]

  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-120px" }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="mt-16"
      aria-label="Personal finance vectors"
    >
      <div className="flex items-center justify-center gap-3 text-xs uppercase tracking-[0.22em] text-gray-500">
        <span className="h-px w-10 bg-white/10" />
        Personal finance vectors
        <span className="h-px w-10 bg-white/10" />
      </div>

      <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {items.map((item) => (
          <div
            key={item.label}
            className="group relative rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-4 shadow-lg"
          >
            <div className="absolute inset-0 rounded-2xl bg-linear-to-br from-white/6 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            <div className="relative flex flex-col items-center text-center">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-black/20 text-blue-400">
                {item.icon}
              </div>
              <div className="mt-3 text-[12px] tracking-wide text-gray-300">{item.label}</div>
            </div>
          </div>
        ))}
      </div>
    </motion.section>
  )
}
