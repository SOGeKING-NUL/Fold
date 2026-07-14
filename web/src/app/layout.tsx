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
          <div className="fixed top-0 left-0 right-0 z-50 flex flex-col">
            <div className="w-full bg-yellow-400 text-black text-center py-2 px-4 text-xs sm:text-sm font-semibold select-none">
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
          </div>
          <div className="flex-1 flex flex-col pt-9">
            {children}
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
}
