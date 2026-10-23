"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Sparkles, 
  Terminal as TerminalIcon, 
  Code2, 
  Eye, 
  Download, 
  StopCircle, 
  CheckCircle2, 
  AlertTriangle,
  Layers,
  ArrowRight
} from "lucide-react";
import { 
  Project, 
  FileMetadata, 
  createProject, 
  fetchProject, 
  startProject, 
  cancelProject, 
  fetchProjectFiles, 
  fetchFileContent, 
  getExportZipUrl,
  fetchPreviewMetadata
} from "@/lib/api";
import ProgressStepper from "@/components/ProgressStepper";
import FolderTree from "@/components/FolderTree";
import CodeViewer from "@/components/CodeViewer";
import LivePreview from "@/components/LivePreview";
import TerminalLogs, { LogLine } from "@/components/TerminalLogs";

export default function Dashboard() {
  const [prompt, setPrompt] = useState("");
  const [referenceUrl, setReferenceUrl] = useState("");
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string>("");
  const [activeFileContent, setActiveFileContent] = useState<string>("");
  const [terminalLogs, setTerminalLogs] = useState<LogLine[]>([]);
  const [activeTab, setActiveTab] = useState<"code" | "terminal" | "preview">("code");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Restore existing project from URL or localStorage on refresh
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const savedId = params.get("project") || localStorage.getItem("hackmate_active_project");
    if (savedId) {
      loadProject(savedId);
    }
  }, []);

  const loadProject = async (projectId: string) => {
    try {
      const p = await fetchProject(projectId);
      setCurrentProject(p);
      localStorage.setItem("hackmate_active_project", projectId);

      const fList = await fetchProjectFiles(projectId);
      setFiles(fList);

      if (fList.length > 0) {
        const defaultFile = fList.find(f => f.file_path === "src/App.tsx") || fList[0];
        handleSelectFile(defaultFile.file_path, projectId);
      }

      // Connect SSE if still in progress
      if (["QUEUED", "ANALYZING", "PLANNING", "GENERATING", "WRITING_FILES", "BUILDING", "REPAIRING"].includes(p.status)) {
        connectSSE(projectId);
      }
    } catch (e) {
      console.error("Failed to load project:", e);
    }
  };

  const connectSSE = (projectId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sseUrl = process.env.NEXT_PUBLIC_API_URL 
      ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "")}/api/v2/projects/${projectId}/events`
      : `/api/v2/projects/${projectId}/events`;
    const sse = new EventSource(sseUrl);
    eventSourceRef.current = sse;

    sse.addEventListener("status_changed", (e) => {
      const data = JSON.parse(e.data);
      setCurrentProject(prev => prev ? { ...prev, status: data.to_status } : null);
      if (data.to_status === "READY" || data.to_status === "FAILED") {
        fetchProjectFiles(projectId).then(setFiles);
      }
    });

    sse.addEventListener("file_written", (e) => {
      const data = JSON.parse(e.data);
      setFiles(prev => {
        if (prev.some(f => f.file_path === data.path)) return prev;
        return [...prev, {
          id: data.path,
          file_path: data.path,
          language: "typescript",
          file_size_bytes: data.size,
          version: 1,
          updated_at: new Date().toISOString()
        }];
      });
      // Auto-select first generated main app file
      if (data.path === "src/App.tsx") {
        handleSelectFile("src/App.tsx", projectId);
      }
    });

    sse.addEventListener("build_log", (e) => {
      const data = JSON.parse(e.data);
      setTerminalLogs(prev => [
        ...prev,
        {
          id: Math.random().toString(),
          stream: data.stream,
          text: data.chunk,
          timestamp: new Date().toISOString()
        }
      ]);
    });

    sse.addEventListener("build_completed", (e) => {
      const data = JSON.parse(e.data);
      setCurrentProject(prev => prev ? {
        ...prev,
        status: data.success ? "READY" : "FAILED",
        preview_url: data.preview_url,
        error_message: data.error
      } : null);
      fetchProjectFiles(projectId).then(setFiles);
      sse.close();
    });

    sse.onerror = () => {
      console.warn("SSE connection error, closing stream.");
      sse.close();
    };
  };

  const handleSelectFile = async (path: string, projId?: string) => {
    const id = projId || currentProject?.id;
    if (!id) return;
    setSelectedFilePath(path);
    try {
      const detail = await fetchFileContent(id, path);
      setActiveFileContent(detail.content);
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartGeneration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || prompt.length < 10) return;

    setIsSubmitting(true);
    setTerminalLogs([]);
    setFiles([]);
    setActiveFileContent("");
    setSelectedFilePath("");

    try {
      const proj = await createProject(prompt, referenceUrl);
      setCurrentProject(proj);
      localStorage.setItem("hackmate_active_project", proj.id);
      window.history.pushState({}, "", `?project=${proj.id}`);

      connectSSE(proj.id);
      await startProject(proj.id);
    } catch (err: any) {
      alert(`Error starting generation: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!currentProject) return;
    try {
      await cancelProject(currentProject.id);
      setCurrentProject(prev => prev ? { ...prev, status: "CANCELLED" } : null);
    } catch (err: any) {
      console.error("Cancel failed:", err);
    }
  };

  const handleDownloadZip = () => {
    if (!currentProject) return;
    window.location.href = getExportZipUrl(currentProject.id);
  };

  const isRunning = currentProject && ["QUEUED", "ANALYZING", "PLANNING", "GENERATING", "WRITING_FILES", "BUILDING", "REPAIRING"].includes(currentProject.status);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#0b0e14] text-slate-100 overflow-hidden">
      {/* Top Navigation Bar */}
      <header className="h-14 bg-[#161b22] border-b border-slate-800 px-5 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 rounded-lg bg-blue-600 text-white font-bold flex items-center justify-center">
            <Sparkles size={18} />
          </div>
          <div>
            <div className="font-semibold text-sm tracking-wide text-white flex items-center space-x-2">
              <span>HackMate</span>
              <span className="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded font-mono">
                v2 Core
              </span>
            </div>
            <div className="text-[10px] text-slate-400">
              Autonomous AI Website Generation & Execution Platform
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {isRunning && (
            <button
              onClick={handleCancel}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-rose-900/60 hover:bg-rose-900 border border-rose-700/60 text-xs font-mono text-rose-200 transition-colors"
            >
              <StopCircle size={14} />
              <span>Cancel Run</span>
            </button>
          )}

          {currentProject && (
            <button
              onClick={handleDownloadZip}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-200 transition-colors"
            >
              <Download size={14} />
              <span>Export ZIP</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Studio Body */}
      <div className="flex-1 flex flex-col p-4 overflow-hidden space-y-3">
        {/* Prompt Input Form Bar */}
        <form onSubmit={handleStartGeneration} className="bg-[#161b22] border border-slate-800 rounded-lg p-3 shrink-0">
          <div className="flex flex-col lg:flex-row lg:items-center space-y-2 lg:space-y-0 lg:space-x-3">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Describe your web app idea (e.g. 'A personal expense tracker with category tags, balance charts, and dark theme')..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={Boolean(isRunning || isSubmitting)}
                className="w-full bg-[#0d1117] border border-slate-800 rounded px-3 py-2 text-xs font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500 text-slate-200"
              />
            </div>

            <div className="w-full lg:w-72">
              <input
                type="text"
                placeholder="Optional Reference URL (SSRF guarded)..."
                value={referenceUrl}
                onChange={(e) => setReferenceUrl(e.target.value)}
                disabled={Boolean(isRunning || isSubmitting)}
                className="w-full bg-[#0d1117] border border-slate-800 rounded px-3 py-2 text-xs font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500 text-slate-200"
              />
            </div>

            <button
              type="submit"
              disabled={Boolean(isRunning || isSubmitting || prompt.length < 10)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded text-xs font-medium font-mono flex items-center justify-center space-x-2 shrink-0 transition-all shadow-md"
            >
              <Sparkles size={14} />
              <span>{isRunning ? "Generating..." : "Generate Website"}</span>
            </button>
          </div>
        </form>

        {/* Progress Pipeline Stepper */}
        {currentProject && <ProgressStepper project={currentProject} />}

        {/* Workspace Splitter Panels */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-0 overflow-hidden">
          {/* Left Panel: Tabs for Code Viewer and Terminal Output (7 cols) */}
          <div className="lg:col-span-7 flex flex-col bg-[#161b22] border border-slate-800 rounded-lg overflow-hidden min-h-0">
            {/* Tab Header */}
            <div className="h-10 bg-[#0d1117] border-b border-slate-800 flex items-center justify-between px-3 shrink-0">
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setActiveTab("code")}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-t text-xs font-mono transition-colors ${
                    activeTab === "code"
                      ? "bg-[#161b22] text-white border-t-2 border-blue-500 font-semibold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Code2 size={14} className="text-blue-400" />
                  <span>Code Explorer</span>
                </button>

                <button
                  onClick={() => setActiveTab("terminal")}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-t text-xs font-mono transition-colors ${
                    activeTab === "terminal"
                      ? "bg-[#161b22] text-white border-t-2 border-emerald-500 font-semibold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <TerminalIcon size={14} className="text-emerald-400" />
                  <span>Terminal Logs</span>
                  {terminalLogs.length > 0 && (
                    <span className="text-[10px] bg-slate-800 px-1 py-0.2 rounded font-mono text-slate-300">
                      {terminalLogs.length}
                    </span>
                  )}
                </button>
              </div>

              <div className="text-[11px] text-slate-500 font-mono hidden sm:inline">
                Target: React 18 + Vite + Tailwind
              </div>
            </div>

            {/* Tab Body */}
            <div className="flex-1 min-h-0 overflow-hidden">
              {activeTab === "code" ? (
                <div className="h-full grid grid-cols-12 min-h-0">
                  {/* File Tree (4 cols) */}
                  <div className="col-span-4 h-full border-r border-slate-800/80 min-h-0">
                    <FolderTree
                      files={files}
                      selectedPath={selectedFilePath}
                      onSelectFile={handleSelectFile}
                    />
                  </div>

                  {/* Code Editor (8 cols) */}
                  <div className="col-span-8 h-full min-h-0">
                    <CodeViewer
                      filePath={selectedFilePath}
                      content={activeFileContent}
                      projectId={currentProject?.id || ""}
                      onDownloadZip={handleDownloadZip}
                    />
                  </div>
                </div>
              ) : (
                <TerminalLogs
                  logs={terminalLogs}
                  onClearLogs={() => setTerminalLogs([])}
                />
              )}
            </div>
          </div>

          {/* Right Panel: Live Interactive Preview (5 cols) */}
          <div className="lg:col-span-5 flex flex-col min-h-0">
            <LivePreview
              previewUrl={currentProject?.preview_url || null}
              status={currentProject?.status || "QUEUED"}
              errorMessage={currentProject?.error_message}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
