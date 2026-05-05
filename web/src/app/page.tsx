"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, UserButton } from "@clerk/nextjs";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";

export default function Page() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [resultData, setResultData] = useState<any>(null);
  const [message, setMessage] = useState<string | React.ReactNode | null>(null);

  const handleSendMessage = async (text: string, files?: File[]) => {
    if (!isSignedIn) {
      setMessage("Please sign in to continue");
      return;
    }

    setIsLoading(true);
    setMessage(null);
    setResultData(null);

    try {
      const token = await getToken();
      const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

      let response;

      // Determine which endpoint to call based on input type
      if (files && files.length > 0) {
        const formData = new FormData();
        formData.append("file", files[0]);
        
        const isAudio = files[0].type.startsWith("audio/") || files[0].name.endsWith(".webm");
        const endpoint = isAudio ? "/api/v1/web/extract/audio" : "/api/v1/web/extract/image";

        console.log("🚀 [Frontend] Uploading file to backend");
        console.log("  - File name:", files[0].name);
        console.log("  - File size:", files[0].size, "bytes");
        console.log("  - File type:", files[0].type);
        console.log("  - Endpoint:", endpoint);
        console.log("  - API Base:", API_BASE);
        console.log("  - Mode: SYNCHRONOUS (user waits for result)");

        response = await fetch(`${API_BASE}${endpoint}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
      } else {
        // Text input (synchronous)
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

      console.log("✅ [Frontend] Response received");
      console.log("  - Status:", result.status);
      console.log("  - Source:", result.source);
      console.log("  - Extracted data:", result.extracted_data);

      // Handle synchronous response
      setIsLoading(false);
      
      if (result.extracted_data) {
        setResultData(result);
      } else {
        setMessage(result.message || "Transaction saved successfully!");
      }

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

      console.log("Extraction result:", result);
    } catch (error) {
      console.error("Error:", error);
      setMessage(error instanceof Error ? error.message : "An error occurred");
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
              <UserButton />
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
          {message && !resultData && (
            <div className="text-center">
              <div className="inline-flex items-center gap-3 px-6 py-3 rounded-lg bg-gray-800/50 border border-gray-700/50 text-white">
                {isLoading && (
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                )}
                <div>{message}</div>
              </div>
            </div>
          )}

          {/* Detailed Result Card */}
          {resultData && resultData.extracted_data && (
            <div className="text-left bg-gray-800/80 border border-gray-700/50 p-5 rounded-2xl text-sm text-gray-300 w-full max-w-xl mx-auto space-y-4 shadow-xl">
              <div className="font-semibold text-white text-lg flex items-center justify-between">
                <span>
                  {resultData.extracted_data.payment_method || 'unknown'}
                  {resultData.extracted_data.payment_provider ? ` ; provider ${resultData.extracted_data.payment_provider}` : ''}
                  {` ; cash flow ${resultData.extracted_data.cash_flow || 'expense'}`}
                </span>
                <span className="text-blue-400 font-bold">
                  ₹{resultData.extracted_data.amount}
                </span>
              </div>
              
              {resultData.extracted_data.merchant && (
                <div>From {resultData.extracted_data.merchant}</div>
              )}
              
              <div className="bg-gray-900/50 p-3 rounded-xl border border-gray-700/50">
                Category: <span className="text-white font-medium capitalize">{resultData.extracted_data.category || 'unknown'}</span>.
                {resultData.ledger_result?.id ? ` Journal #${resultData.ledger_result.id}.` : ''}
                <br/>
                <span className="text-gray-400 text-xs mt-1 block">
                  Wrong category?{' '}
                  <button onClick={() => alert("Change category feature coming soon!")} className="text-blue-400 hover:text-blue-300 transition-colors">
                    Change category
                  </button>
                  , pick the right label, or use Back.
                </span>
              </div>
              
              <div className="text-gray-500 text-xs mt-4 border-t border-gray-700/50 pt-3 font-mono">
                <div className="text-gray-400 mb-1">Debug:</div>
                <ul className="space-y-1 pl-2 border-l-2 border-gray-700">
                  <li>- amount_source: {resultData.extracted_data.amount_source || 'llm'}</li>
                  <li>- upi_evidence: {resultData.extracted_data.payment_method === 'upi' ? 'True' : 'False'}</li>
                  <li>- payment_provider: {resultData.extracted_data.payment_provider || 'None'}</li>
                  <li>- bank_last4: {resultData.extracted_data.bank_account || 'None'}</li>
                  <li>- llm_called: True</li>
                  <li>- llm_success: True</li>
                  <li className="break-words">- raw_text: {resultData.extracted_data.raw_text || resultData.extracted_data.text_transcript || 'N/A'}</li>
                </ul>
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
