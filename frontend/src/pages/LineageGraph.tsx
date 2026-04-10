import { GitBranch } from "lucide-react";

export default function LineageGraph() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">기술 계보</h1>
        <p className="text-sm text-neutral-500 mt-1">
          논문/모델 간의 참조 관계와 기술 흐름을 그래프로 봅니다.
        </p>
      </div>

      <div className="rounded-xl border border-dashed border-neutral-800 bg-neutral-900/50 p-12 text-center">
        <GitBranch className="h-12 w-12 text-neutral-700 mx-auto mb-3" />
        <p className="text-sm text-neutral-400 mb-1">기술 계보 그래프</p>
        <p className="text-xs text-neutral-600">
          Phase 5에서 구현 예정 · Semantic Scholar + LLM 관계 판단 + reactflow
        </p>
      </div>
    </div>
  );
}
