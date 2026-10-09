import { Badge } from "@/components/ui/badge";

type Status = "queued" | "generating" | "done" | "failed";

export default function StatusIndicator({ status }: { status: Status }) {
  const config: Record<Status, { label: string; variant: "default" | "success" | "error" | "pending" }> = {
    queued: { label: "Queued", variant: "default" },
    generating: { label: "Generating...", variant: "pending" },
    done: { label: "Done", variant: "success" },
    failed: { label: "Failed", variant: "error" },
  };
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
