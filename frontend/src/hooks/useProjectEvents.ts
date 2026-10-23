"use client";

import { useEffect, useState } from "react";
import { ProjectEventStream } from "@/lib/events";
import { AgentEvent } from "@/lib/types";

export function useProjectEvents(projectId: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [latestStatus, setLatestStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setIsConnected(false);
      setEvents([]);
      return;
    }

    const stream = new ProjectEventStream(projectId);

    stream.connect(
      () => setIsConnected(true),
      () => setIsConnected(false)
    );

    const unsubscribeAll = stream.on("*", (event) => {
      setEvents((prev) => [event, ...prev].slice(0, 50));
      if (event.event_type === "project.status" && event.data.status) {
        setLatestStatus(String(event.data.status));
      }
    });

    return () => {
      unsubscribeAll();
      stream.close();
      setIsConnected(false);
    };
  }, [projectId]);

  return { events, isConnected, latestStatus };
}
