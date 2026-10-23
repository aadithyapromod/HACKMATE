"use client";

import React, { useState, useRef } from "react";
import { Monitor, Tablet, Smartphone, RotateCw, ExternalLink, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";

interface LivePreviewProps {
  previewUrl: string | null;
  status: string;
  errorMessage?: string | null;
}

type ViewportMode = "desktop" | "tablet" | "mobile";

export default function LivePreview({ previewUrl, status, errorMessage }: LivePreviewProps) {
  const [viewport, setViewport] = useState<ViewportMode>("desktop");
  const [reloadKey, setReloadKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const isReady = status === "READY" && !!previewUrl;
  const isBuilding = ["ANALYZING", "PLANNING", "GENERATING", "WRITING_FILES", "BUILDING", "REPAIRING"].includes(status);
  const isFailed = status === "FAILED";

  const handleReload = () => {
    setReloadKey(k => k + 1);
  };

  const getViewportWidth = () => {
    switch (viewport) {
      case "mobile": return "375px";
      case "tablet": return "768px";
      case "desktop":
      default: return "100%";
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#0b0e14] border border-slate-800 rounded-lg overflow-hidden">
      {/* Preview Navigation Bar */}
      <div className="h-10 bg-[#161b22] border-b border-slate-800 flex items-center justify-between px-3 select-none">
        {/* Viewport Toggles */}
        <div className="flex items-center space-x-1 bg-slate-900/80 p-0.5 rounded border border-slate-800">
          <button
            onClick={() => setViewport("desktop")}
            className={`p-1 rounded transition-colors ${
              viewport === "desktop" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
            title="Desktop View (100%)"
          >
            <Monitor size={14} />
          </button>
          <button
            onClick={() => setViewport("tablet")}
            className={`p-1 rounded transition-colors ${
              viewport === "tablet" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
            title="Tablet View (768px)"
          >
            <Tablet size={14} />
          </button>
          <button
            onClick={() => setViewport("mobile")}
            className={`p-1 rounded transition-colors ${
              viewport === "mobile" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
            title="Mobile View (375px)"
          >
            <Smartphone size={14} />
          </button>
        </div>

        {/* Status indicator */}
        <div className="flex items-center space-x-1 text-xs text-slate-400 font-mono">
          <ShieldCheck size={14} className="text-emerald-400" />
          <span className="hidden sm:inline">Sandboxed IFrame Preview</span>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-1.5">
          <button
            onClick={handleReload}
            disabled={!isReady}
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 disabled:opacity-30"
            title="Reload Preview"
          >
            <RotateCw size={14} />
          </button>

          {isReady && previewUrl && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 text-slate-400 hover:text-blue-400 rounded hover:bg-slate-800"
              title="Open in new window"
            >
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      </div>

      {/* Frame Container */}
      <div className="flex-1 bg-slate-950 flex items-center justify-center p-2 overflow-auto">
        {isReady && previewUrl ? (
          <div
            style={{ width: getViewportWidth(), height: "100%" }}
            className="transition-all duration-300 shadow-2xl rounded overflow-hidden border border-slate-800 bg-white"
          >
            <iframe
              key={reloadKey}
              ref={iframeRef}
              src={previewUrl}
              sandbox="allow-scripts allow-forms allow-same-origin"
              className="w-full h-full border-0"
              title="Generated App Live Preview"
            />
          </div>
        ) : isBuilding ? (
          <div className="flex flex-col items-center justify-center text-center p-8 text-slate-400 space-y-3">
            <Loader2 size={36} className="text-blue-500 animate-spin" />
            <div className="text-sm font-medium text-slate-200">
              Compiling application inside Docker sandbox...
            </div>
            <div className="text-xs text-slate-500 max-w-sm">
              Live preview will automatically mount as soon as the sandbox build succeeds and passes validation.
            </div>
          </div>
        ) : isFailed ? (
          <div className="flex flex-col items-center justify-center text-center p-8 text-rose-300 space-y-3 max-w-md">
            <AlertCircle size={36} className="text-rose-500" />
            <div className="text-sm font-medium text-rose-200">
              Build Failed — Preview Unavailable
            </div>
            <div className="text-xs text-rose-400 font-mono bg-rose-950/40 p-3 rounded border border-rose-900/60 break-all text-left w-full">
              {errorMessage || "Check the compiler terminal logs for detailed stack traces."}
            </div>
          </div>
        ) : (
          <div className="text-center p-8 text-slate-500 text-xs italic">
            Enter a prompt and click "Generate Website" to start autonomous building.
          </div>
        )}
      </div>
    </div>
  );
}
