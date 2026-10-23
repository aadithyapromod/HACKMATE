import React from "react";
import { MonitorPlay, ExternalLink, ShieldCheck, ShieldAlert } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { isValidPreviewUrl } from "@/lib/utils";

interface AppPreviewProps {
  previewUrl: string | null;
  isMock?: boolean;
}

export const AppPreview: React.FC<AppPreviewProps> = ({
  previewUrl,
  isMock = false,
}) => {
  const isSafe = isValidPreviewUrl(previewUrl);

  return (
    <Card
      title="Application Live Preview"
      icon={<MonitorPlay className="h-4 w-4" />}
      action={
        <div className="flex items-center gap-2">
          {isMock && (
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
              Mock Preview
            </span>
          )}
          {previewUrl && isSafe && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary-light hover:underline flex items-center gap-1 font-mono"
            >
              <span>Open Tab</span>
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      }
    >
      {previewUrl ? (
        isSafe ? (
          <div className="rounded-lg border border-gray-800 overflow-hidden bg-black aspect-video">
            <iframe
              src={previewUrl}
              title="Application Preview"
              className="w-full h-full border-0"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
        ) : (
          <div className="rounded-lg border border-rose-900/60 bg-rose-950/30 p-6 text-center space-y-2">
            <ShieldAlert className="h-8 w-8 text-rose-400 mx-auto" />
            <h4 className="text-sm font-semibold text-rose-200">
              Untrusted Preview URL Blocked
            </h4>
            <p className="text-xs text-rose-300 font-mono">
              The preview URL did not pass safe HTTP/HTTPS validation.
            </p>
          </div>
        )
      ) : (
        <div className="rounded-lg border border-dashed border-gray-800 bg-[#0d131f]/50 p-8 text-center flex flex-col items-center justify-center space-y-3">
          <div className="h-10 w-10 rounded-full bg-purple-950/60 border border-purple-800/50 flex items-center justify-center text-purple-400">
            <MonitorPlay size={20} />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-200">
              Preview Server Standby
            </h4>
            <p className="text-xs text-gray-400 max-w-sm mt-1">
              Once the AI generates the React + Vite code and the Docker runner executes the build, the sandboxed preview will mount here automatically.
            </p>
          </div>
          <div className="inline-flex items-center gap-1.5 text-[11px] text-gray-400 bg-gray-900/60 px-2.5 py-1 rounded-full border border-gray-800">
            <ShieldCheck size={13} className="text-emerald-400" />
            <span>Sandboxed execution: host system protected</span>
          </div>
        </div>
      )}
    </Card>
  );
};
