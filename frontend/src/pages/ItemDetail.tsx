import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ExternalLink, Star } from "lucide-react";
import { fetchItem } from "../api/items";
import SourceBadge from "../components/SourceBadge";
import PriorityBadge from "../components/PriorityBadge";

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: item } = useQuery({
    queryKey: ["item", id],
    queryFn: () => fetchItem(Number(id)),
    enabled: !!id,
  });

  if (!item) return <div className="text-neutral-500">Loading...</div>;
  const score = item.llm_score || item.keyword_score;

  return (
    <div className="max-w-4xl space-y-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-100"
      >
        <ChevronLeft className="h-3.5 w-3.5" /> 대시보드
      </Link>

      <article className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
        <div className="flex items-center gap-2 mb-3">
          <SourceBadge source={item.source} />
          <PriorityBadge priority={item.priority} />
          {score > 0 && (
            <span className="inline-flex items-center gap-1 text-sm text-amber-400">
              <Star className="h-4 w-4 fill-current" />
              {score}/10
            </span>
          )}
        </div>

        <h1 className="text-xl font-bold mb-3">{item.title}</h1>

        {item.authors && <p className="text-sm text-neutral-400 mb-4">{item.authors}</p>}

        {item.abstract && (
          <div className="text-sm text-neutral-300 leading-relaxed mb-6 whitespace-pre-wrap">
            {item.abstract}
          </div>
        )}

        {item.llm_reason && (
          <div className="rounded-lg border border-brand-500/30 bg-brand-500/5 p-4 mb-4">
            <div className="text-[10px] font-semibold text-brand-400 uppercase mb-1">
              AI 분석
            </div>
            <p className="text-sm text-neutral-200">{item.llm_reason}</p>
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-neutral-800">
          <div className="text-xs text-neutral-500">
            발견: {new Date(item.discovered_at).toLocaleString("ko-KR")}
            {item.published_at && (
              <> · 게시: {new Date(item.published_at).toLocaleDateString("ko-KR")}</>
            )}
          </div>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-500"
          >
            원문 보기 <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </article>

      {item.category_slugs.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold text-neutral-500 uppercase mb-2">
            카테고리
          </div>
          <div className="flex flex-wrap gap-2">
            {item.category_slugs.map((slug) => (
              <Link
                key={slug}
                to={`/category/${slug}`}
                className="rounded-md border border-neutral-700 bg-neutral-800 px-2 py-1 text-xs text-neutral-300 hover:border-brand-500/50"
              >
                {slug}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Phase 2: 댓글 영역 예정 */}
      <div className="rounded-xl border border-dashed border-neutral-800 p-6 text-center">
        <p className="text-sm text-neutral-500">💬 댓글 기능 (Phase 2 예정)</p>
      </div>
    </div>
  );
}
