import type { QuerySourceItem } from "../types/query";

/** Read a diagnostics field, including nested `vector_retrieval_diagnostics` if present. */
export function readDiag(d: Record<string, unknown> | undefined, key: string): unknown {
  if (!d) return undefined;
  if (Object.prototype.hasOwnProperty.call(d, key)) return d[key];
  const nested = d.vector_retrieval_diagnostics;
  if (nested && typeof nested === "object" && nested !== null && key in (nested as Record<string, unknown>)) {
    return (nested as Record<string, unknown>)[key];
  }
  return undefined;
}

export function diagString(d: Record<string, unknown> | undefined, key: string): string | undefined {
  const v = readDiag(d, key);
  if (v === null || v === undefined) return undefined;
  return String(v);
}

export function diagNumber(d: Record<string, unknown> | undefined, key: string): number | undefined {
  const v = readDiag(d, key);
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v))) return Number(v);
  return undefined;
}

export function diagBool(d: Record<string, unknown> | undefined, key: string): boolean | undefined {
  const v = readDiag(d, key);
  if (typeof v === "boolean") return v;
  return undefined;
}

export function diagStringArray(d: Record<string, unknown> | undefined, key: string): string[] {
  const v = readDiag(d, key);
  if (!Array.isArray(v)) return [];
  return v.map((x) => String(x)).filter((s) => s.length > 0);
}

/** Short explainability lines for answer provenance (demo / transparency). */
export function answerProvenanceHints(
  sources: QuerySourceItem[] | null | undefined,
  diagnostics: Record<string, unknown> | undefined,
): string[] {
  const hints: string[] = [];
  const recovered = diagnostics?.response_fields_recovered_from_generic === true;

  const types = (sources ?? []).map((s) => String(s.chunk_type || "").toLowerCase());
  const anySemantic = types.some((t) => t.includes("semantic_summary"));
  const anyFlattened = types.some((t) => t.includes("table_flattened") || t.includes("flattened"));
  const anyGeneric = types.some((t) => t.includes("generic_section"));

  if (anySemantic) {
    hints.push("Answer derived from semantic API summary");
  }
  if (anyFlattened) {
    hints.push("Structured detail includes flattened response table context");
  }
  if (recovered && anyGeneric) {
    hints.push("Recovered from generic section when structured response chunks were insufficient");
  }

  return hints;
}
