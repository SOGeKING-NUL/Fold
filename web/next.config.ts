import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    // Force Turbopack to resolve relative to this project folder
    root: path.resolve("."),
  },
};

export default nextConfig;

