"use client";

import React from "react";
import { CheckCircle2, Circle, AlertCircle, Loader2, Wrench } from "lucide-react";
import { Project } from "@/lib/api";

interface ProgressStepperProps {
  project: Project | null;
}

const STAGES = [
  { key: "ANALYZING", label: "Requirements Analysis" },
  { key: "PLANNING", label: "Solution Planning" },
  { key: "GENERATING", label: "Code Synthesis" },
  { key: "WRITING_FILES", label: "Writing Workspace" },
  { key: "BUILDING", label: "Sandbox Build & Test" },
  { key: "READY", label: "Live Preview Ready" },
];

export default function ProgressStepper({ project }: ProgressStepperProps) {
  if (!project) return null;

  const currentStatus = project.status;
  const isRepairing = currentStatus === "REPAIRING";
  const isFailed = currentStatus === "FAILED";
  const isCancelled = currentStatus === "CANCELLED";

  const getStageIndex = (status: string) => {
    switch (status) {
      case "QUEUED": return 0;
      case "ANALYZING": return 0;
      case "PLANNING": return 1;
      case "GENERATING": return 2;
      case "WRITING_FILES": return 3;
      case "BUILDING": return 4;
      case "REPAIRING": return 4;
      case "READY": return 5;
      case "FAILED": return 4;
      default: return 0;
    }
  };

  const currentIndex = getStageIndex(currentStatus);

  return (
    <div className="w-full bg-[#161b22] border border-slate-800 rounded-lg p-4 my-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Pipeline Execution
          </span>
          <span
            className={`px-2 py-0.5 text-[11px] font-mono rounded font-medium ${
              currentStatus === "READY"
                ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                : isFailed
                ? "bg-rose-950 text-rose-300 border border-rose-700/60"
                : isCancelled
                ? "bg-amber-950 text-amber-300 border border-amber-700/60"
                : "bg-blue-950 text-blue-300 border border-blue-700/60 animate-pulse"
            }`}
          >
            {currentStatus}
          </span>
        </div>

        {isRepairing && (
          <div className="flex items-center space-x-1.5 text-xs text-amber-300 font-mono bg-amber-950/60 border border-amber-700/50 px-2 py-0.5 rounded">
            <Wrench size={13} className="animate-spin" />
            <span>Autonomous Repair in Progress (Attempt {project.current_repair_iteration + 1}/1)</span>
          </div>
        )}
      </div>

      {/* Stepper Steps */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        {STAGES.map((stage, idx) => {
          let state: "completed" | "current" | "pending" | "failed" = "pending";

          if (currentStatus === "READY") {
            state = "completed";
          } else if (isFailed && idx === currentIndex) {
            state = "failed";
          } else if (idx < currentIndex) {
            state = "completed";
          } else if (idx === currentIndex) {
            state = "current";
          }

          return (
            <div
              key={stage.key}
              className={`flex items-center space-x-2 p-2 rounded border text-xs font-medium transition-all ${
                state === "completed"
                  ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-300"
                  : state === "current"
                  ? "bg-blue-950/30 border-blue-600/70 text-blue-200 shadow-sm"
                  : state === "failed"
                  ? "bg-rose-950/30 border-rose-600/70 text-rose-300"
                  : "bg-slate-900/40 border-slate-800 text-slate-500"
              }`}
            >
              {state === "completed" && <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />}
              {state === "current" && <Loader2 size={16} className="text-blue-400 animate-spin shrink-0" />}
              {state === "failed" && <AlertCircle size={16} className="text-rose-400 shrink-0" />}
              {state === "pending" && <Circle size={16} className="text-slate-600 shrink-0" />}

              <span className="truncate">{stage.label}</span>
            </div>
          );
        })}
      </div>

      {isFailed && project.error_message && (
        <div className="mt-3 p-2.5 rounded bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs font-mono">
          <span className="font-semibold text-rose-200">Build Failure: </span>
          {project.error_message}
        </div>
      )}
    </div>
  );
}
