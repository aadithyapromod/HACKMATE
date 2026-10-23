import {
  Project,
  ProjectCreateRequest,
  Task,
  FileListResponse,
  BuildResult,
  HealthResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Use fallback error message
    }
    throw new ApiError(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health");
  },

  async createProject(idea: string): Promise<Project> {
    const payload: ProjectCreateRequest = { idea };
    return request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getProject(id: string): Promise<Project> {
    return request<Project>(`/api/projects/${id}`);
  },

  async startProject(id: string): Promise<Project> {
    return request<Project>(`/api/projects/${id}/start`, {
      method: "POST",
    });
  },

  async getProjectTasks(id: string): Promise<Task[]> {
    return request<Task[]>(`/api/projects/${id}/tasks`);
  },

  async getProjectFiles(id: string): Promise<FileListResponse> {
    return request<FileListResponse>(`/api/projects/${id}/files`);
  },

  async getProjectPreview(id: string): Promise<BuildResult> {
    return request<BuildResult>(`/api/projects/${id}/preview`);
  },

  getEventsUrl(id: string): string {
    return `${BASE_URL}/api/projects/${id}/events`;
  },
};
