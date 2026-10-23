import React from "react";
import { ProjectStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ProjectStatusBadgeProps {
  status: ProjectStatus;
  className?: string;
}

export const ProjectStatusBadge: React.FC<ProjectStatusBadgeProps> = ({
  status,
  className,
}) => {
  const statusConfig: Record<
    ProjectStatus,
    { label: string; bg: string; text: string; dot: string; pulse?: boolean }
  > = {
    created: {
      label: "Created",
      bg: "bg-slate-900 border-slate-700",
      text: "text-slate-300",
      dot: "bg-slate-400",
    },
    planning: {
      label: "Planning",
      bg: "bg-blue-950/60 border-blue-800/60",
      text: "text-blue-300",
      dot: "bg-blue-400",
      pulse: true,
    },
    generating: {
      label: "Generating Code",
      bg: "bg-purple-950/60 border-purple-800/60",
      text: "text-purple-300",
      dot: "bg-purple-400",
      pulse: true,
    },
    building: {
      label: "Sandbox Building",
      bg: "bg-amber-950/60 border-amber-800/60",
      text: "text-amber-300",
      dot: "bg-amber-400",
      pulse: true,
    },
    testing: {
      label: "Testing",
      bg: "bg-cyan-950/60 border-cyan-800/60",
      text: "text-cyan-300",
      dot: "bg-cyan-400",
      pulse: true,
    },
    repairing: {
      label: "Self-Healing",
      bg: "bg-orange-950/60 border-orange-800/60",
      text: "text-orange-300",
      dot: "bg-orange-400",
      pulse: true,
    },
    completed: {
      label: "Completed",
      bg: "bg-emerald-950/60 border-emerald-800/60",
      text: "text-emerald-300",
      dot: "bg-emerald-400",
    },
    failed: {
      label: "Failed",
      bg: "bg-rose-950/60 border-rose-800/60",
      text: "text-rose-300",
      dot: "bg-rose-400",
    },
  };

  const config = statusConfig[status] || statusConfig.created;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
        config.bg,
        config.text,
        className
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          config.dot,
          config.pulse && "animate-ping"
        )}
      />
      {config.label}
    </span>
  );
};
