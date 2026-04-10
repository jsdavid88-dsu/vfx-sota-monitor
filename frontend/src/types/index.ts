export type Category = {
  id: number;
  slug: string;
  name_ko: string;
  name_en: string;
  description: string | null;
  icon: string | null;
  keywords: string[];
  github_topics: string[];
  hf_tags: string[];
  subreddits: string[];
  x_accounts: string[];
  current_sota: string[];
  display_order: number;
  item_count: number;
  new_this_week: number;
};

export type Item = {
  id: number;
  source: "arxiv" | "github" | "huggingface" | "reddit" | "x";
  external_id: string;
  url: string;
  title: string;
  abstract: string | null;
  authors: string | null;
  published_at: string | null;
  discovered_at: string;
  metadata: Record<string, unknown>;
  keyword_score: number;
  llm_score: number;
  llm_reason: string | null;
  priority: "P0" | "P1" | "P2" | "P3" | "WATCH" | null;
  status: string;
  category_slugs: string[];
};

export type DashboardSummary = {
  total_items: number;
  new_this_week: number;
  p0_count: number;
  p1_count: number;
  categories_with_updates: number;
  last_crawl: string | null;
};
