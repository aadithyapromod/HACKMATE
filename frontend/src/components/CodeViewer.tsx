"use client";

import React, { useState, useEffect } from "react";
import { Copy, Check, Download, FileCode, ExternalLink } from "lucide-react";
import Prism from "prismjs";
import "prismjs/components/prism-typescript";
import "prismjs/components/prism-jsx";
import "prismjs/components/prism-tsx";
import "prismjs/components/prism-json";
import "prismjs/components/prism-css";
import "prismjs/components/prism-markdown";
import "prismjs/components/prism-python";

interface CodeViewerProps {
  filePath: string;
  content: string;
  projectId: string;
  onDownloadZip?: () => void;
}

export default function CodeViewer({ filePath, content, projectId, onDownloadZip }: CodeViewerProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    Prism.highlightAll();
  }, [content, filePath]);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLanguage = (path: string) => {
    if (path.endsWith(".tsx")) return "tsx";
    if (path.endsWith(".ts")) return "typescript";
    if (path.endsWith(".jsx")) return "jsx";
    if (path.endsWith(".js")) return "javascript";
    if (path.endsWith(".json")) return "json";
    if (path.endsWith(".css")) return "css";
    if (path.endsWith(".html")) return "html";
    if (path.endsWith(".py")) return "python";
    if (path.endsWith(".md")) return "markdown";
    return "text";
  };

  const lines = content.split("\n");
  const lang = getLanguage(filePath);

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1117] text-slate-200 overflow-hidden">
      {/* Editor Header Bar */}
      <div className="h-10 bg-[#161b22] border-b border-slate-800 flex items-center justify-between px-4 select-none">
        <div className="flex items-center space-x-2 truncate">
          <FileCode size={16} className="text-blue-400 shrink-0" />
          <span className="text-xs font-mono font-medium text-slate-200 truncate">
            {filePath || "No file selected"}
          </span>
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {lang}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            disabled={!content}
            className="flex items-center space-x-1 px-2.5 py-1 text-xs font-mono rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors disabled:opacity-40"
          >
            {copied ? (
              <>
                <Check size={13} className="text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={13} />
                <span>Copy</span>
              </>
            )}
          </button>

          {onDownloadZip && (
            <button
              onClick={onDownloadZip}
              className="flex items-center space-x-1 px-2.5 py-1 text-xs font-mono rounded bg-blue-600/80 hover:bg-blue-600 text-white transition-colors"
            >
              <Download size={13} />
              <span>Download ZIP</span>
            </button>
          )}
        </div>
      </div>

      {/* Code Editor Body with Line Numbers */}
      <div className="flex-1 overflow-auto font-mono text-xs leading-relaxed flex">
        {content ? (
          <div className="flex min-w-full">
            {/* Line numbers column */}
            <div className="select-none py-3 px-3 text-right bg-[#0d1117] border-r border-slate-800/60 text-slate-600 font-mono text-[11px] shrink-0 min-w-[3rem]">
              {lines.map((_, idx) => (
                <div key={idx} className="h-5 leading-5">
                  {idx + 1}
                </div>
              ))}
            </div>

            {/* Code content */}
            <pre className="flex-1 p-3 m-0 bg-transparent overflow-x-auto whitespace-pre font-mono">
              <code className={`language-${lang} font-mono leading-5 block`}>
                {content}
              </code>
            </pre>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500 italic text-xs">
            Select a file from the explorer to view its contents.
          </div>
        )}
      </div>
    </div>
  );
}
