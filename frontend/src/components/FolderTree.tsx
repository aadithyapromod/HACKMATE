"use client";

import React, { useState, useMemo } from "react";
import { Folder, FolderOpen, FileCode, FileText, ChevronRight, ChevronDown } from "lucide-react";
import { FileMetadata } from "@/lib/api";

interface FolderTreeProps {
  files: FileMetadata[];
  selectedPath: string;
  onSelectFile: (path: string) => void;
}

interface TreeNode {
  name: string;
  fullPath: string;
  isFolder: boolean;
  children: { [name: string]: TreeNode };
  file?: FileMetadata;
}

export default function FolderTree({ files, selectedPath, onSelectFile }: FolderTreeProps) {
  const [collapsed, setCollapsed] = useState<{ [path: string]: boolean }>({});

  const toggleFolder = (path: string) => {
    setCollapsed(prev => ({ ...prev, [path]: !prev[path] }));
  };

  const tree = useMemo(() => {
    const root: TreeNode = { name: "root", fullPath: "", isFolder: true, children: {} };

    files.forEach(file => {
      const parts = file.file_path.split("/");
      let current = root;

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isLast = i === parts.length - 1;
        const currentPath = parts.slice(0, i + 1).join("/");

        if (!current.children[part]) {
          current.children[part] = {
            name: part,
            fullPath: currentPath,
            isFolder: !isLast,
            children: {},
            file: isLast ? file : undefined,
          };
        }
        current = current.children[part];
      }
    });

    return root;
  }, [files]);

  const getFileBadgeColor = (filename: string) => {
    if (filename.endsWith(".tsx") || filename.endsWith(".jsx")) return "text-blue-400";
    if (filename.endsWith(".ts") || filename.endsWith(".js")) return "text-cyan-400";
    if (filename.endsWith(".css")) return "text-purple-400";
    if (filename.endsWith(".json")) return "text-amber-400";
    if (filename.endsWith(".html")) return "text-orange-400";
    return "text-slate-400";
  };

  const renderNode = (node: TreeNode, depth: number = 0) => {
    const isFolder = node.isFolder;
    const isExpanded = !collapsed[node.fullPath];
    const isSelected = selectedPath === node.fullPath;

    return (
      <div key={node.fullPath || "root"}>
        {node.name !== "root" && (
          <div
            onClick={() => {
              if (isFolder) {
                toggleFolder(node.fullPath);
              } else {
                onSelectFile(node.fullPath);
              }
            }}
            style={{ paddingLeft: `${depth * 14 + 10}px` }}
            className={`flex items-center py-1.5 px-2 text-xs font-mono cursor-pointer select-none transition-colors rounded-sm ${
              isSelected
                ? "bg-blue-600/30 text-blue-200 border-l-2 border-blue-500 font-medium"
                : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
            }`}
          >
            {isFolder ? (
              <>
                <span className="mr-1.5 text-slate-400">
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
                <span className="mr-1.5 text-amber-300">
                  {isExpanded ? <FolderOpen size={14} /> : <Folder size={14} />}
                </span>
                <span className="truncate">{node.name}</span>
              </>
            ) : (
              <>
                <span className={`mr-2 ml-4 ${getFileBadgeColor(node.name)}`}>
                  <FileCode size={14} />
                </span>
                <span className="truncate">{node.name}</span>
                {node.file && (
                  <span className="ml-auto text-[10px] text-slate-500 font-sans">
                    {node.file.file_size_bytes < 1024
                      ? `${node.file.file_size_bytes}B`
                      : `${(node.file.file_size_bytes / 1024).toFixed(1)}KB`}
                  </span>
                )}
              </>
            )}
          </div>
        )}

        {isFolder && isExpanded && (
          <div>
            {Object.values(node.children)
              .sort((a, b) => {
                if (a.isFolder === b.isFolder) return a.name.localeCompare(b.name);
                return a.isFolder ? -1 : 1;
              })
              .map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-full h-full overflow-y-auto select-none bg-slate-900/60 border-r border-slate-800/80">
      <div className="px-3 py-2 border-b border-slate-800/80 flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider">
        <span>Project Explorer</span>
        <span className="bg-slate-800 px-1.5 py-0.5 rounded text-[10px] text-slate-300">
          {files.length} files
        </span>
      </div>
      <div className="py-2">
        {files.length === 0 ? (
          <div className="p-4 text-xs text-slate-500 italic text-center">
            Files will appear as they are generated...
          </div>
        ) : (
          renderNode(tree, 0)
        )}
      </div>
    </div>
  );
}
