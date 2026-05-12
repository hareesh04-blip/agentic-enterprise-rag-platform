import { chunkTypeBadgeClasses, semanticCategoryLabel, semanticChunkCategory } from "../../lib/chunkTypeMeta";

interface ChunkTypeBadgeProps {
  chunkType?: string | null;
  /** Show compact machine chunk_type alongside friendly category */
  showRaw?: boolean;
  className?: string;
}

export function ChunkTypeBadge({ chunkType, showRaw = true, className = "" }: ChunkTypeBadgeProps) {
  const raw = chunkType?.trim() || "unknown_chunk_type";
  const category = semanticChunkCategory(chunkType);
  const label = semanticCategoryLabel(category);
  const styles = chunkTypeBadgeClasses(chunkType);

  return (
    <span
      title={raw}
      className={`inline-flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${styles} ${className}`}
    >
      <span className="truncate">{label}</span>
      {showRaw ? <span className="font-normal opacity-80">({raw})</span> : null}
    </span>
  );
}
