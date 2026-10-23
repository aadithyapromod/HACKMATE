"use client";

import React, { useState } from "react";
import { GeneratedFile } from "@/lib/types";
import { Code2, FileCode, Copy, Check } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface CodeViewerProps {
  files: GeneratedFile[];
  isMock?: boolean;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ files, isMock = false }) => {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  const activeFile = files[selectedIdx] || files[0];

  const handleCopy = () => {
    if (!activeFile) return;
    navigator.clipboard.writeText(activeFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card
      title="Generated Code Inspector"
      icon={<Code2 className="h-4 w-4" />}
      action={
        <div className="flex items-center gap-2">
          {isMock && (
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
              Mock Template
            </span>
          )}
          {activeFile && (
            <button
              onClick={handleCopy}
              className="text-xs text-gray-400 hover:text-white flex items-center gap-1 border border-gray-800 rounded px-2 py-0.5 bg-gray-900"
            >
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          )}
        </div>
      }
    >
      {files.length === 0 ? (
        <div className="py-12 text-center text-xs text-gray-500 font-mono">
          [Code Viewer] No files generated yet. Pipeline will synthesize React + Vite files here.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-1 border-r border-gray-800/80 pr-2 space-y-1">
            <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">
              Files ({files.length})
            </span>
            <div className="mt-1 space-y-0.5">
              {files.map((f, idx) => (
                <button
                  key={f.path}
                  onClick={() => setSelectedIdx(idx)}
                  className={`w-full text-left px-2 py-1.5 rounded text-xs flex items-center gap-1.5 font-mono truncate transition-colors ${
                    idx === selectedIdx
                      ? "bg-purple-950/60 text-purple-200 border border-purple-800/50"
                      : "text-gray-400 hover:bg-gray-800/40 hover:text-gray-200"
                  }`}
                >
                  <FileCode size={13} className="shrink-0" />
                  <span className="truncate">{f.path}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="md:col-span-3">
            <div className="rounded-lg bg-[#0b0f19] border border-gray-800/80 p-3 font-mono text-xs overflow-x-auto max-h-72">
              <pre className="text-gray-300 whitespace-pre leading-relaxed">
                {activeFile?.content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};
