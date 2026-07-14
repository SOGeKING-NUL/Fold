import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";

const sans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Fold AI - Financial Assistant",
  description: "AI-powered financial tracking and expense management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className={`${sans.variable} ${mono.variable} h-full antialiased`}>
        <body className="min-h-full flex flex-col font-sans">
          <div className="w-full bg-yellow-400 text-black text-center py-2 px-4 text-xs sm:text-sm font-semibold select-none z-[9999]">
            backend hosted on huggingface is down, please check sourcecode at{" "}
            <a 
              href="https://github.com/SOGeKING-NUL/Fold" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="underline hover:text-neutral-800"
            >
              github.com/SOGeKING-NUL/Fold
            </a>
          </div>
          <Navbar />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
