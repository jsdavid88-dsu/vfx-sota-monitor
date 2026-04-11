import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sparkles, TrendingUp, AlertCircle, Clock } from "lucide-react";
import { fetchCategories } from "../api/categories";
import { fetchSummary } from "../api/stats";
import { fetchItems, type ItemFilters } from "../api/items";
import CategoryGrid from "../components/CategoryGrid";
import ItemCard from "../components/ItemCard";
import FilterPanel from "../components/FilterPanel";

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-4">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg p-2 ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="text-xs text-neutral-500">{label}</div>
          <div className="text-xl font-bold text-neutral-100">{value}</div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [filters, setFilters] = useState<ItemFilters>({ sort: "discovered" });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
  });
  const { data: summary } = useQuery({ queryKey: ["summary"], queryFn: fetchSummary });
  const { data: p0Items = [] } = useQuery({
    queryKey: ["items", { priority: "P0" }],
    queryFn: () => fetchItems({ priority: "P0", limit: 5 }),
  });
  const { data: filteredItems = [] } = useQuery({
    queryKey: ["items", "filtered", filters],
    queryFn: () => fetchItems({ ...filters, limit: 12 }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">대시보드</h1>
        <p className="text-sm text-neutral-500 mt-1">
          VFX 관련 AI SOTA 실시간 추적 · 마지막 업데이트:{" "}
          {summary?.last_crawl ? new Date(summary.last_crawl).toLocaleString("ko-KR") : "—"}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={TrendingUp}
          label="전체 추적"
          value={summary?.total_items ?? "—"}
          accent="bg-brand-500/20 text-brand-400"
        />
        <StatCard
          icon={Sparkles}
          label="이번 주 신규"
          value={summary?.new_this_week ?? "—"}
          accent="bg-emerald-500/20 text-emerald-400"
        />
        <StatCard
          icon={AlertCircle}
          label="P0 긴급"
          value={summary?.p0_count ?? "—"}
          accent="bg-red-500/20 text-red-400"
        />
        <StatCard
          icon={Clock}
          label="P1 중요"
          value={summary?.p1_count ?? "—"}
          accent="bg-amber-500/20 text-amber-400"
        />
      </div>

      {p0Items.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            긴급 (P0)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {p0Items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm font-semibold text-neutral-300 mb-3">카테고리 (10)</h2>
        <CategoryGrid categories={categories} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-neutral-300">최근 발견</h2>
        </div>
        <div className="mb-3">
          <FilterPanel
            filters={filters}
            onChange={setFilters}
            showCategory
            categories={categories.map((c) => ({ slug: c.slug, name_ko: c.name_ko }))}
          />
        </div>
        {filteredItems.length === 0 ? (
          <div className="rounded-xl border border-dashed border-neutral-800 p-8 text-center text-sm text-neutral-500">
            조건에 맞는 아이템이 없습니다
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filteredItems.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>

      {categories.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-800 bg-neutral-900/50 p-12 text-center">
          <p className="text-neutral-500 mb-2">카테고리 데이터가 없습니다</p>
          <p className="text-xs text-neutral-600">
            <code className="rounded bg-neutral-800 px-2 py-1">python seed.py</code> 실행
          </p>
        </div>
      )}
    </div>
  );
}
