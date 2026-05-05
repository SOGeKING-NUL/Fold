"use client"

import { motion } from "framer-motion"
import Link from "next/link"

export const CTASection = () => {
  return (
    <section className="w-full bg-white py-32">
      <div className="max-w-[1400px] mx-auto px-6 md:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="text-center"
        >
          <div className="max-w-3xl mx-auto mb-16">
            <h2 className="text-[48px] md:text-[64px] leading-[1.1] tracking-tight text-black mb-6 font-light">
              Ready to take control of your finances?
            </h2>
            <p className="text-[17px] leading-relaxed text-[#666] mb-12 font-light">
              Join thousands of users who have simplified their expense tracking with Fold. Start for free today.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                href="/chat"
                className="inline-block text-white bg-[#156d95] rounded-xl px-10 py-4 text-[15px] font-medium transition-all duration-200 hover:bg-[#156d95]/90 cursor-pointer"
              >
                Get Started Free
              </Link>
            </div>
          </div>

          <div className="mt-20 pt-20 border-t border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-left">
              <div>
                <div className="mb-4 text-[#156d95]">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <h3 className="text-[20px] font-normal text-black mb-2">Multi-Modal Input</h3>
                <p className="text-[15px] text-[#666] font-light">
                  Track expenses via text, voice, or images. Works with UPI screenshots and receipts.
                </p>
              </div>

              <div>
                <div className="mb-4 text-[#156d95]">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </div>
                <h3 className="text-[20px] font-normal text-black mb-2">Real-Time Processing</h3>
                <p className="text-[15px] text-[#666] font-light">
                  AI-powered categorization and instant insights. See your financial health at a glance.
                </p>
              </div>

              <div>
                <div className="mb-4 text-[#156d95]">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M7 11V7C7 4.79086 8.79086 3 11 3H13C15.2091 3 17 4.79086 17 7V11" stroke="currentColor" strokeWidth="1.5"/>
                  </svg>
                </div>
                <h3 className="text-[20px] font-normal text-black mb-2">Bank-Level Security</h3>
                <p className="text-[15px] text-[#666] font-light">
                  Your data is encrypted and secure. We never share your information with third parties.
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
