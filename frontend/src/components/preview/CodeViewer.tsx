"use client";

import React, { useState } from "react";
import { GeneratedFile } from "@/lib/types";
import { Code2, FileCode, Copy, Check, FileText } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface CodeViewerProps {
  files: GeneratedFile[];
  isMock?: boolean;
}

function getLanguageInfo(filePath: string): { label: string; badgeClass: string } {
  const ext = filePath.split(".").pop()?.toLowerCase() || "";
  switch (ext) {
    case "jsx":
      return { label: "React JSX", badgeClass: "text-cyan-300 bg-cyan-950/60 border-cyan-800/60" };
    case "tsx":
      return { label: "React TSX", badgeClass: "text-blue-300 bg-blue-950/60 border-blue-800/60" };
    case "js":
      return { label: "JavaScript", badgeClass: "text-amber-300 bg-amber-950/60 border-amber-800/60" };
    case "ts":
      return { label: "TypeScript", badgeClass: "text-blue-300 bg-blue-950/60 border-blue-800/60" };
    case "json":
      return { label: "JSON", badgeClass: "text-emerald-300 bg-emerald-950/60 border-emerald-800/60" };
    case "css":
      return { label: "CSS", badgeClass: "text-pink-300 bg-pink-950/60 border-pink-800/60" };
    case "html":
      return { label: "HTML", badgeClass: "text-orange-300 bg-orange-950/60 border-orange-800/60" };
    case "md":
      return { label: "Markdown", badgeClass: "text-purple-300 bg-purple-950/60 border-purple-800/60" };
    default:
      return { label: ext.toUpperCase() || "Plain Text", badgeClass: "text-gray-300 bg-gray-900 border-gray-800" };
  }
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ files, isMock = false }) => {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  const activeFile = files[selectedIdx] || files[0];
  const langInfo = activeFile ? getLanguageInfo(activeFile.path) : null;
  const lineCount = activeFile ? activeFile.content.split("\n").length : 0;

  const handleCopy = async () => {
    if (!activeFile) return;

    try {
      if (typeof navigator !== "undefined" && navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(activeFile.content);
      } else {
        // Fallback for non-secure contexts or iframe restrictions
        const textArea = document.createElement("textarea");
        textArea.value = activeFile.content;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("[CodeViewer] Copy to clipboard failed:", err);
    }
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
              className="text-xs text-gray-300 hover:text-white flex items-center gap-1 border border-gray-800 rounded px-2.5 py-1 bg-gray-900/80 hover:bg-gray-800 transition-colors"
              title="Copy file contents"
            >
              {copied ? (
                <>
                  <Check size={12} className="text-emerald-400" />
                  <span className="text-emerald-300">Copied</span>
                </>
              ) : (
                <>
                  <Copy size={12} />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}
        </div>
      }
    >
      {files.length === 0 ? (
        <div className="py-12 text-center text-xs text-gray-500 font-mono">
          [Code Viewer] No files generated yet. The AI generator will synthesize React + Vite files here.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* File Sidebar */}
          <div className="md:col-span-1 border-r border-gray-800/80 pr-2 space-y-1">
            <div className="flex items-center justify-between pb-1">
              <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">
                Files ({files.length})
              </span>
            </div>
            <div className="mt-1 space-y-0.5 max-h-72 overflow-y-auto">
              {files.map((f, idx) => {
                const info = getLanguageInfo(f.path);
                const isSelected = idx === selectedIdx;
                return (
                  <button
                    key={f.path}
                    onClick={() => setSelectedIdx(idx)}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs flex items-center justify-between font-mono truncate transition-colors ${
                      isSelected
                        ? "bg-purple-950/60 text-purple-200 border border-purple-800/50"
                        : "text-gray-400 hover:bg-gray-800/40 hover:text-gray-200"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      <FileCode size={13} className="shrink-0" />
                      <span className="truncate">{f.path}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Code Area */}
          <div className="md:col-span-3 space-y-2">
            {activeFile && (
              <div className="flex items-center justify-between text-xs text-gray-400 border-b border-gray-800/60 pb-1.5">
                <div className="flex items-center gap-2 font-mono">
                  <FileText size={13} className="text-gray-400" />
                  <span className="text-gray-200 font-semibold">{activeFile.path}</span>
                  {langInfo && (
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${langInfo.badgeClass}`}
                    >
                      {langInfo.label}
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-mono text-gray-400">
                  {lineCount} {lineCount === 1 ? "line" : "lines"}
                </span>
              </div>
            )}

            <div className="rounded-lg bg-[#070a10] border border-gray-800/80 p-3 font-mono text-xs overflow-x-auto max-h-72">
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
