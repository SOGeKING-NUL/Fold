"use client";

import { HeroCard } from "@/components/HeroCard";
import { CTASection } from "@/components/CTASection";
import { FAQSection } from "@/components/FAQSection";
import { Footer } from "@/components/Footer";

export default function Page() {
  return (
    <div className="min-h-screen flex flex-col font-sans relative overflow-hidden">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-32 -left-24 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute top-1/3 -right-24 h-80 w-80 rounded-full bg-blue-400/10 blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="fixed inset-0 pointer-events-none opacity-[0.03]">
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(rgba(96, 165, 250, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(96, 165, 250, 0.1) 1px, transparent 1px)`,
          backgroundSize: '50px 50px'
        }} />
      </div>

      <div className="relative z-10 bg-linear-to-br from-black via-gray-900 to-black">
        <HeroCard />
        <CTASection />
        <FAQSection />
        <Footer />
      </div>
    </div>
  );
}
