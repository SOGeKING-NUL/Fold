"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Menu, X } from "lucide-react"
import { useAuth, UserButton } from "@clerk/nextjs"
import { useRouter } from "next/navigation"

const navigationLinks = [
  {
    name: "Transactions",
    href: "/transactions",
  },
  {
    name: "Chat",
    href: "/chat",
  },
  {
    name: "Accounts",
    href: "/accounts",
  },
]

export const Navbar = () => {
  const router = useRouter()
  const { isSignedIn } = useAuth()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen)
  }

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false)
  }

  const handleLinkClick = (href: string) => {
    closeMobileMenu()
    if (href) {
      router.push(href)
    } else {
      router.push("/")
    }
  }

  return (
    <nav
      className={`w-full transition-all duration-300 ${
        isScrolled ? "bg-black/70 backdrop-blur-md border-b border-white/10" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          <div className="shrink-0">
            <button
              type="button"
              onClick={() => handleLinkClick("")}
              className="text-2xl text-white hover:text-gray-300 transition-colors duration-200 cursor-pointer font-medium"
              aria-label="Go to home"
            >
              Fold AI
            </button>
          </div>

          <div className="hidden md:block">
            {isSignedIn && (
              <div className="ml-10 flex items-baseline space-x-8">
                {navigationLinks.map((link) => (
                  <button
                    key={link.name}
                    type="button"
                    onClick={() => handleLinkClick(link.href)}
                    className="text-white hover:text-gray-300 font-semibold px-3 py-2 text-base transition-colors duration-200 relative group cursor-pointer"
                  >
                    {link.name}
                    <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-gray-300 transition-all duration-300 group-hover:w-full" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="hidden md:flex items-center gap-3">
            {isSignedIn ? (
              <>
                <button
                  type="button"
                  onClick={() => router.push("/reports")}
                  className="px-4 py-2 text-sm bg-[#0d9488] hover:bg-[#0f766e] text-white rounded-lg transition-colors cursor-pointer font-medium"
                >
                  View Report
                </button>
                <UserButton />
              </>
            ) : (
              <button
                type="button"
                onClick={() => router.push("/login")}
                className="px-4 py-2 text-sm bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-lg transition-colors cursor-pointer font-medium"
              >
                Sign In
              </button>
            )}
          </div>

          <div className="md:hidden">
            <button
              type="button"
              onClick={toggleMobileMenu}
              className="text-gray-200 hover:text-white p-2 rounded-md transition-colors duration-200 cursor-pointer"
              aria-label="Toggle mobile menu"
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-nav"
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="md:hidden bg-black/70 backdrop-blur-md border-t border-white/10"
            id="mobile-nav"
          >
            <div className="px-6 py-6 space-y-4">
              {isSignedIn && navigationLinks.map((link) => (
                <button
                  key={link.name}
                  type="button"
                  onClick={() => handleLinkClick(link.href)}
                  className="block w-full text-left text-white hover:text-gray-300 py-3 text-lg font-normal transition-colors duration-200 cursor-pointer"
                >
                  {link.name}
                </button>
              ))}
              <div className="pt-4 border-t border-white/5">
                {isSignedIn ? (
                  <button
                    type="button"
                    onClick={() => handleLinkClick("/reports")}
                    className="w-full bg-[#0d9488] text-white px-[18px] py-[15px] rounded-lg text-base font-semibold hover:bg-[#0f766e] transition-all duration-200 cursor-pointer"
                  >
                    View Report
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleLinkClick("/login")}
                    className="w-full bg-[#1e3a8a] text-white px-[18px] py-[15px] rounded-lg text-base font-semibold hover:bg-[#1e40af] transition-all duration-200 cursor-pointer"
                  >
                    Sign In
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
