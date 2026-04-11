import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Search, RefreshCw } from "lucide-react";

export default function Header() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = q.trim();
    if (trimmed.length >= 2) {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  return (
    <header className="flex items-center justify-between border-b border-neutral-800 bg-neutral-900/40 px-6 py-3 backdrop-blur">
      <form onSubmit={onSubmit} className="flex items-center gap-3 flex-1 max-w-lg">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="논문, 모델, 저장소 검색... (Enter)"
            className="w-full rounded-lg border border-neutral-800 bg-neutral-900 py-2 pl-10 pr-4 text-sm text-neutral-100 placeholder:text-neutral-500 focus:border-brand-500 focus:outline-none"
          />
        </div>
      </form>

      <div className="flex items-center gap-3">
        <button
          type="button"
          className="flex items-center gap-2 rounded-lg border border-neutral-800 px-3 py-1.5 text-xs text-neutral-400 hover:bg-neutral-800"
          title="Phase 7에서 활성화"
          disabled
        >
          <RefreshCw className="h-3.5 w-3.5" />
          수동 크롤
        </button>
      </div>
    </header>
  );
}
