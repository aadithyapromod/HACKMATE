"use client";

import React, { useEffect, useRef } from "react";
import { Terminal, CheckCircle2, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { BuildResult } from "@/lib/types";

interface BuildLogsProps {
  buildResult: BuildResult | null;
  isMock?: boolean;
}

export const BuildLogs: React.FC<BuildLogsProps> = ({
  buildResult,
  isMock = false,
}) => {
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [buildResult?.logs]);

  return (
    <Card
      title="Runner Sandbox Build Logs"
      icon={<Terminal className="h-4 w-4" />}
      action={
        <div className="flex items-center gap-2">
          {isMock && (
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
              Mock Stream
            </span>
          )}
          {buildResult && (
            <span
              className={`inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded border ${
                buildResult.success
                  ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/60"
                  : "bg-rose-950/60 text-rose-300 border-rose-800/60"
              }`}
            >
              {buildResult.success ? (
                <CheckCircle2 size={12} />
              ) : (
                <AlertCircle size={12} />
              )}
              <span>exit code {buildResult.exit_code}</span>
            </span>
          )}
        </div>
      }
    >
      <div
        ref={logContainerRef}
        className="rounded-lg bg-[#070a10] border border-gray-800/90 p-3 font-mono text-xs text-gray-300 overflow-y-auto max-h-52 leading-relaxed"
      >
        {buildResult?.logs ? (
          <pre className="whitespace-pre-wrap">{buildResult.logs}</pre>
        ) : (
          <div className="text-gray-400 italic">
            [Runner Logs] Sandbox runner waiting for build trigger...
          </div>
        )}
      </div>
    </Card>
  );
};
