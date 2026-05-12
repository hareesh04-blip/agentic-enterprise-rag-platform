/** Maps backend chunk_type strings to badge styling and human-readable semantic categories. */

export type SemanticChunkCategory =
  | "semantic_summary"
  | "structured_table"
  | "authentication"
  | "request_params"
  | "response_params"
  | "errors"
  | "generic"
  | "other";

const CATEGORY_LABEL: Record<SemanticChunkCategory, string> = {
  semantic_summary: "Semantic API summary",
  structured_table: "Flattened / structured table",
  authentication: "Authentication",
  request_params: "Request parameters",
  response_params: "Response parameters",
  errors: "Errors / failures",
  generic: "Generic section",
  other: "Chunk",
};

export function semanticChunkCategory(chunkType: string | null | undefined): SemanticChunkCategory {
  const t = String(chunkType || "").toLowerCase();
  if (t.includes("semantic_summary")) return "semantic_summary";
  if (t.includes("table_flattened") || t.includes("flattened")) return "structured_table";
  if (t.includes("authentication")) return "authentication";
  if (t.includes("request_parameters") || t.includes("header_parameter")) return "request_params";
  if (t.includes("response_parameters") || t.includes("success_response")) return "response_params";
  if (t.includes("failed_response") || t.includes("error")) return "errors";
  if (t.includes("generic_section")) return "generic";
  return "other";
}

export function semanticCategoryLabel(category: SemanticChunkCategory): string {
  return CATEGORY_LABEL[category] ?? CATEGORY_LABEL.other;
}

/** Tailwind classes for chunk-type badges (border + soft background + text). */
export function chunkTypeBadgeClasses(chunkType: string | null | undefined): string {
  const cat = semanticChunkCategory(chunkType);
  switch (cat) {
    case "semantic_summary":
      return "border-violet-200 bg-violet-50 text-violet-800";
    case "structured_table":
      return "border-cyan-200 bg-cyan-50 text-cyan-900";
    case "authentication":
      return "border-amber-200 bg-amber-50 text-amber-900";
    case "request_params":
      return "border-blue-200 bg-blue-50 text-blue-800";
    case "response_params":
      return "border-emerald-200 bg-emerald-50 text-emerald-900";
    case "errors":
      return "border-rose-200 bg-rose-50 text-rose-800";
    case "generic":
      return "border-slate-300 bg-slate-100 text-slate-800";
    default:
      return "border-indigo-200 bg-indigo-50 text-indigo-800";
  }
}
