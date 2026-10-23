import {
  Project,
  ProjectCreateRequest,
  Task,
  FileListResponse,
  BuildResult,
  HealthResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
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
  async getHealth(options?: RequestInit): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health", options);
  },

  async createProject(idea: string, options?: RequestInit): Promise<Project> {
    const payload: ProjectCreateRequest = { idea };
    return request<Project>("/api/projects", {
      ...options,
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getProject(id: string, options?: RequestInit): Promise<Project> {
    return request<Project>(`/api/projects/${id}`, options);
  },

  async startProject(id: string, options?: RequestInit): Promise<Project> {
    return request<Project>(`/api/projects/${id}/start`, {
      ...options,
      method: "POST",
    });
  },

  async getProjectTasks(id: string, options?: RequestInit): Promise<Task[]> {
    return request<Task[]>(`/api/projects/${id}/tasks`, options);
  },

  async getProjectFiles(id: string, options?: RequestInit): Promise<FileListResponse> {
    return request<FileListResponse>(`/api/projects/${id}/files`, options);
  },

  async getProjectPreview(id: string, options?: RequestInit): Promise<BuildResult> {
    return request<BuildResult>(`/api/projects/${id}/preview`, options);
  },

  getEventsUrl(id: string): string {
    return `${BASE_URL}/api/projects/${id}/events`;
  },
};
