"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { Navbar } from "@/components/Navbar";

export default function ChatPage() {
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
                            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors cursor-pointer"
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
            <div className="min-h-screen flex items-center justify-center bg-white">
                <div className="text-[#202020]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col font-sans bg-white">
            <Navbar />

            <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
                <div className="w-full max-w-3xl space-y-8">
                    <div className="w-full">
                        <PromptInputBox
                            onSend={handleSendMessage}
                            isLoading={isLoading}
                            placeholder="Upload a receipt, record audio, or type your expense..."
                        />
                    </div>

                    {message && !resultData && (
                        <div className="text-center">
                            <div className="inline-flex items-center gap-3 px-6 py-3 rounded-lg bg-[#f5f5f5] border border-[#e5e5e5] text-[#202020]">
                                {isLoading && (
                                    <div className="w-4 h-4 border-2 border-[#156d95] border-t-transparent rounded-full animate-spin" />
                                )}
                                <div>{message}</div>
                            </div>
                        </div>
                    )}

                    {resultData && resultData.extracted_data && (
                        <div className="text-left bg-[#fafafa] border border-[#e5e5e5] p-5 rounded-2xl text-sm text-[#404040] w-full max-w-xl mx-auto space-y-4 shadow-sm">
                            <div className="font-semibold text-[#202020] text-lg flex items-center justify-between">
                                <span>
                                    {resultData.extracted_data.payment_method || 'unknown'}
                                    {resultData.extracted_data.payment_provider ? ` ; provider ${resultData.extracted_data.payment_provider}` : ''}
                                    {` ; cash flow ${resultData.extracted_data.cash_flow || 'expense'}`}
                                </span>
                                <span className="text-[#156d95] font-bold">
                                    ₹{resultData.extracted_data.amount}
                                </span>
                            </div>

                            {resultData.extracted_data.merchant && (
                                <div>From {resultData.extracted_data.merchant}</div>
                            )}

                            <div className="bg-white p-3 rounded-xl border border-[#e5e5e5]">
                                Category: <span className="text-[#202020] font-medium capitalize">{resultData.extracted_data.category || 'unknown'}</span>.
                                {resultData.ledger_result?.id ? ` Journal #${resultData.ledger_result.id}.` : ''}
                                <br />
                                <span className="text-[#666666] text-xs mt-1 block">
                                    Wrong category?{' '}
                                    <button onClick={() => alert("Change category feature coming soon!")} className="text-[#156d95] hover:text-[#146e96] transition-colors cursor-pointer">
                                        Change category
                                    </button>
                                    , pick the right label, or use Back.
                                </span>
                            </div>

                            <div className="text-[#666666] text-xs mt-4 border-t border-[#e5e5e5] pt-3 font-mono">
                                <div className="text-[#404040] mb-1">Debug:</div>
                                <ul className="space-y-1 pl-2 border-l-2 border-[#e5e5e5]">
                                    <li>- amount_source: {resultData.extracted_data.amount_source || 'llm'}</li>
                                    <li>- upi_evidence: {resultData.extracted_data.payment_method === 'upi' ? 'True' : 'False'}</li>
                                    <li>- payment_provider: {resultData.extracted_data.payment_provider || 'None'}</li>
                                    <li>- bank_last4: {resultData.extracted_data.bank_account || 'None'}</li>
                                    <li>- llm_called: True</li>
                                    <li>- llm_success: True</li>
                                    <li className="wrap-break-word">- raw_text: {resultData.extracted_data.raw_text || resultData.extracted_data.text_transcript || 'N/A'}</li>
                                </ul>
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
                        <button
                            onClick={() => router.push("/accounts")}
                            className="group p-6 rounded-2xl bg-[#fafafa] border border-[#e5e5e5] hover:border-[#156d95] hover:bg-white transition-all duration-300 text-left cursor-pointer"
                        >
                            <div className="flex flex-col gap-2">
                                <h3 className="text-lg font-semibold text-[#202020]">Add Payment Method</h3>
                                <p className="text-sm text-[#666666]">Connect your bank, card, or wallet</p>
                            </div>
                        </button>

                        <button
                            onClick={() => router.push("/dashboard")}
                            className="group p-6 rounded-2xl bg-[#fafafa] border border-[#e5e5e5] hover:border-[#167E6C] hover:bg-white transition-all duration-300 text-left cursor-pointer"
                        >
                            <div className="flex flex-col gap-2">
                                <h3 className="text-lg font-semibold text-[#202020]">View Reports</h3>
                                <p className="text-sm text-[#666666]">See your spending insights</p>
                            </div>
                        </button>

                        <button
                            onClick={() => router.push("/transactions")}
                            className="group p-6 rounded-2xl bg-[#fafafa] border border-[#e5e5e5] hover:border-[#146e96] hover:bg-white transition-all duration-300 text-left cursor-pointer"
                        >
                            <div className="flex flex-col gap-2">
                                <h3 className="text-lg font-semibold text-[#202020]">All Transactions</h3>
                                <p className="text-sm text-[#666666]">View your complete history</p>
                            </div>
                        </button>
                    </div>

                    <div className="flex flex-wrap items-center justify-center gap-3 pt-6">
                        <div className="px-4 py-2 rounded-full bg-[#fafafa] border border-[#e5e5e5] text-sm text-[#666666]">
                            Image Recognition
                        </div>
                        <div className="px-4 py-2 rounded-full bg-[#fafafa] border border-[#e5e5e5] text-sm text-[#666666]">
                            Voice Input
                        </div>
                        <div className="px-4 py-2 rounded-full bg-[#fafafa] border border-[#e5e5e5] text-sm text-[#666666]">
                            AI Categorization
                        </div>
                        <div className="px-4 py-2 rounded-full bg-[#fafafa] border border-[#e5e5e5] text-sm text-[#666666]">
                            Smart Analytics
                        </div>
                    </div>
                </div>
            </main>

            <div className="text-center space-y-4 mb-12">

                <p className="text-lg text-[#666666] max-w-2xl mx-auto">
                    Upload receipts, record voice notes, or simply type to track your expenses.
                    Let AI handle the rest.
                </p>
            </div>

            <footer className="w-full px-6 py-4 text-center text-sm text-[#999999] border-t border-[#e5e5e5]">
                Powered by AI • Secure & Private
            </footer>
        </div>
    );
}
