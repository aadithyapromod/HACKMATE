import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HackMate v2 — Autonomous AI Website Generator",
  description: "Transform natural-language ideas into testable, compilable React + Vite prototypes in isolated Docker containers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0b0e14] text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
