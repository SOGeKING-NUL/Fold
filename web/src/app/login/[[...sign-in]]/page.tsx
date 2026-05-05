"use client"

import { SignIn } from "@clerk/nextjs";
import { motion } from "framer-motion";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-white via-gray-50 to-white relative overflow-hidden">
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-white via-gray-50 to-white relative overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 bg-[#156d95]/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute -bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-purple-500/10 rounded-full blur-3xl"
        />
      </div>

      <div className="w-full max-w-6xl mx-auto px-6 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="hidden lg:block"
          >
            <div className="text-left">
              <h1 className="text-[56px] leading-[1.1] tracking-tight text-black mb-6 font-light">
                Welcome to<br />
                <span className="text-[#156d95]">Fold AI</span>
              </h1>
              <p className="text-[17px] leading-relaxed text-[#666] mb-8 font-light max-w-md">
                AI-powered expense tracking for modern India. Transform receipts, voice notes, and text into organized financial insights.
              </p>

              <div className="mt-12 space-y-4">
                {[
                  "Multi-modal input: Text, Voice & Images",
                  "AI-powered categorization",
                  "Real-time financial insights",
                  "Bank-level security"
                ].map((feature, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.8 + index * 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-5 h-5 rounded-full bg-[#156d95]/10 flex items-center justify-center">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="#156d95" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <span className="text-[15px] text-[#666]">{feature}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
            className="w-full"
          >
            <div className="lg:p-12">
              <div className="text-center mb-8 lg:hidden">
                <h2 className="text-[32px] leading-[1.1] tracking-tight text-black mb-3 font-light">
                  Welcome to <span className="text-[#156d95]">Fold AI</span>
                </h2>
                <p className="text-[15px] text-[#666]">Sign in to manage your finances</p>
              </div>

              <SignIn
                appearance={{
                  elements: {
                    rootBox: "w-full",
                    card: "bg-transparent shadow-none border-0 p-0",
                    headerTitle: "hidden",
                    headerSubtitle: "hidden",
                    socialButtonsBlockButton: "bg-white border-2 border-gray-200 hover:border-[#156d95] hover:bg-gray-50 transition-all duration-200 rounded-xl text-[15px] font-normal",
                    socialButtonsBlockButtonText: "text-gray-700 font-normal",
                    dividerLine: "bg-gray-200",
                    dividerText: "text-gray-500 text-[13px]",
                    formButtonPrimary: "bg-[#156d95] hover:bg-[#156d95]/90 rounded-xl text-[15px] font-medium py-3 transition-all duration-200",
                    formFieldInput: "rounded-xl border-2 border-gray-200 focus:border-[#156d95] focus:ring-0 text-[15px] py-3 transition-all duration-200",
                    formFieldLabel: "text-[14px] font-medium text-gray-700",
                    footerActionLink: "text-[#156d95] hover:text-[#156d95]/80 font-medium",
                    identityPreviewText: "text-[15px]",
                    identityPreviewEditButton: "text-[#156d95]",
                    formResendCodeLink: "text-[#156d95] hover:text-[#156d95]/80",
                    otpCodeFieldInput: "border-2 border-gray-200 focus:border-[#156d95] rounded-xl",
                  },
                  layout: {
                    socialButtonsPlacement: "top",
                    socialButtonsVariant: "blockButton",
                  },
                }}
                routing="path"
                path="/login"
                signUpUrl="/sign-up"
                forceRedirectUrl="/dashboard"
                fallbackRedirectUrl="/dashboard"
              />
            </div>

            <div className="mt-6 text-center lg:hidden">
              <p className="text-[13px] text-[#999]">
                By signing in, you agree to our Terms of Service and Privacy Policy
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
