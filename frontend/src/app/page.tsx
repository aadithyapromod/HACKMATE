"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Header } from "@/components/dashboard/Header";
import { IdeaInput } from "@/components/dashboard/IdeaInput";
import { ProjectStatusBadge } from "@/components/project/ProjectStatusBadge";
import { TaskList } from "@/components/tasks/TaskList";
import { ActivityFeed } from "@/components/activity/ActivityFeed";
import { CodeViewer } from "@/components/preview/CodeViewer";
import { AppPreview } from "@/components/preview/AppPreview";
import { BuildLogs } from "@/components/preview/BuildLogs";
import { useProjectEvents } from "@/hooks/useProjectEvents";
import { api } from "@/lib/api";
import {
  Project,
  ProjectStatus,
  Task,
  TaskStatus,
  GeneratedFile,
  BuildResult,
  AgentEvent,
} from "@/lib/types";
import { isValidPreviewUrl } from "@/lib/utils";
import { Sparkles, Info, RefreshCw, FolderGit2, AlertTriangle } from "lucide-react";

// Clearly labeled mock data for initial UI inspection and teammate demonstration
const MOCK_TASKS: Task[] = [
  {
    id: "task-1",
    title: "Project Architecture & Requirements",
    description: "Analyze concept and decompose into modular React component structure.",
    status: "completed",
  },
  {
    id: "task-2",
    title: "Scaffold Vite + React Structure",
    description: "Generate package.json, index.html, vite.config.js, and main entry.",
    status: "completed",
  },
  {
    id: "task-3",
    title: "Synthesize Core UI Components",
    description: "Generate responsive navigation, interactive dashboard, and state containers.",
    status: "running",
  },
  {
    id: "task-4",
    title: "Runner Sandbox Validation",
    description: "Execute containerized build and verify zero console errors.",
    status: "pending",
  },
];

const MOCK_FILES: GeneratedFile[] = [
  {
    path: "src/App.jsx",
    content: `import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';

export default function App() {
  const [joined, setJoined] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      <header className="max-w-4xl mx-auto flex justify-between items-center pb-8 border-b border-slate-800">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
          HackMate Matching
        </h1>
        <button 
          onClick={() => setJoined(!joined)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-semibold transition"
        >
          {joined ? 'Team Joined!' : 'Find Team'}
        </button>
      </header>
    </div>
  );
}`,
  },
  {
    path: "package.json",
    content: `{
  "name": "hackmate-generated-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.453.0"
  }
}`,
  },
];

const MOCK_BUILD: BuildResult = {
  success: true,
  exit_code: 0,
  logs: `[Runner Daemon] Initialized sandbox container
[Runner Daemon] Staging project files into /workspace...
[Runner Daemon] Installing dependencies: react, react-dom, lucide-react
[Runner Daemon] npm install completed in 2.8s
[Runner Daemon] vite v5.4.9 building for production...
✓ 4 modules transformed.
dist/index.html   0.45 kB
dist/assets/index.js   142.12 kB
✓ built in 184ms
[Runner Daemon] Build status: SUCCESS. Container ready for preview.`,
  preview_url: null,
};

export default function DashboardPage() {
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [tasks, setTasks] = useState<Task[]>(MOCK_TASKS);
  const [files, setFiles] = useState<GeneratedFile[]>(MOCK_FILES);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(MOCK_BUILD);
  const [useMockData, setUseMockData] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [projectLookupId, setProjectLookupId] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);

  // Reference tracking currently active project ID to guard against stale async responses
  const activeProjectIdRef = useRef<string | null>(null);
  const refreshTimersRef = useRef<{ [key: string]: NodeJS.Timeout }>({});

  // Debounce helper to coalesce fast SSE updates and avoid redundant network requests
  const debouncedAction = useCallback((key: string, fn: () => void, delayMs = 350) => {
    if (refreshTimersRef.current[key]) {
      clearTimeout(refreshTimersRef.current[key]);
    }
    refreshTimersRef.current[key] = setTimeout(() => {
      delete refreshTimersRef.current[key];
      fn();
    }, delayMs);
  }, []);

  // Cleanup all timers on unmount
  useEffect(() => {
    return () => {
      Object.values(refreshTimersRef.current).forEach(clearTimeout);
      refreshTimersRef.current = {};
    };
  }, []);

  // Check backend health on mount
  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        const health = await api.getHealth();
        if (isMounted && health.status === "ok") {
          setBackendHealthy(true);
        }
      } catch {
        if (isMounted) {
          setBackendHealthy(false);
        }
      }
    }
    checkHealth();
    return () => {
      isMounted = false;
    };
  }, []);

  // Authoritative data fetch for a given project ID
  const fetchProjectState = useCallback(
    async (projectId: string, silent = false) => {
      if (!silent) setIsSyncing(true);
      try {
        const [proj, freshTasks, fileList, preview] = await Promise.all([
          api.getProject(projectId),
          api.getProjectTasks(projectId),
          api.getProjectFiles(projectId),
          api.getProjectPreview(projectId),
        ]);

        // Guard against race conditions when user switches project during fetch
        if (activeProjectIdRef.current === projectId) {
          setActiveProject(proj);
          setTasks(freshTasks);
          setFiles(fileList.files);
          setBuildResult(preview);
        }
      } catch (err: unknown) {
        if (activeProjectIdRef.current === projectId) {
          const msg = err instanceof Error ? err.message : "Failed to sync project state.";
          setErrorMessage(msg);
        }
      } finally {
        if (!silent) setIsSyncing(false);
      }
    },
    []
  );

  // Switch to a new or existing project
  const selectProject = useCallback(
    async (projectId: string | null) => {
      // Clear active timers
      Object.values(refreshTimersRef.current).forEach(clearTimeout);
      refreshTimersRef.current = {};

      if (!projectId) {
        activeProjectIdRef.current = null;
        setActiveProject(null);
        setTasks(MOCK_TASKS);
        setFiles(MOCK_FILES);
        setBuildResult(MOCK_BUILD);
        setUseMockData(true);
        setErrorMessage(null);
        return;
      }

      activeProjectIdRef.current = projectId;
      setUseMockData(false);
      setErrorMessage(null);

      await fetchProjectState(projectId);
    },
    [fetchProjectState]
  );

  // SSE event handlers configured via useProjectEvents
  const { events, isConnected, connectionError } = useProjectEvents(
    activeProject?.id || null,
    {
      onStatusChange: (status) => {
        setActiveProject((prev) =>
          prev ? { ...prev, status: status as ProjectStatus } : null
        );

        const currentId = activeProjectIdRef.current;
        if (!currentId) return;

        // Refresh tasks and files when state moves to generating or building
        debouncedAction("status_sync", () => {
          fetchProjectState(currentId, true);
        }, 400);
      },

      onTaskUpdated: (event: AgentEvent) => {
        // Optimistic inline update if task fields are present in data
        const taskId = event.data?.task_id as string | undefined;
        const newStatus = event.data?.status as TaskStatus | undefined;
        const newTitle = event.data?.title as string | undefined;

        if (taskId && newStatus) {
          setTasks((prev) =>
            prev.map((t) =>
              t.id === taskId
                ? { ...t, status: newStatus, title: newTitle || t.title }
                : t
            )
          );
        }

        const currentId = activeProjectIdRef.current;
        if (!currentId) return;

        // Authoritative debounced refresh of task list
        debouncedAction("tasks_refresh", async () => {
          try {
            const freshTasks = await api.getProjectTasks(currentId);
            if (activeProjectIdRef.current === currentId) {
              setTasks(freshTasks);
            }
          } catch (e) {
            console.error("[Tasks Refresh Error]", e);
          }
        }, 350);
      },

      onBuildLog: (event: AgentEvent) => {
        // Support either chunk, logs, or message as per contract
        const chunk = event.data?.chunk ?? event.data?.logs ?? event.data?.message;
        if (chunk !== undefined && chunk !== null) {
          const chunkStr = String(chunk);
          setBuildResult((prev) => {
            if (!prev) {
              return { success: false, exit_code: 0, logs: chunkStr, preview_url: null };
            }
            // If server sends full log text vs. incremental delta chunk
            const updatedLogs = prev.logs
              ? prev.logs.includes(chunkStr)
                ? prev.logs
                : `${prev.logs}\n${chunkStr}`
              : chunkStr;
            return { ...prev, logs: updatedLogs };
          });
        }
      },

      onBuildCompleted: (event: AgentEvent) => {
        const success = typeof event.data?.success === "boolean" ? event.data.success : true;
        const exitCode = typeof event.data?.exit_code === "number" ? event.data.exit_code : 0;

        setBuildResult((prev) => ({
          success,
          exit_code: exitCode,
          logs: prev?.logs || "Build completed.",
          preview_url: prev?.preview_url || null,
        }));

        const currentId = activeProjectIdRef.current;
        if (!currentId) return;

        // Refresh project, tasks, files, and build info
        debouncedAction("build_completed_sync", () => {
          fetchProjectState(currentId, true);
        }, 300);
      },

      onPreviewReady: (event: AgentEvent) => {
        const rawUrl = event.data?.preview_url ? String(event.data.preview_url) : null;
        if (rawUrl && isValidPreviewUrl(rawUrl)) {
          setBuildResult((prev) =>
            prev
              ? { ...prev, preview_url: rawUrl }
              : { success: true, exit_code: 0, logs: "", preview_url: rawUrl }
          );
        }
      },

      onProjectCompleted: (event: AgentEvent) => {
        setActiveProject((prev) =>
          prev ? { ...prev, status: "completed" as ProjectStatus } : null
        );

        const rawUrl = event.data?.preview_url ? String(event.data.preview_url) : null;
        if (rawUrl && isValidPreviewUrl(rawUrl)) {
          setBuildResult((prev) =>
            prev
              ? { ...prev, preview_url: rawUrl }
              : { success: true, exit_code: 0, logs: "", preview_url: rawUrl }
          );
        }

        const currentId = activeProjectIdRef.current;
        if (!currentId) return;

        debouncedAction("project_completed_sync", () => {
          fetchProjectState(currentId, true);
        }, 250);
      },

      onProjectFailed: (event: AgentEvent) => {
        setActiveProject((prev) =>
          prev ? { ...prev, status: "failed" as ProjectStatus } : null
        );

        const err = event.data?.error ? String(event.data.error) : "Pipeline execution failed.";
        setErrorMessage(`Pipeline failed: ${err}`);

        const currentId = activeProjectIdRef.current;
        if (!currentId) return;

        debouncedAction("project_failed_sync", () => {
          fetchProjectState(currentId, true);
        }, 250);
      },
    }
  );

  // Handle Idea Submission
  const handleStartBuilding = async (idea: string) => {
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      // 1. Create project via POST /api/projects
      const created = await api.createProject(idea);
      activeProjectIdRef.current = created.id;
      setActiveProject(created);
      setUseMockData(false);
      setTasks([]);
      setFiles([]);
      setBuildResult(null);

      // 2. Start pipeline via POST /api/projects/{id}/start
      const started = await api.startProject(created.id);
      if (activeProjectIdRef.current === created.id) {
        setActiveProject(started);
      }

      // 3. Fetch initial state
      await fetchProjectState(created.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend service.";
      setErrorMessage(msg);
      // Local fallback representation if backend is completely offline
      setActiveProject({
        id: "demo-project-offline",
        idea,
        status: "created",
        created_at: new Date().toISOString(),
      });
      setUseMockData(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Switch or lookup project by ID
  const handleLookupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = projectLookupId.trim();
    if (!cleanId) return;
    await selectProject(cleanId);
  };

  const currentStatus = activeProject ? activeProject.status : "created";

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16]">
      <Header backendConnected={backendHealthy} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Banner notification for Mock / Demo Mode */}
        {useMockData && (
          <div className="flex items-center justify-between rounded-lg border border-purple-900/50 bg-purple-950/20 px-4 py-2.5 text-xs text-purple-200">
            <div className="flex items-center gap-2">
              <Info size={16} className="text-purple-400 shrink-0" />
              <span>
                <strong>Scaffold Demo Mode:</strong> Displaying mock pipeline components. Submit an idea below or start the backend (`uvicorn app.main:app`) to stream live project data.
              </span>
            </div>
            <button
              onClick={() => selectProject(null)}
              className="text-purple-400 hover:text-white underline text-[11px]"
            >
              Reset to Standby
            </button>
          </div>
        )}

        {/* Real-time SSE Connection Status Banner */}
        {activeProject && !useMockData && (
          <div className="flex items-center justify-between rounded-lg border border-gray-800 bg-[#111827]/70 px-4 py-2 text-xs">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span
                  className={`h-2 w-2 rounded-full ${
                    isConnected
                      ? "bg-emerald-400 animate-pulse"
                      : connectionError
                      ? "bg-rose-400"
                      : "bg-amber-400"
                  }`}
                />
                <span className="font-mono text-gray-300">
                  {isConnected
                    ? "SSE Stream Active"
                    : connectionError
                    ? "SSE Reconnecting..."
                    : "Connecting to Event Stream..."}
                </span>
              </div>
              <span className="text-gray-500">•</span>
              <div className="flex items-center gap-1.5 font-mono text-gray-400">
                <FolderGit2 size={13} className="text-purple-400" />
                <span>Project:</span>
                <span className="text-gray-200 font-semibold">{activeProject.id}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isSyncing && (
                <span className="text-purple-400 flex items-center gap-1 text-[11px] font-mono animate-pulse">
                  <RefreshCw size={11} className="animate-spin" />
                  Syncing
                </span>
              )}
              <button
                onClick={() => fetchProjectState(activeProject.id)}
                className="text-gray-400 hover:text-white flex items-center gap-1 text-[11px] font-mono border border-gray-800 rounded px-2 py-0.5 bg-gray-900 hover:bg-gray-800 transition-colors"
                title="Force refresh project state from backend"
              >
                <RefreshCw size={11} />
                Refresh
              </button>
            </div>
          </div>
        )}

        {/* Error Notice */}
        {errorMessage && (
          <div className="flex items-center gap-2 rounded-lg border border-rose-900/50 bg-rose-950/20 px-4 py-2.5 text-xs text-rose-300">
            <AlertTriangle size={15} className="shrink-0 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Top Hero / Idea Input Section */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary-light" />
                <span>Autonomous Prototype Workspace</span>
              </h2>
              <p className="text-xs text-gray-400">
                Transform any hackathon prompt into a validated, runnable React + Vite MVP.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400">Project Status:</span>
              <ProjectStatusBadge status={currentStatus} />
            </div>
          </div>

          <IdeaInput onSubmit={handleStartBuilding} isLoading={isSubmitting} />

          {/* Quick Lookup Bar */}
          <div className="flex items-center justify-between pt-1 text-xs text-gray-500">
            <form onSubmit={handleLookupSubmit} className="flex items-center gap-2">
              <span className="font-mono text-[11px]">Load Project by ID:</span>
              <input
                type="text"
                value={projectLookupId}
                onChange={(e) => setProjectLookupId(e.target.value)}
                placeholder="project-..."
                className="bg-[#111827] border border-gray-800 rounded px-2 py-0.5 text-xs text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-600 font-mono"
              />
              <button
                type="submit"
                className="text-[11px] font-mono text-gray-400 hover:text-white border border-gray-800 rounded px-2 py-0.5 bg-gray-900 hover:bg-gray-800"
              >
                Switch
              </button>
            </form>

            {activeProject && !useMockData && (
              <button
                onClick={() => selectProject(null)}
                className="text-[11px] font-mono text-gray-500 hover:text-gray-300 underline"
              >
                Back to Demo Mode
              </button>
            )}
          </div>
        </section>

        {/* Main Grid: Left = Tasks & Activity, Right = Preview, Code & Logs */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Tasks & Agent Stream */}
          <div className="lg:col-span-5 space-y-6">
            <TaskList tasks={tasks} isMock={useMockData} />
            <ActivityFeed events={events} isMock={useMockData} />
          </div>

          {/* Right Column: Preview, Code Inspector, and Build Logs */}
          <div className="lg:col-span-7 space-y-6">
            <AppPreview
              previewUrl={buildResult?.preview_url || null}
              isMock={useMockData}
            />
            <CodeViewer files={files} isMock={useMockData} />
            <BuildLogs buildResult={buildResult} isMock={useMockData} />
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/80 py-4 text-center text-xs text-gray-400">
        HackMate MVP • React + Vite Autonomous Pipeline • Built for 19-Hour Team Sprint
      </footer>
    </div>
  );
}
