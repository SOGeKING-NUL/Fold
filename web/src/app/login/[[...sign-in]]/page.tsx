"use client"

import { SignIn } from "@clerk/nextjs";
import { motion } from "framer-motion";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-black via-gray-900 to-black relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.15, 0.25, 0.15],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 bg-blue-500/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.1, 0.2, 0.1],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute -bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-purple-500/20 rounded-full blur-3xl"
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
              <h1 className="text-[56px] leading-[1.1] tracking-tight text-white mb-6 font-light">
                Welcome to<br />
                <span className="text-blue-400">Fold AI</span>
              </h1>
              <p className="text-[17px] leading-relaxed text-gray-400 mb-8 font-light max-w-md">
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
                    <div className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center border border-blue-500/30">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <span className="text-[15px] text-gray-300">{feature}</span>
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
                <h2 className="text-[32px] leading-[1.1] tracking-tight text-white mb-3 font-light">
                  Welcome to <span className="text-blue-400">Fold AI</span>
                </h2>
                <p className="text-[15px] text-gray-400">Sign in to manage your finances</p>
              </div>

              <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 shadow-lg">
                <SignIn
                  appearance={{
                    elements: {
                      rootBox: "w-full",
                      card: "bg-transparent shadow-none border-0 p-0",
                      headerTitle: "hidden",
                      headerSubtitle: "hidden",
                      socialButtonsBlockButton: "bg-white/10 border border-white/20 hover:bg-white/20 hover:border-white/30 transition-all duration-200 rounded-xl text-[15px] font-normal text-white",
                      socialButtonsBlockButtonText: "text-white font-normal",
                      socialButtonsIconButton: "border-white/20 hover:bg-white/20",
                      dividerLine: "bg-white/20",
                      dividerText: "text-gray-400 text-[13px]",
                      formButtonPrimary: "bg-[#1e3a8a] hover:bg-[#1e40af] rounded-xl text-[15px] font-medium py-3 transition-all duration-200 text-white",
                      formFieldInput: "rounded-xl border border-white/20 bg-white/5 focus:border-blue-500 focus:ring-0 text-[15px] py-3 transition-all duration-200 text-white placeholder:text-gray-500",
                      formFieldLabel: "text-[14px] font-medium text-gray-300",
                      footerActionLink: "text-blue-400 hover:text-blue-300 font-medium",
                      identityPreviewText: "text-[15px] text-white",
                      identityPreviewEditButton: "text-blue-400",
                      formResendCodeLink: "text-blue-400 hover:text-blue-300",
                      otpCodeFieldInput: "border border-white/20 bg-white/5 focus:border-blue-500 rounded-xl text-white",
                      formFieldInputShowPasswordButton: "text-gray-400 hover:text-gray-300",
                      formFieldAction: "text-blue-400 hover:text-blue-300",
                      footerActionText: "text-gray-400",
                      identityPreviewEditButtonIcon: "text-blue-400",
                      formHeaderTitle: "text-white",
                      formHeaderSubtitle: "text-gray-400",
                      alertText: "text-gray-300",
                      formFieldErrorText: "text-red-400",
                    },
                    layout: {
                      socialButtonsPlacement: "top",
                      socialButtonsVariant: "blockButton",
                    },
                  }}
                  routing="path"
                  path="/login"
                  signUpUrl="/sign-up"
                  forceRedirectUrl="/reports"
                  fallbackRedirectUrl="/reports"
                />
              </div>
            </div>

            <div className="mt-6 text-center lg:hidden">
              <p className="text-[13px] text-gray-500">
                By signing in, you agree to our Terms of Service and Privacy Policy
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
