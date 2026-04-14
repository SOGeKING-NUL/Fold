"use client";

export default function LoginPage() {
  return (
    <div className="flex items-center justify-center min-h-screen px-4 bg-white">
      <div className="max-w-sm text-center space-y-5">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-gray-900 flex items-center justify-center shadow-lg">
          <span className="text-2xl font-bold text-white">F</span>
        </div>
        <h1 className="text-xl font-bold text-gray-900">Fold Reports</h1>
        <p className="text-sm text-gray-500 leading-relaxed">
          Open your Telegram bot and tap{" "}
          <span className="text-gray-900 font-semibold">
            Open Reports Dashboard
          </span>{" "}
          to get a secure link.
        </p>
        <p className="text-xs text-gray-400">
          Each link is valid for 5 minutes and works once.
        </p>
      </div>
    </div>
  );
}
