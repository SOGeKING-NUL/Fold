"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { OrbitalLoader } from "@/components/ui/OrbitalLoader";
import { SeamlessLoader } from "@/components/ui/SeamlessLoader";

export default function ChatPage() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  type ProcessingMode = "text" | "image" | "audio";
  const [processingMode, setProcessingMode] = useState<ProcessingMode>("text");
  type ExtractionResult = {
    message?: string;
    extracted_data?: {
      amount?: number;
      amount_source?: string;
      merchant?: string;
      category?: string;
      payment_method?: string;
      payment_provider?: string;
      cash_flow?: string;
      bank_account?: string;
    };
    ledger_result?: {
      id?: number;
      reason?: string;
    };
  };

  const [resultData, setResultData] = useState<ExtractionResult | null>(null);
  const [message, setMessage] = useState<string | React.ReactNode | null>(null);

  const steps = useMemo(() => {
    const map: Record<ProcessingMode, string[]> = {
      text: [
        "Reading your note...",
        "Extracting merchant and amount...",
        "Categorizing transaction...",
        "Saving to ledger...",
      ],
      image: [
        "Uploading receipt...",
        "Reading text from image...",
        "Extracting merchant and amount...",
        "Categorizing transaction...",
        "Saving to ledger...",
      ],
      audio: [
        "Uploading audio...",
        "Transcribing speech...",
        "Extracting merchant and amount...",
        "Categorizing transaction...",
        "Saving to ledger...",
      ],
    };
    return map[processingMode];
  }, [processingMode]);

  const handleSendMessage = async (text: string, files?: File[]) => {
    if (!isSignedIn) {
      setMessage("Please sign in to continue");
      return;
    }

    if (files && files.length > 0) {
      const file = files[0];
      const isAudio =
        file.type.startsWith("audio/") || file.name.endsWith(".webm");
      setProcessingMode(isAudio ? "audio" : "image");
    } else {
      setProcessingMode("text");
    }

    setIsLoading(true);
    setMessage(null);
    setResultData(null);

    try {
      const token = await getToken();
      const API_BASE =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

      let response;

      if (files && files.length > 0) {
        const formData = new FormData();
        formData.append("file", files[0]);

        const isAudio =
          files[0].type.startsWith("audio/") || files[0].name.endsWith(".webm");
        const endpoint = isAudio
          ? "/api/v1/web/extract/audio"
          : "/api/v1/web/extract/image";

        response = await fetch(`${API_BASE}${endpoint}`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });
      } else {
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
      setIsLoading(false);

      if (result.extracted_data) {
        setResultData(result);
      } else {
        setMessage(result.message || "Transaction saved successfully!");
      }

      if (result.ledger_result?.reason === "no_payment_method") {
        setMessage(
          <div className="flex flex-col items-center gap-3">
            <span>{result.message}</span>
            <button
              onClick={() => router.push("/accounts")}
              className="px-4 py-2 bg-[#1e3a8a] hover:bg-[#1e40af] text-white rounded-lg text-sm font-medium transition-colors cursor-pointer"
            >
              Add Payment Method
            </button>
          </div>,
        );
      }
    } catch (error) {
      console.error("Error:", error);
      setMessage(error instanceof Error ? error.message : "An error occurred");
      setIsLoading(false);
    }
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-black via-gray-900 to-black">
        <OrbitalLoader message="Loading..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col font-sans bg-linear-to-br from-black via-gray-900 to-black">
      <main className="flex-1 px-4 py-16 mt-16">
        <div className="w-full max-w-2xl mx-auto space-y-8">
          <div className="text-center mb-12">
            <h1 className="text-[32px] md:text-[40px] leading-tight text-white mb-3 font-normal">
              Your AI Financial Assistant
            </h1>
            <p className="text-[15px] text-gray-400">
              Upload receipts, record voice notes, or simply type to track your
              expenses. Let AI handle the rest.
            </p>
          </div>

          <div className="w-full">
            <PromptInputBox
              onSend={handleSendMessage}
              isLoading={isLoading}
              placeholder="Upload a receipt, record audio, or type your expense..."
            />
          </div>

          {isLoading && !message && !resultData && (
            <div className="w-full mt-4">
              <SeamlessLoader steps={steps} interval={3200} />
            </div>
          )}

          {message && !resultData && (
            <div className="text-center animate-fadeIn">
              <div className="inline-flex items-center gap-3 px-5 py-3 rounded-2xl bg-white/5 border border-white/10 text-white backdrop-blur-sm shadow-lg">
                <div>{message}</div>
              </div>
            </div>
          )}

          {resultData && resultData.extracted_data && (
            <div className="w-full animate-slideUp">
              <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-sm shadow-lg">
                <div className="bg-linear-to-r from-[#0d9488] to-[#0f766e] p-5 text-white">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="text-sm mb-2">Transaction Recorded</div>
                      <div className="text-xs opacity-90">
                        <span className="capitalize">
                          {resultData.extracted_data.payment_method ||
                            "unknown"}
                        </span>
                        {resultData.extracted_data.payment_provider && (
                          <span>
                            {" "}
                            • {resultData.extracted_data.payment_provider}
                          </span>
                        )}
                        <span className="block mt-1 capitalize opacity-75">
                          {resultData.extracted_data.cash_flow || "expense"}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-semibold">
                        ₹{resultData.extracted_data.amount}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-5 space-y-4">
                  {resultData.extracted_data.merchant && (
                    <div className="flex items-center gap-3 p-3 bg-white/5 rounded-2xl border border-white/10">
                      <div className="text-xs text-gray-400 uppercase tracking-wide min-w-15">
                        Merchant
                      </div>
                      <div className="text-sm font-medium text-white">
                        {resultData.extracted_data.merchant}
                      </div>
                    </div>
                  )}

                  <div className="border border-white/10 rounded-2xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">
                          Category
                        </div>
                        <div className="text-base font-medium text-white capitalize">
                          {resultData.extracted_data.category || "unknown"}
                        </div>
                      </div>
                      {resultData.ledger_result?.id && (
                        <div className="text-right">
                          <div className="text-xs text-gray-400">
                            Journal ID
                          </div>
                          <div className="text-sm font-mono text-gray-300">
                            #{resultData.ledger_result.id}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="text-xs text-gray-400 pt-3 border-t border-white/10">
                      Wrong category?{" "}
                      <button
                        onClick={() =>
                          alert("Change category feature coming soon!")
                        }
                        className="text-gray-300 hover:text-white hover:underline cursor-pointer"
                      >
                        Change it
                      </button>
                    </div>
                  </div>

                  <details className="group">
                    <summary className="flex items-center justify-between cursor-pointer p-3 rounded-2xl hover:bg-white/5 transition-colors">
                      <span className="text-sm text-gray-400">
                        Technical Details
                      </span>
                      <svg
                        className="w-4 h-4 text-gray-400 transition-transform group-open:rotate-180"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </summary>
                    <div className="mt-2 p-4 bg-white/5 rounded-2xl border border-white/10">
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <div className="text-gray-400 mb-1">
                            Amount Source
                          </div>
                          <div className="text-white font-mono">
                            {resultData.extracted_data.amount_source || "llm"}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-400 mb-1">UPI Evidence</div>
                          <div className="text-white font-mono">
                            {resultData.extracted_data.payment_method === "upi"
                              ? "Yes"
                              : "No"}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-400 mb-1">Provider</div>
                          <div className="text-white font-mono">
                            {resultData.extracted_data.payment_provider ||
                              "None"}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-400 mb-1">Bank Account</div>
                          <div className="text-white font-mono">
                            {resultData.extracted_data.bank_account || "None"}
                          </div>
                        </div>
                      </div>
                    </div>
                  </details>
                </div>

                <div className="bg-white/5 px-5 py-3 border-t border-white/10">
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>Saved successfully</span>
                    <button
                      onClick={() => router.push("/transactions")}
                      className="text-gray-300 hover:text-white hover:underline cursor-pointer"
                    >
                      View all transactions →
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
            <button
              onClick={() => router.push("/accounts")}
              className="group p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 hover:bg-white/[0.07] transition-all duration-300 text-left cursor-pointer backdrop-blur-sm shadow-lg"
            >
              <div className="flex flex-col gap-2">
                <h3 className="text-lg font-semibold text-white">
                  Add Payment Method
                </h3>
                <p className="text-sm text-gray-400">
                  Connect your bank, card, or wallet
                </p>
              </div>
            </button>

            <button
              onClick={() => router.push("/reports")}
              className="group p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 hover:bg-white/[0.07] transition-all duration-300 text-left cursor-pointer backdrop-blur-sm shadow-lg"
            >
              <div className="flex flex-col gap-2">
                <h3 className="text-lg font-semibold text-white">
                  View Reports
                </h3>
                <p className="text-sm text-gray-400">
                  See your spending insights
                </p>
              </div>
            </button>

            <button
              onClick={() => router.push("/transactions")}
              className="group p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 hover:bg-white/[0.07] transition-all duration-300 text-left cursor-pointer backdrop-blur-sm shadow-lg"
            >
              <div className="flex flex-col gap-2">
                <h3 className="text-lg font-semibold text-white">
                  All Transactions
                </h3>
                <p className="text-sm text-gray-400">
                  View your complete history
                </p>
              </div>
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-12 pb-4">
            <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300">
              Image Recognition
            </div>
            <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300">
              Voice Input
            </div>
            <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300">
              AI Categorization
            </div>
            <div className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs text-gray-300">
              Smart Analytics
            </div>
          </div>
        </div>
      </main>

      <footer className="w-full px-6 py-6 text-center text-sm text-gray-400 border-t border-white/10">
        Powered by AI • Secure & Private
      </footer>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
        .animate-slideUp {
          animation: slideUp 0.4s ease-out;
        }
      `}</style>
    </div>
  );
}
