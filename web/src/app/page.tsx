"use client";

import { HeroCard } from "@/components/HeroCard";
import { LandingDefinitionSections } from "@/components/LandingDefinationSections";
import { CTASection } from "@/components/CTASection";
import { FAQSection } from "@/components/FAQSection";
import { Footer } from "@/components/Footer";
import { AsciiWave } from "@/components/ui/AsciiWave";

export default function Page() {
  return (
    <div className="min-h-screen flex flex-col font-sans relative overflow-hidden bg-linear-to-br from-black via-gray-900 to-black">
      {/* AsciiWave background across entire page - reduced opacity for better performance */}
      <div className="fixed inset-0 opacity-20 pointer-events-none overflow-hidden z-0">
        <AsciiWave className="w-full h-full" />
      </div>

      <div className="fixed inset-0 pointer-events-none opacity-[0.03] z-0">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `linear-gradient(rgba(96, 165, 250, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(96, 165, 250, 0.1) 1px, transparent 1px)`,
            backgroundSize: "50px 50px",
          }}
        />
      </div>

      <div className="relative z-10">
        <HeroCard />
        <LandingDefinitionSections />
        <CTASection />
        <FAQSection />
        <Footer />
      </div>
    </div>
  );
}
