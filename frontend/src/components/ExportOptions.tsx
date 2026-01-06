import { motion } from "framer-motion";
import { Copy, FileDown, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { api } from "@/api";

const NotionIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 2.028c-.42-.327-.981-.56-2.055-.467l-12.75.839c-.466.046-.559.28-.373.42zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.047.934-.559.934-1.166V6.354c0-.606-.233-.933-.746-.886l-15.177.887c-.56.047-.748.327-.748.933zm14.337.653c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.746 0-.933-.234-1.494-.933l-4.577-7.186v6.952l1.449.327s0 .84-1.168.84l-3.22.186c-.093-.186 0-.653.327-.746l.84-.233V9.854l-1.168-.093c-.093-.42.14-1.026.793-1.073l3.453-.233 4.763 7.28v-6.44l-1.215-.14c-.093-.513.28-.886.746-.932zm-13.589-2.8l15.318-.887c1.542-.14 1.963-.047 2.944.7l4.04 2.847c.653.467.794.607.794 1.12v14.37c0 1.026-.373 1.635-1.68 1.728l-15.505.933c-.98.047-1.448-.093-1.962-.746l-3.172-4.107c-.56-.746-.793-1.26-.793-1.866V6.175c0-.793.373-1.494 1.635-1.635z" />
  </svg>
);

const JiraIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005zm5.723-5.756H5.736a5.215 5.215 0 0 0 5.215 5.214h2.129v2.058a5.218 5.218 0 0 0 5.215 5.214V6.758a1.001 1.001 0 0 0-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 0 0 5.215 5.215h2.129v2.057A5.215 5.215 0 0 0 24 12.483V1.005A1.005 1.005 0 0 0 23.013 0z" />
  </svg>
);

interface ExportOptionsProps {
  sessionId?: string;
  documentation?: string;
}

interface ExportOption {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
}

export const ExportOptions = ({ sessionId, documentation }: ExportOptionsProps) => {
  const handleCopy = async () => {
    if (documentation) {
      await navigator.clipboard.writeText(documentation);
      toast.success("Documentation copied to clipboard");
    } else {
      toast.error("No documentation to copy");
    }
  };

  const handleDownload = () => {
    if (documentation) {
      const blob = new Blob([documentation], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `documentation-${sessionId || "doc"}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Documentation downloaded as Markdown");
    } else {
      toast.error("No documentation to download");
    }
  };

  const handleNotion = async () => {
    if (!sessionId) {
      toast.error("No session selected");
      return;
    }
    try {
      const response = await api.exportSession(sessionId, "notion");
      toast.success(response.data.message || "Sent to Notion!");
    } catch (err: any) {
      toast.error(err.message || "Failed to send to Notion");
    }
  };

  const handleJira = async () => {
    if (!sessionId) {
      toast.error("No session selected");
      return;
    }
    try {
      const response = await api.exportSession(sessionId, "jira");
      toast.success(response.data.message || "Jira ticket created!");
    } catch (err: any) {
      toast.error(err.message || "Failed to create Jira ticket");
    }
  };

  const options: ExportOption[] = [
    {
      id: "copy",
      label: "Copy to Clipboard",
      description: "Copy as Markdown",
      icon: Copy,
      action: handleCopy,
    },
    {
      id: "download",
      label: "Download",
      description: "Save as .md file",
      icon: FileDown,
      action: handleDownload,
    },
    {
      id: "notion",
      label: "Send to Notion",
      description: "Create a new page",
      icon: NotionIcon,
      action: handleNotion,
    },
    {
      id: "jira",
      label: "Create Jira Ticket",
      description: "Export as issue",
      icon: JiraIcon,
      action: handleJira,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="space-y-4"
    >
      <h3 className="text-lg font-semibold text-foreground">Export Options</h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {options.map((option, index) => (
          <motion.button
            key={option.id}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 + index * 0.05 }}
            onClick={option.action}
            className="group p-4 rounded-xl border border-border bg-card hover:border-primary/30 hover:bg-card/80 transition-all text-left"
          >
            <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center mb-3 group-hover:bg-primary/10 transition-colors">
              <option.icon className="text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <p className="font-medium text-foreground text-sm group-hover:text-primary transition-colors">
              {option.label}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {option.description}
            </p>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
};
