import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

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
      <html lang="en" className="h-full antialiased">
        <body className="min-h-full flex flex-col bg-[var(--color-surface)] text-gray-900">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
