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
    question: "What is Fold?",
    answer:
      "AI-powered expense tracking for India. Upload receipts, record voice notes in Hinglish, or type. We automatically extract amounts, categorize transactions, and give you real-time insights.",
  },
  {
    question: "Does it support Indian payment methods?",
    answer:
      "Yes. Built for India with support for UPI (GPay, PhonePe, Paytm), all major banks, and Hinglish input. Handles rupees with paisa precision.",
  },
  {
    question: "How accurate is it?",
    answer:
      "95%+ accuracy using AI trained on 42,500+ Indian transactions. You can correct any mistakes, and the system learns from your edits.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Encrypted and private. We never share your data with third parties. You control everything and can export or delete anytime.",
  },
  {
    question: "How do I get started?",
    answer:
      "Sign up, add your accounts, and start tracking via text, voice, or images. All core features are free.",
  },
]

export const FAQSection = ({ title = "Frequently asked questions", faqs = defaultFAQs }: FAQSectionProps) => {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index)
  }

  return (
    <section className="w-full py-32 px-6 md:px-12 bg-transparent relative">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 opacity-[0.03]">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255, 255, 255, 0.05) 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }} />
      </div>
      
      <div className="max-w-350 mx-auto relative z-10">
        <div className="grid lg:grid-cols-12 gap-16 lg:gap-24">
          <div className="lg:col-span-4">
            <div className="sticky top-24">
              <h2 className="text-[40px] md:text-[48px] leading-tight font-light text-white tracking-tight mb-6">
                {title}
              </h2>
              <div className="w-20 h-1 bg-linear-to-r from-gray-400 to-transparent rounded-full" />
            </div>
          </div>

          <div className="lg:col-span-8">
            <div className="space-y-0">
              {faqs.map((faq, index) => (
                <motion.div 
                  key={index} 
                  className="border-b border-white/10 last:border-b-0 relative group"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  {/* Hover background */}
                  <div className="absolute inset-0 bg-linear-to-r from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-lg" />
                  
                  <button
                    onClick={() => toggleFAQ(index)}
                    className="w-full flex items-center justify-between py-8 text-left group hover:opacity-70 transition-opacity duration-150 cursor-pointer relative z-10"
                    aria-expanded={openIndex === index}
                  >
                    <span className="text-[17px] leading-relaxed text-white pr-8 font-light">
                      {faq.question}
                    </span>
                    <motion.div
                      animate={{ rotate: openIndex === index ? 45 : 0 }}
                      transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                      className="shrink-0"
                    >
                      <Plus className="w-6 h-6 text-white" strokeWidth={1.5} />
                    </motion.div>
                  </button>

                  <AnimatePresence initial={false}>
                    {openIndex === index && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                        className="overflow-hidden relative z-10"
                      >
                        <div className="pb-8 pr-12">
                          <p className="text-[15px] leading-relaxed text-gray-400 font-light">
                            {faq.answer}
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
