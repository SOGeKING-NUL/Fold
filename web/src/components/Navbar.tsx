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
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? "bg-background/95 backdrop-blur-md shadow-sm" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          <div className="shrink-0">
            <button
              onClick={() => handleLinkClick("")}
              className="text-2xl text-foreground hover:text-primary transition-colors duration-200 cursor-pointer"
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
                    onClick={() => handleLinkClick(link.href)}
                    className="text-foreground hover:text-primary px-3 py-2 text-base font-normal transition-colors duration-200 relative group cursor-pointer"
                  >
                    {link.name}
                    <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-primary transition-all duration-300 group-hover:w-full" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="hidden md:flex items-center gap-3">
            {isSignedIn ? (
              <>
                <button
                  onClick={() => router.push("/dashboard")}
                  className="px-4 py-2 text-sm bg-[#156d95] hover:bg-[#156d95]/90 text-white rounded-lg transition-colors cursor-pointer"
                >
                  View Dashboard
                </button>
                <UserButton />
              </>
            ) : (
              <button
                onClick={() => router.push("/login")}
                className="px-4 py-2 text-sm bg-[#156d95] hover:bg-[#156d95]/90 text-white rounded-lg transition-colors cursor-pointer"
              >
                Sign In
              </button>
            )}
          </div>

          <div className="md:hidden">
            <button
              onClick={toggleMobileMenu}
              className="text-foreground hover:text-primary p-2 rounded-md transition-colors duration-200 cursor-pointer"
              aria-label="Toggle mobile menu"
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
            className="md:hidden bg-background/95 backdrop-blur-md border-t border-border"
          >
            <div className="px-6 py-6 space-y-4">
              {isSignedIn && navigationLinks.map((link) => (
                <button
                  key={link.name}
                  onClick={() => handleLinkClick(link.href)}
                  className="block w-full text-left text-foreground hover:text-primary py-3 text-lg font-normal transition-colors duration-200 cursor-pointer"
                >
                  {link.name}
                </button>
              ))}
              <div className="pt-4 border-t border-border">
                {isSignedIn ? (
                  <button
                    onClick={() => handleLinkClick("/dashboard")}
                    className="w-full bg-[#156d95] text-white px-[18px] py-[15px] rounded-lg text-base font-semibold hover:bg-[#156d95]/90 transition-all duration-200 cursor-pointer"
                  >
                    View Dashboard
                  </button>
                ) : (
                  <button
                    onClick={() => handleLinkClick("/login")}
                    className="w-full bg-[#156d95] text-white px-[18px] py-[15px] rounded-lg text-base font-semibold hover:bg-[#156d95]/90 transition-all duration-200 cursor-pointer"
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
