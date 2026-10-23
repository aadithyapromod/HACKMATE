import { EventType, AgentEvent } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type EventHandler = (event: AgentEvent) => void;

export class ProjectEventStream {
  private eventSource: EventSource | null = null;
  private listeners: Map<string, Set<EventHandler>> = new Map();
  private isExplicitlyClosed = false;

  constructor(public readonly projectId: string) {}

  public get readyState(): number {
    return this.eventSource?.readyState ?? (typeof EventSource !== "undefined" ? EventSource.CLOSED : 2);
  }

  public get isConnected(): boolean {
    return typeof EventSource !== "undefined" && this.eventSource?.readyState === EventSource.OPEN;
  }

  public connect(onOpen?: () => void, onError?: (err: Event) => void): void {
    if (this.eventSource) {
      return;
    }

    this.isExplicitlyClosed = false;
    const url = `${BASE_URL}/api/projects/${this.projectId}/events`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      if (this.isExplicitlyClosed) return;
      if (onOpen) onOpen();
    };

    this.eventSource.onerror = (err) => {
      if (this.isExplicitlyClosed) return;
      if (onError) onError(err);
    };

    const eventTypes: EventType[] = [
      "project.status",
      "task.updated",
      "agent.status",
      "build.log",
      "build.completed",
      "preview.ready",
      "project.completed",
      "project.failed",
    ];

    eventTypes.forEach((type) => {
      this.eventSource?.addEventListener(type, (event: MessageEvent) => {
        if (this.isExplicitlyClosed) return;
        try {
          const parsed = JSON.parse(event.data);
          const agentEvent: AgentEvent = {
            event_type: type,
            project_id: this.projectId,
            timestamp: parsed.timestamp || new Date().toISOString(),
            data: parsed,
          };
          this.notify(type, agentEvent);
          this.notify("*", agentEvent);
        } catch (e) {
          console.error(`[SSE] Failed to parse payload for event ${type}:`, e);
        }
      });
    });

    // Default message handler for unframed SSE messages
    this.eventSource.onmessage = (event: MessageEvent) => {
      if (this.isExplicitlyClosed) return;
      try {
        const parsed = JSON.parse(event.data);
        const eventType: EventType = parsed.event_type || "project.status";
        const agentEvent: AgentEvent = {
          event_type: eventType,
          project_id: this.projectId,
          timestamp: parsed.timestamp || new Date().toISOString(),
          data: parsed,
        };
        this.notify(eventType, agentEvent);
        this.notify("*", agentEvent);
      } catch {
        // Ping or heartbeats ignore
      }
    };
  }

  public on(eventType: EventType | "*", handler: EventHandler): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)?.add(handler);

    return () => {
      this.listeners.get(eventType)?.delete(handler);
    };
  }

  private notify(eventType: string, event: AgentEvent): void {
    const handlers = this.listeners.get(eventType);
    if (handlers) {
      handlers.forEach((handler) => handler(event));
    }
  }

  public close(): void {
    this.isExplicitlyClosed = true;
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.listeners.clear();
  }
}
