import { Suspense } from "react";
import DashboardClient from "@/components/DashboardClient";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin" />
            <span className="text-gray-400 text-sm">Loading...</span>
          </div>
        </div>
      }
    >
      <DashboardClient />
    </Suspense>
  );
}
