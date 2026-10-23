import React from "react";
import { Terminal, Sparkles, Activity } from "lucide-react";

interface HeaderProps {
  backendConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ backendConnected }) => {
  return (
    <header className="border-b border-gray-800 bg-[#090d16]/90 backdrop-blur sticky top-0 z-50 px-4 sm:px-8 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-purple-500/20">
          <Terminal className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg tracking-tight text-white">HackMate</span>
            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800/50">
              Agentic MVP
            </span>
          </div>
          <p className="text-xs text-gray-400">Autonomous Hackathon Prototype Builder</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`h-2 w-2 rounded-full ${
              backendConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
            }`}
          />
          <span className="text-gray-400">
            {backendConnected ? "Backend Ready" : "Backend Offline / Standby"}
          </span>
        </div>
        <a
          href="https://github.com/aadithyapromod/HACKMATE"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-gray-400 hover:text-white transition-colors border border-gray-800 rounded px-2.5 py-1 bg-gray-900/60"
        >
          GitHub
        </a>
      </div>
    </header>
  );
};
