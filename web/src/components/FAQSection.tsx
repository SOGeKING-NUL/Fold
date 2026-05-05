"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Plus } from "lucide-react"

type FAQItem = {
  question: string
  answer: string
}

type FAQSectionProps = {
  title?: string
  faqs?: FAQItem[]
}

const defaultFAQs: FAQItem[] = [
  {
    question: "What is Fold and how does it work?",
    answer:
      "Fold is an AI-powered expense tracking system designed for Indian users. It accepts multiple input types: upload receipt images (including UPI screenshots), record voice notes in Hinglish, or simply type your expenses. Our AI automatically extracts amounts, categorizes transactions, detects payment methods, and maintains double-entry accounting ledgers. All processing happens in real-time, giving you instant financial insights.",
  },
  {
    question: "Does Fold support Indian languages and payment methods?",
    answer:
      "Yes! Fold is built specifically for India. It natively supports Hinglish (Hindi-English code-mixed) voice and text input. Our OCR system recognizes UPI apps like GPay, PhonePe, Paytm, and others. We support all major Indian banks (HDFC, ICICI, SBI, Axis, etc.) and payment methods including UPI, cards, and cash. The system understands Indian currency formats and handles amounts in rupees with paisa precision.",
  },
  {
    question: "How accurate is the AI extraction and can I correct mistakes?",
    answer:
      "Our multi-modal AI achieves 95%+ accuracy on receipt OCR and uses a fine-tuned DistilBERT model trained on 42,500+ Indian transaction examples. For images, we use Roboflow for UPI detection, PaddleOCR for text extraction, and optional LLM structuring. You can always correct categories after posting—the system learns from your corrections and improves over time. All transactions are stored with double-entry accounting precision.",
  },
  {
    question: "Is my financial data secure and private?",
    answer:
      "Absolutely. All data is encrypted and stored securely in PostgreSQL. We use Clerk for authentication with industry-standard security practices. Your financial information never leaves our secure servers, and we never share data with third parties. You have complete control over your data and can export or delete it anytime. The system processes everything locally without sending sensitive information to external APIs.",
  },
  {
    question: "What features does Fold offer and how do I get started?",
    answer:
      "Fold offers multi-modal expense tracking (text, voice, image), automatic categorization across 10 categories, payment method detection, bank account linking, UPI profile management, weekly and monthly reports, category breakdowns, and a comprehensive dashboard with charts and insights. Getting started is simple: sign up, add your bank accounts or UPI profiles, and start tracking expenses via the web dashboard or Telegram bot. The free tier includes all core features.",
  },
]

export const FAQSection = ({ title = "Frequently asked questions", faqs = defaultFAQs }: FAQSectionProps) => {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index)
  }

  return (
    <section className="w-full py-32 px-6 md:px-12 bg-white">
      <div className="max-w-[1400px] mx-auto">
        <div className="grid lg:grid-cols-12 gap-16 lg:gap-24">
          <div className="lg:col-span-4">
            <h2 className="text-[40px] md:text-[48px] leading-tight font-light text-black tracking-tight sticky top-24">
              {title}
            </h2>
          </div>

          <div className="lg:col-span-8">
            <div className="space-y-0">
              {faqs.map((faq, index) => (
                <div key={index} className="border-b border-gray-200 last:border-b-0">
                  <button
                    onClick={() => toggleFAQ(index)}
                    className="w-full flex items-center justify-between py-8 text-left group hover:opacity-70 transition-opacity duration-150 cursor-pointer"
                    aria-expanded={openIndex === index}
                  >
                    <span className="text-[17px] leading-relaxed text-black pr-8 font-light">
                      {faq.question}
                    </span>
                    <motion.div
                      animate={{ rotate: openIndex === index ? 45 : 0 }}
                      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                      className="shrink-0"
                    >
                      <Plus className="w-6 h-6 text-black" strokeWidth={1.5} />
                    </motion.div>
                  </button>

                  <AnimatePresence initial={false}>
                    {openIndex === index && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="pb-8 pr-12">
                          <p className="text-[15px] leading-relaxed text-[#666] font-light">
                            {faq.answer}
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
