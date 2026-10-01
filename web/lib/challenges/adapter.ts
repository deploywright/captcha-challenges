import type { ChallengeCatalogEntry, ClientChallenge } from "./types";

/**
 * Validates and converts a catalog entry or raw public challenge into a sanitized ClientChallenge.
 * Ensures zero private metadata escapes to the client components.
 */
export function toClientChallenge(
  raw: ChallengeCatalogEntry | Record<string, unknown>
): ClientChallenge {
  if (!raw.id || typeof raw.id !== "string") {
    throw new Error("Challenge is missing valid 'id'");
  }
  if (!raw.variant || typeof raw.variant !== "string") {
    throw new Error(`Challenge ${raw.id} is missing valid 'variant'`);
  }
  if (!raw.instruction || typeof raw.instruction !== "string") {
    throw new Error(`Challenge ${raw.id} is missing valid 'instruction'`);
  }

  const rawUi = (raw.ui as Record<string, unknown>) || {};
  const rows = typeof rawUi.rows === "number" ? rawUi.rows : undefined;
  const columns = typeof rawUi.columns === "number" ? rawUi.columns : undefined;
  const selectionMode =
    rawUi.selectionMode === "single" || rawUi.selectionMode === "multiple"
      ? rawUi.selectionMode
      : "multiple";
  const options = Array.isArray(rawUi.options)
    ? rawUi.options.map(String)
    : undefined;

  const rawAssets = Array.isArray(raw.assets) ? raw.assets.map(String) : [];

  return {
    id: raw.id,
    level: Number(raw.level) || 1,
    levelKey: String(raw.levelKey || ""),
    variant: raw.variant as ClientChallenge["variant"],
    subtype: typeof raw.subtype === "string" ? (raw.subtype as ClientChallenge["subtype"]) : undefined,
    difficulty: typeof raw.difficulty === "string" ? (raw.difficulty as ClientChallenge["difficulty"]) : undefined,
    displayName: String(raw.displayName || raw.variant),
    levelLabel: String(raw.levelLabel || `Level ${raw.level}`),
    type: raw.type === "single-choice" ? "single-choice" : "image-selection",
    instruction: raw.instruction,
    seed: "seed" in raw && typeof raw.seed === "number" ? raw.seed : 0,
    assets: rawAssets,
    ui: {
      rows,
      columns,
      selectionMode,
      options,
    },
    resolution: typeof raw.resolution === "number" ? raw.resolution : undefined,
    seriesId: typeof raw.seriesId === "string" ? raw.seriesId : undefined,
  };
}
