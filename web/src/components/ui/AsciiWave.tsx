"use client";

import { useEffect, useRef } from "react";

export function AsciiWave({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    let animationId: number;
    let time = 0;
    let lastFrameTime = 0;
    const targetFPS = 30; // Reduced from 60 to 30 FPS
    const frameInterval = 1000 / targetFPS;

    const chars = "█▓▒░ ";
    const width = 80; // Reduced from 120
    const height = 30; // Reduced from 40

    const animate = (currentTime: number) => {
      const elapsed = currentTime - lastFrameTime;

      if (elapsed > frameInterval) {
        lastFrameTime = currentTime - (elapsed % frameInterval);

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = "12px JetBrains Mono, monospace";

        for (let y = 0; y < height; y++) {
          for (let x = 0; x < width; x++) {
            const wave1 = Math.sin((x * 0.08) + time) * Math.cos((y * 0.12) + time * 0.5);
            const wave2 = Math.sin((x * 0.05) - time * 0.7) * Math.sin((y * 0.08) + time * 0.3);
            const wave3 = Math.cos((x * 0.03) + (y * 0.03) + time * 0.4);
            
            const combined = (wave1 + wave2 + wave3) / 3;
            const normalized = (combined + 1) / 2;
            
            const charIndex = Math.floor(normalized * (chars.length - 1));
            const char = chars[charIndex];
            
            if (char !== " ") {
              // Grayscale to match bg-gradient-to-br from-black via-gray-900 to-black
              const lightness = 0.15 + normalized * 0.25; // Range from dark gray to lighter gray
              const alpha = 0.2 + normalized * 0.5; // Subtle transparency
              ctx.fillStyle = `oklch(${lightness} 0 0 / ${alpha})`;
              ctx.fillText(char, x * 10, y * 14 + 14);
            }
          }
        }

        time += 0.02; // Slightly slower animation
      }

      animationId = requestAnimationFrame(animate);
    };

    canvas.width = width * 10;
    canvas.height = height * 14;
    animate(0);

    return () => cancelAnimationFrame(animationId);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`${className}`}
      style={{ imageRendering: "pixelated" }}
    />
  );
}
