"use client";

import { useEffect, useState } from "react";

interface SeamlessLoaderProps {
  steps: string[];
  interval?: number;
}

export function SeamlessLoader({ steps, interval = 3200 }: SeamlessLoaderProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (steps.length === 0) return;

    const cycleStep = () => {
      setIsVisible(false);
      
      setTimeout(() => {
        setCurrentIndex((prev) => (prev + 1) % steps.length);
        setIsVisible(true);
      }, 400);
    };

    const timer = setInterval(cycleStep, interval);
    return () => clearInterval(timer);
  }, [steps.length, interval]);

  return (
    <div className="w-full animate-slideDown">
      <div className="relative overflow-hidden rounded-3xl bg-[#0a0e13] border border-white/[0.06] shadow-2xl">
        {/* Subtle top accent */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-blue-500/20 to-transparent" />
        
        <div className="relative px-8 py-8">
          <div className="flex items-center gap-8">
            {/* Large coin animation area */}
            <div className="relative flex-shrink-0 w-32 h-32 flex items-center justify-center">
              <svg
                className="w-full h-full"
                viewBox="0 0 120 120"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Coin 1 - Bottom layer */}
                <g className="animate-coinFloat1">
                  <ellipse
                    cx="60"
                    cy="80"
                    rx="28"
                    ry="8"
                    fill="url(#coinGradient1)"
                    opacity="0.4"
                  />
                  <ellipse
                    cx="60"
                    cy="78"
                    rx="28"
                    ry="8"
                    fill="url(#coinGradient2)"
                    opacity="0.6"
                  />
                  <ellipse
                    cx="60"
                    cy="76"
                    rx="26"
                    ry="7"
                    fill="#1e40af"
                    opacity="0.3"
                  />
                </g>
                
                {/* Coin 2 - Middle layer */}
                <g className="animate-coinFloat2">
                  <ellipse
                    cx="60"
                    cy="60"
                    rx="28"
                    ry="8"
                    fill="url(#coinGradient1)"
                    opacity="0.5"
                  />
                  <ellipse
                    cx="60"
                    cy="58"
                    rx="28"
                    ry="8"
                    fill="url(#coinGradient2)"
                    opacity="0.7"
                  />
                  <ellipse
                    cx="60"
                    cy="56"
                    rx="26"
                    ry="7"
                    fill="#2563eb"
                    opacity="0.4"
                  />
                </g>
                
                {/* Coin 3 - Top layer */}
                <g className="animate-coinFloat3">
                  <ellipse
                    cx="60"
                    cy="40"
                    rx="28"
                    ry="8"
                    fill="url(#coinGradient1)"
                    opacity="0.6"
                  />
                  <ellipse
                    cx="60"
                    cy="38"
                    rx="28"
                    ry="8"
                    fill="url(#coinGradient2)"
                    opacity="0.85"
                  />
                  <ellipse
                    cx="60"
                    cy="36"
                    rx="26"
                    ry="7"
                    fill="#3b82f6"
                    opacity="0.5"
                  />
                  
                  {/* Rupee symbol on top coin */}
                  <text
                    x="60"
                    y="42"
                    textAnchor="middle"
                    fill="white"
                    fontSize="20"
                    fontWeight="700"
                    opacity="0.9"
                    className="animate-symbolPulse"
                  >
                    ₹
                  </text>
                </g>

                {/* Sparkle effects */}
                <circle
                  cx="35"
                  cy="30"
                  r="2"
                  fill="white"
                  opacity="0.6"
                  className="animate-sparkle1"
                />
                <circle
                  cx="85"
                  cy="45"
                  r="1.5"
                  fill="white"
                  opacity="0.5"
                  className="animate-sparkle2"
                />
                <circle
                  cx="40"
                  cy="70"
                  r="1.5"
                  fill="white"
                  opacity="0.4"
                  className="animate-sparkle3"
                />

                {/* Gradient definitions */}
                <defs>
                  <linearGradient id="coinGradient1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#1e40af" stopOpacity="0.6" />
                  </linearGradient>
                  <linearGradient id="coinGradient2" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.7" />
                    <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.9" />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity="0.7" />
                  </linearGradient>
                </defs>
              </svg>

              {/* Ambient glow */}
              <div className="absolute inset-0 bg-blue-500/10 rounded-full blur-2xl animate-glowPulse" />
            </div>
            
            {/* Text content - larger and more prominent */}
            <div className="flex-1 min-w-0">
              <div
                className={`text-xl font-semibold text-white/95 mb-3 transition-all duration-400 ${
                  isVisible 
                    ? "opacity-100 translate-x-0" 
                    : "opacity-0 translate-x-6"
                }`}
              >
                {steps[currentIndex]}
              </div>
              
              {/* Progress section */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-500 font-mono min-w-[40px]">
                    {currentIndex + 1}/{steps.length}
                  </span>
                  <div className="flex-1 h-1 bg-white/[0.05] rounded-full overflow-hidden max-w-[200px]">
                    <div
                      className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-400 ease-out"
                      style={{ width: `${((currentIndex + 1) / steps.length) * 100}%` }}
                    />
                  </div>
                </div>
                
                <div className="text-xs text-gray-600">
                  Processing your transaction securely
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom accent */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-2/3 h-[1px] bg-gradient-to-r from-transparent via-blue-500/15 to-transparent" />
      </div>

      <style jsx>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-15px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes coinFloat1 {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-6px);
          }
        }

        @keyframes coinFloat2 {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-8px);
          }
        }

        @keyframes coinFloat3 {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-10px);
          }
        }

        @keyframes symbolPulse {
          0%, 100% {
            opacity: 0.9;
            transform: scale(1);
          }
          50% {
            opacity: 1;
            transform: scale(1.05);
          }
        }

        @keyframes sparkle1 {
          0%, 100% {
            opacity: 0;
            transform: scale(0);
          }
          50% {
            opacity: 0.8;
            transform: scale(1.2);
          }
        }

        @keyframes sparkle2 {
          0%, 100% {
            opacity: 0;
            transform: scale(0);
          }
          50% {
            opacity: 0.6;
            transform: scale(1.3);
          }
        }

        @keyframes sparkle3 {
          0%, 100% {
            opacity: 0;
            transform: scale(0);
          }
          50% {
            opacity: 0.5;
            transform: scale(1.1);
          }
        }

        @keyframes glowPulse {
          0%, 100% {
            opacity: 0.3;
            transform: scale(0.9);
          }
          50% {
            opacity: 0.6;
            transform: scale(1.1);
          }
        }

        .animate-slideDown {
          animation: slideDown 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .animate-coinFloat1 {
          animation: coinFloat1 2.5s ease-in-out infinite;
        }

        .animate-coinFloat2 {
          animation: coinFloat2 2.5s ease-in-out infinite 0.3s;
        }

        .animate-coinFloat3 {
          animation: coinFloat3 2.5s ease-in-out infinite 0.6s;
        }

        .animate-symbolPulse {
          animation: symbolPulse 2s ease-in-out infinite;
        }

        .animate-sparkle1 {
          animation: sparkle1 3s ease-in-out infinite;
        }

        .animate-sparkle2 {
          animation: sparkle2 3s ease-in-out infinite 0.5s;
        }

        .animate-sparkle3 {
          animation: sparkle3 3s ease-in-out infinite 1s;
        }

        .animate-glowPulse {
          animation: glowPulse 3s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
