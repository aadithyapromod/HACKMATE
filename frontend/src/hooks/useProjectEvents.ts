"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { ProjectEventStream } from "@/lib/events";
import { AgentEvent } from "@/lib/types";

export interface UseProjectEventsOptions {
  onEvent?: (event: AgentEvent) => void;
  onStatusChange?: (status: string) => void;
  onTaskUpdated?: (event: AgentEvent) => void;
  onBuildLog?: (event: AgentEvent) => void;
  onBuildCompleted?: (event: AgentEvent) => void;
  onPreviewReady?: (event: AgentEvent) => void;
  onProjectCompleted?: (event: AgentEvent) => void;
  onProjectFailed?: (event: AgentEvent) => void;
}

export function useProjectEvents(
  projectId: string | null,
  options?: UseProjectEventsOptions
) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [latestStatus, setLatestStatus] = useState<string | null>(null);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  useEffect(() => {
    if (!projectId) {
      setIsConnected(false);
      setConnectionError(false);
      setEvents([]);
      setLatestStatus(null);
      return;
    }

    setConnectionError(false);
    const stream = new ProjectEventStream(projectId);

    stream.connect(
      () => {
        setIsConnected(true);
        setConnectionError(false);
      },
      () => {
        setIsConnected(false);
        setConnectionError(true);
      }
    );

    const unsubscribe = stream.on("*", (event) => {
      // Discard event if stream belongs to an older project
      if (event.project_id !== projectId) {
        return;
      }

      setEvents((prev) => [event, ...prev].slice(0, 100));

      const opts = optionsRef.current;
      if (opts?.onEvent) {
        opts.onEvent(event);
      }

      switch (event.event_type) {
        case "project.status": {
          const status = event.data?.status ? String(event.data.status) : null;
          if (status) {
            setLatestStatus(status);
            opts?.onStatusChange?.(status);
          }
          break;
        }
        case "task.updated":
          opts?.onTaskUpdated?.(event);
          break;
        case "build.log":
          opts?.onBuildLog?.(event);
          break;
        case "build.completed":
          opts?.onBuildCompleted?.(event);
          break;
        case "preview.ready":
          opts?.onPreviewReady?.(event);
          break;
        case "project.completed": {
          setLatestStatus("completed");
          opts?.onProjectCompleted?.(event);
          break;
        }
        case "project.failed": {
          setLatestStatus("failed");
          opts?.onProjectFailed?.(event);
          break;
        }
      }
    });

    return () => {
      unsubscribe();
      stream.close();
      setIsConnected(false);
      setConnectionError(false);
    };
  }, [projectId]);

  return { events, isConnected, connectionError, latestStatus, clearEvents };
}
