import { Link } from "react-router-dom";
import { ExternalLink, Star } from "lucide-react";
import type { Item } from "../types";
import SourceBadge from "./SourceBadge";
import PriorityBadge from "./PriorityBadge";

export default function ItemCard({ item }: { item: Item }) {
  const score = item.llm_score || item.keyword_score;
  return (
    <Link
      to={`/item/${item.id}`}
      className="block rounded-lg border border-neutral-800 bg-neutral-900 p-4 hover:border-brand-500/50 transition"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceBadge source={item.source} />
          <PriorityBadge priority={item.priority} />
          {score > 0 && (
            <span className="inline-flex items-center gap-1 text-xs text-amber-400">
              <Star className="h-3 w-3 fill-current" />
              {score}
            </span>
          )}
        </div>
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-neutral-500 hover:text-neutral-300"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>

      <h3 className="text-sm font-semibold text-neutral-100 mb-1 line-clamp-2">{item.title}</h3>
      {item.abstract && (
        <p className="text-xs text-neutral-400 line-clamp-2 mb-2">{item.abstract}</p>
      )}
      <div className="flex items-center gap-2 text-[10px] text-neutral-500">
        <span>{new Date(item.discovered_at).toLocaleDateString("ko-KR")}</span>
        {item.category_slugs.length > 0 && <span>· {item.category_slugs.join(", ")}</span>}
      </div>
    </Link>
  );
}
