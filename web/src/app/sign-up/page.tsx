import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-black via-gray-900 to-black font-sans">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-block w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 mb-4" />
          <h1 className="text-3xl font-semibold text-white mb-2">Join Fold AI</h1>
          <p className="text-gray-400">Create your account to get started</p>
        </div>
        <SignUp
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-gray-800 shadow-xl",
            },
          }}
          routing="path"
          path="/sign-up"
          signInUrl="/login"
        />
      </div>
    </div>
  );
}
