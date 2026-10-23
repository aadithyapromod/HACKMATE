"use client";

import React, { useState, useEffect } from "react";
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
  GeneratedFile,
  BuildResult,
} from "@/lib/types";
import { Sparkles, Layers, Info } from "lucide-react";

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
import { Sparkles, Trophy, Users, Rocket } from 'lucide-react';

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

  const { events, isConnected, latestStatus } = useProjectEvents(
    activeProject?.id || null
  );

  // Check backend health on mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const health = await api.getHealth();
        if (health.status === "ok") {
          setBackendHealthy(true);
        }
      } catch {
        setBackendHealthy(false);
      }
    }
    checkHealth();
  }, []);

  // Update project status if SSE emits update
  useEffect(() => {
    if (latestStatus && activeProject) {
      setActiveProject((prev) =>
        prev ? { ...prev, status: latestStatus as ProjectStatus } : null
      );
    }
  }, [latestStatus]);

  // Handle Idea Submission
  const handleStartBuilding = async (idea: string) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const created = await api.createProject(idea);
      setActiveProject(created);
      setUseMockData(false);

      // Trigger pipeline start
      const started = await api.startProject(created.id);
      setActiveProject(started);

      // Fetch fresh tasks and files
      const fetchedTasks = await api.getProjectTasks(created.id);
      setTasks(fetchedTasks);

      const fetchedFiles = await api.getProjectFiles(created.id);
      setFiles(fetchedFiles.files);

      const fetchedPreview = await api.getProjectPreview(created.id);
      setBuildResult(fetchedPreview);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend service.";
      setErrorMessage(msg);
      // Fallback to demo mode if backend is unreachable
      setActiveProject({
        id: "demo-project-123",
        idea,
        status: "planning",
        created_at: new Date().toISOString(),
      });
      setUseMockData(true);
    } finally {
      setIsSubmitting(false);
    }
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
                <strong>Scaffold Demo Mode:</strong> Displaying mock pipeline components. Submit an idea below or start the backend (`python uvicorn`) to stream live project data.
              </span>
            </div>
            <button
              onClick={() => setUseMockData(false)}
              className="text-purple-400 hover:text-white underline text-[11px]"
            >
              Clear Mock Data
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="rounded-lg border border-rose-900/50 bg-rose-950/20 px-4 py-2.5 text-xs text-rose-300">
            <strong>Backend Connection Notice:</strong> {errorMessage} (Displaying local demo view)
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
