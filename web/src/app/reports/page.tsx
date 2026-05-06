import { Suspense } from "react";
import DashboardClient from "@/components/DashboardClient";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen bg-linear-to-br from-black via-gray-900 to-black">
          <div className="flex flex-col items-center gap-4">
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 rounded-full border-2 border-gray-800"></div>
              <div className="absolute inset-0 rounded-full border-2 border-white border-t-transparent animate-spin"></div>
            </div>
            <span className="text-gray-400 text-sm">Loading...</span>
          </div>
        </div>
      }
    >
      <DashboardClient />
    </Suspense>
  );
}
