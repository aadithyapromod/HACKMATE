import React from "react";
import { Task } from "@/lib/types";
import { CheckCircle2, Clock, Loader2, XCircle, ListTodo } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface TaskListProps {
  tasks: Task[];
  isMock?: boolean;
}

export const TaskList: React.FC<TaskListProps> = ({ tasks, isMock = false }) => {
  const getStatusIcon = (status: Task["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />;
      case "running":
        return <Loader2 className="h-4 w-4 text-purple-400 animate-spin shrink-0" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-rose-400 shrink-0" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500 shrink-0" />;
    }
  };

  return (
    <Card
      title="Pipeline Tasks"
      icon={<ListTodo className="h-4 w-4" />}
      action={
        isMock ? (
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
            Mock Preview
          </span>
        ) : null
      }
    >
      {tasks.length === 0 ? (
        <div className="py-6 text-center text-xs text-gray-500">
          No tasks registered yet. Submit an idea above to start the pipeline.
        </div>
      ) : (
        <div className="space-y-2.5">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="flex items-start gap-3 rounded-lg border border-gray-800/80 bg-gray-900/40 p-2.5 hover:border-gray-700/80 transition-colors"
            >
              <div className="mt-0.5">{getStatusIcon(task.status)}</div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-gray-200 truncate">
                    {task.title}
                  </h4>
                  <span className="text-[10px] uppercase font-mono text-gray-400">
                    {task.status}
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 mt-0.5 line-clamp-2">
                  {task.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};
