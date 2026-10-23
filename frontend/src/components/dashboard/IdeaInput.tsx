"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface IdeaInputProps {
  onSubmit: (idea: string) => Promise<void>;
  isLoading: boolean;
}

export const IdeaInput: React.FC<IdeaInputProps> = ({ onSubmit, isLoading }) => {
  const [idea, setIdea] = useState("");
  const trimmedLength = idea.trim().length;
  const isValid = trimmedLength >= 10 && trimmedLength <= 2000;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isLoading) return;
    await onSubmit(idea);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="relative rounded-xl border border-gray-800 bg-[#111827]/80 p-1 focus-within:border-primary/80 focus-within:ring-1 focus-within:ring-primary/40 transition-all">
        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="Describe your hackathon concept (e.g., 'Build a real-time collaborative code review tool for students with live syntax highlighting and AI test generation')..."
          rows={3}
          maxLength={2000}
          className="w-full bg-transparent px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none resize-none"
          disabled={isLoading}
        />
        <div className="flex items-center justify-between border-t border-gray-800/80 px-3 py-2">
          <div className="text-xs text-gray-400">
            <span
              className={
                trimmedLength > 0 && !isValid ? "text-amber-400 font-semibold" : ""
              }
            >
              {trimmedLength}
            </span>
            <span className="text-gray-600"> / 2000 characters</span>
            {trimmedLength > 0 && trimmedLength < 10 && (
              <span className="ml-2 text-amber-400">(Min 10 characters required)</span>
            )}
          </div>
          <Button
            type="submit"
            disabled={!isValid || isLoading}
            isLoading={isLoading}
            size="sm"
            className="gap-2"
          >
            <Sparkles size={15} />
            <span>Start Building</span>
            <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    </form>
  );
};
