import type { Item } from "../types";

const styles: Record<Item["source"], string> = {
  arxiv: "bg-red-500/10 text-red-400 border-red-500/30",
  github: "bg-neutral-500/10 text-neutral-300 border-neutral-500/30",
  huggingface: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  reddit: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  x: "bg-sky-500/10 text-sky-400 border-sky-500/30",
};

const labels: Record<Item["source"], string> = {
  arxiv: "arXiv",
  github: "GitHub",
  huggingface: "HF",
  reddit: "Reddit",
  x: "X",
};

export default function SourceBadge({ source }: { source: Item["source"] }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${styles[source]}`}>
      {labels[source]}
    </span>
  );
}
