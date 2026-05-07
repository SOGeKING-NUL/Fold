"use client"
import { motion } from "framer-motion"
import Link from "next/link"

type FooterLink = {
  label: string
  href: string
}

type FooterSection = {
  title: string
  links: FooterLink[]
}

type FooterProps = {
  companyName?: string
  tagline?: string
  sections?: FooterSection[]
  copyrightText?: string
}

const defaultSections: FooterSection[] = [
  {
    title: "Product",
    links: [
      { label: "Dashboard", href: "/reports" },
      { label: "Chat", href: "/chat" },
      { label: "Transactions", href: "/transactions" },
      { label: "Accounts", href: "/accounts" },
    ],
  },
  {
    title: "Features",
    links: [
      { label: "Image Recognition", href: "/chat" },
      { label: "Voice Input", href: "/chat" },
      { label: "AI Categorization", href: "/reports" },
      { label: "Smart Analytics", href: "/reports" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "#docs" },
      { label: "Help Center", href: "#help" },
      { label: "API Reference", href: "#api" },
      { label: "Telegram Bot", href: "#telegram" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "#privacy" },
      { label: "Terms of Service", href: "#terms" },
      { label: "Security", href: "#security" },
      { label: "Data Protection", href: "#data" },
    ],
  },
]

export const Footer = ({
  companyName = "Fold AI",
  tagline = "AI-Powered Expense Tracking for Modern India", 
  sections = defaultSections,
  copyrightText,
}: FooterProps) => {
  const currentYear = new Date().getFullYear()
  const copyright = copyrightText || `© ${currentYear} ${companyName}. All rights reserved.`

  return (
    <footer className="w-full border-t border-white/10">
      <div className="max-w-350 mx-auto px-6 md:px-12 py-16 md:py-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-x-12 gap-y-10 mb-14 md:mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="sm:col-span-2 lg:col-span-2"
          >
            <div className="mb-6">
              <h3 className="text-[24px] font-light text-white mb-3">
                {companyName}
              </h3>
              <p className="text-[15px] leading-relaxed text-gray-400 max-w-xs font-light">
                {tagline}
              </p>
            </div>
          </motion.div>

          {sections.map((section, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
              className="min-w-0"
            >
              <h4 className="text-[13px] font-medium text-white mb-4 uppercase tracking-wider">
                {section.title}
              </h4>
              <ul className="space-y-3">
                {section.links.map((link, linkIndex) => (
                  <li key={linkIndex}>
                    {link.href.startsWith("#") ? (
                      <a
                        href={link.href}
                        className="text-[15px] text-gray-400 hover:text-white transition-colors duration-150 font-light cursor-pointer"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="text-[15px] text-gray-400 hover:text-white transition-colors duration-150 font-light cursor-pointer"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="pt-8 border-t border-white/10"
        >
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <p className="text-[14px] text-gray-500 font-light text-left">{copyright}</p>
          </div>
        </motion.div>
      </div>
    </footer>
  )
}
