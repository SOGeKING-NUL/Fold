"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";

export default function Page() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | React.ReactNode | null>(null);

  const handleSendMessage = async (text: string, files?: File[]) => {
    if (!isSignedIn) {
      setMessage("Please sign in to continue");
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

      let response;

      // Determine which endpoint to call based on input type
      if (files && files.length > 0) {
        // Image upload
        const formData = new FormData();
        formData.append("file", files[0]);

        response = await fetch(`${API_BASE}/api/v1/web/extract/image`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
      } else if (text.startsWith("[Voice message")) {
        // Voice recording (placeholder - actual audio file would be sent)
        setMessage("Voice recording feature coming soon!");
        setIsLoading(false);
        return;
      } else {
        // Text input
        response = await fetch(`${API_BASE}/api/v1/web/extract/text`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ text }),
        });
      }

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || "Failed to process request");
      }

      const result = await response.json();
      setMessage(result.message || "Transaction saved successfully!");

      // If user needs to add payment method, show special message
      if (result.ledger_result?.reason === "no_payment_method") {
        setMessage(
          <div className="flex flex-col items-center gap-3">
            <span>{result.message}</span>
            <button
              onClick={() => router.push("/accounts")}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Add Payment Method
            </button>
          </div>
        );
      }

      // Optionally refresh or show success
      console.log("Extraction result:", result);
    } catch (error) {
      console.error("Error:", error);
      setMessage(error instanceof Error ? error.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black flex flex-col font-sans">
      {/* Header */}
      <header className="w-full px-6 py-4 flex items-center justify-between border-b border-gray-800/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600" />
          <h1 className="text-xl font-semibold text-white">Fold AI</h1>
        </div>
        <div className="flex items-center gap-4">
          {isSignedIn ? (
            <>
              <button
                onClick={() => router.push("/dashboard")}
                className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors"
              >
                View Dashboard
              </button>
              <UserButton afterSignOutUrl="/" />
            </>
          ) : (
            <button
              onClick={() => router.push("/login")}
              className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-3xl space-y-8">
          {/* Hero Section */}
          <div className="text-center space-y-4 mb-12">
            <h2 className="text-4xl md:text-5xl font-semibold text-white">
              Your AI Financial Assistant
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              Upload receipts, record voice notes, or simply type to track your expenses.
              Let AI handle the rest.
            </p>
          </div>

          {/* Prompt Box */}
          <div className="w-full">
            <PromptInputBox
              onSend={handleSendMessage}
              isLoading={isLoading}
              placeholder="Upload a receipt, record audio, or type your expense..."
            />
          </div>

          {/* Feedback Message */}
          {message && (
            <div className="text-center">
              <div className="inline-block px-6 py-3 rounded-lg bg-gray-800/50 border border-gray-700/50 text-white">
                {message}
              </div>
            </div>
          )}

          {/* Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
            {/* Add Payment Method */}
            <button
              onClick={() => router.push("/accounts")}
              className="group p-6 rounded-2xl bg-gray-800/30 border border-gray-700/50 hover:border-blue-500/50 hover:bg-gray-800/50 transition-all duration-300 text-left"
            >
              <div className="flex flex-col gap-2">
                <h3 className="text-lg font-semibold text-white">Add Payment Method</h3>
                <p className="text-sm text-gray-400">Connect your bank, card, or wallet</p>
              </div>
            </button>

            {/* View Reports */}
            <button
              onClick={() => router.push("/dashboard")}
              className="group p-6 rounded-2xl bg-gray-800/30 border border-gray-700/50 hover:border-purple-500/50 hover:bg-gray-800/50 transition-all duration-300 text-left"
            >
              <div className="flex flex-col gap-2">
                <h3 className="text-lg font-semibold text-white">View Reports</h3>
                <p className="text-sm text-gray-400">See your spending insights</p>
              </div>
            </button>

            {/* View Transactions */}
            <button
              onClick={() => router.push("/transactions")}
              className="group p-6 rounded-2xl bg-gray-800/30 border border-gray-700/50 hover:border-green-500/50 hover:bg-gray-800/50 transition-all duration-300 text-left"
            >
              <div className="flex flex-col gap-2">
                <h3 className="text-lg font-semibold text-white">All Transactions</h3>
                <p className="text-sm text-gray-400">View your complete history</p>
              </div>
            </button>
          </div>

          {/* Feature Pills */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-6">
            <div className="px-4 py-2 rounded-full bg-gray-800/50 border border-gray-700/50 text-sm text-gray-300">
              Image Recognition
            </div>
            <div className="px-4 py-2 rounded-full bg-gray-800/50 border border-gray-700/50 text-sm text-gray-300">
              Voice Input
            </div>
            <div className="px-4 py-2 rounded-full bg-gray-800/50 border border-gray-700/50 text-sm text-gray-300">
              AI Categorization
            </div>
            <div className="px-4 py-2 rounded-full bg-gray-800/50 border border-gray-700/50 text-sm text-gray-300">
              Smart Analytics
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full px-6 py-4 text-center text-sm text-gray-500 border-t border-gray-800/50">
        Powered by AI • Secure & Private
      </footer>
    </div>
  );
}
