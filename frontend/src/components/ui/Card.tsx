import React from "react";
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  title,
  icon,
  action,
  children,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        "rounded-xl border border-gray-800 bg-[#111827]/70 backdrop-blur-sm p-4 sm:p-5 shadow-lg",
        className
      )}
      {...props}
    >
      {(title || icon || action) && (
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-gray-800/80">
          <div className="flex items-center gap-2">
            {icon && <span className="text-primary-light">{icon}</span>}
            {title && <h3 className="text-sm font-semibold text-gray-200">{title}</h3>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};
