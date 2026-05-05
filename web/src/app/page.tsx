"use client";

import { HeroCard } from "@/components/HeroCard";
import { CTASection } from "@/components/CTASection";
import { FAQSection } from "@/components/FAQSection";
import { Footer } from "@/components/Footer";

export default function Page() {
  return (
    <div className="min-h-screen flex flex-col font-sans bg-white">
      <HeroCard />
      <CTASection />
      <FAQSection />
      <Footer />
    </div>
  );
}
