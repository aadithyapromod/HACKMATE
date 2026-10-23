"use client";

import React, { useRef, useEffect, useState } from "react";
import { Terminal, Copy, Trash2, ArrowDown } from "lucide-react";

export interface LogLine {
  id: string;
  stream: "stdout" | "stderr" | "system";
  text: string;
  timestamp: string;
}

interface TerminalLogsProps {
  logs: LogLine[];
  onClearLogs?: () => void;
}

export default function TerminalLogs({ logs, onClearLogs }: TerminalLogsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const copyLogs = () => {
    const raw = logs.map(l => l.text).join("");
    navigator.clipboard.writeText(raw);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0b0e14] border border-slate-800 rounded-lg overflow-hidden">
      {/* Terminal Title Bar */}
      <div className="h-9 bg-[#161b22] border-b border-slate-800 flex items-center justify-between px-3 select-none">
        <div className="flex items-center space-x-2">
          <Terminal size={14} className="text-emerald-400" />
          <span className="text-xs font-mono font-medium text-slate-300">
            Docker Build & Compiler Output
          </span>
          <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-mono">
            {logs.length} lines
          </span>
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded border transition-colors ${
              autoScroll
                ? "bg-blue-600/30 border-blue-500/50 text-blue-300"
                : "bg-slate-800 border-slate-700 text-slate-400 hover:text-white"
            }`}
          >
            Auto-scroll: {autoScroll ? "ON" : "OFF"}
          </button>
          <button
            onClick={copyLogs}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
            title="Copy logs"
          >
            <Copy size={13} />
          </button>
          {onClearLogs && (
            <button
              onClick={onClearLogs}
              className="p-1 text-slate-400 hover:text-rose-400 rounded hover:bg-slate-800"
              title="Clear logs"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Terminal Log View */}
      <div
        ref={containerRef}
        className="flex-1 p-3 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-300 space-y-0.5"
      >
        {logs.length === 0 ? (
          <div className="text-slate-600 italic select-none">
            Awaiting build execution... Compiler stdout and stderr will stream here in real-time.
          </div>
        ) : (
          logs.map((line) => {
            let textColor = "text-slate-300";
            if (line.stream === "stderr") {
              textColor = line.text.toLowerCase().includes("error")
                ? "text-rose-400 font-medium"
                : "text-amber-300";
            } else if (line.stream === "system") {
              textColor = "text-emerald-400";
            }

            return (
              <div key={line.id} className="whitespace-pre-wrap break-all font-mono">
                <span className={textColor}>{line.text}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
