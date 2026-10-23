import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HackMate — Agentic AI Hackathon Companion",
  description:
    "Autonomous agentic AI system turning hackathon ideas into functional React + Vite applications.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#090d16] text-gray-100 antialiased selection:bg-purple-900 selection:text-white">
        {children}
      </body>
    </html>
  );
}
