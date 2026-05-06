"use client";

import * as React from "react";

type MarqueeProps = {
  children: React.ReactNode;
  /** seconds for a full loop */
  durationSeconds?: number;
  pauseOnHover?: boolean;
  className?: string;
  innerClassName?: string;
};

export function Marquee({
  children,
  durationSeconds = 22,
  pauseOnHover = true,
  className = "",
  innerClassName = "",
}: MarqueeProps) {
  return (
    <div
      className={
        "relative overflow-hidden mask-[linear-gradient(to_right,transparent,black_12%,black_88%,transparent)] " +
        className
      }
    >
      <div
        className={
          "flex w-max gap-3 marquee-track " +
          (pauseOnHover ? "marquee-pause" : "") +
          " " +
          innerClassName
        }
        style={{ "--marquee-duration": `${durationSeconds}s` } as React.CSSProperties}
        aria-hidden
      >
        {children}
        {children}
      </div>

      <style jsx>{`
        @keyframes marquee {
          from {
            transform: translateX(0);
          }
          to {
            transform: translateX(-50%);
          }
        }

        .marquee-track {
          animation: marquee var(--marquee-duration) linear infinite;
          will-change: transform;
        }

        .marquee-pause:hover {
          animation-play-state: paused;
        }

        @media (prefers-reduced-motion: reduce) {
          .marquee-track {
            animation: none;
            transform: none;
          }
        }
      `}</style>
    </div>
  );
}
