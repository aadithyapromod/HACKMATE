export type ProjectStatus =
  | "created"
  | "planning"
  | "generating"
  | "building"
  | "testing"
  | "repairing"
  | "completed"
  | "failed";

export interface Project {
  id: string;
  idea: string;
  status: ProjectStatus;
  created_at: string;
}

export interface ProjectCreateRequest {
  idea: string;
}

export type TaskStatus = "pending" | "running" | "completed" | "failed";

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
}

export interface GeneratedFile {
  path: string;
  content: string;
}

export interface FileListResponse {
  files: GeneratedFile[];
}

export interface BuildResult {
  success: boolean;
  exit_code: number;
  logs: string;
  preview_url: string | null;
}

export type EventType =
  | "project.status"
  | "task.updated"
  | "agent.status"
  | "build.log"
  | "build.completed"
  | "preview.ready"
  | "project.completed"
  | "project.failed";

export interface AgentEvent {
  event_type: EventType;
  project_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
}
