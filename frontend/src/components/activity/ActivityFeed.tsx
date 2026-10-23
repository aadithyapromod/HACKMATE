import React from "react";
import { AgentEvent } from "@/lib/types";
import { formatTimestamp } from "@/lib/utils";
import { Activity, Bot, Cpu, GitCommit } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface ActivityFeedProps {
  events: AgentEvent[];
  isMock?: boolean;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  events,
  isMock = false,
}) => {
  const getEventIcon = (eventType: AgentEvent["event_type"]) => {
    switch (eventType) {
      case "agent.status":
        return <Bot className="h-3.5 w-3.5 text-purple-400" />;
      case "build.log":
      case "build.completed":
        return <Cpu className="h-3.5 w-3.5 text-amber-400" />;
      case "task.updated":
        return <GitCommit className="h-3.5 w-3.5 text-blue-400" />;
      default:
        return <Activity className="h-3.5 w-3.5 text-emerald-400" />;
    }
  };

  const getEventMessage = (event: AgentEvent) => {
    const data = event.data;
    if (data.message) return String(data.message);
    if (data.status) return `Status changed to: ${data.status}`;
    if (data.logs) return String(data.logs).slice(0, 80);
    return JSON.stringify(data);
  };

  return (
    <Card
      title="Agent Activity Feed"
      icon={<Activity className="h-4 w-4" />}
      action={
        isMock ? (
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
            Mock Stream
          </span>
        ) : null
      }
    >
      {events.length === 0 ? (
        <div className="py-6 text-center text-xs text-gray-500">
          No agent activity streamed yet.
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1 font-mono">
          {events.map((evt, idx) => (
            <div
              key={`${evt.timestamp}-${idx}`}
              className="flex items-start gap-2.5 text-xs border-b border-gray-800/40 pb-2"
            >
              <div className="mt-0.5 shrink-0">{getEventIcon(evt.event_type)}</div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between text-[10px] text-gray-400">
                  <span className="text-purple-300 font-semibold">{evt.event_type}</span>
                  <span>{formatTimestamp(evt.timestamp)}</span>
                </div>
                <p className="text-gray-300 text-[11px] mt-0.5 break-words">
                  {getEventMessage(evt)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};
