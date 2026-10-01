import fs from "node:fs";
import path from "node:path";

interface PublicUiConfig {
  rows?: number;
  columns?: number;
  selectionMode?: "single" | "multiple";
  options?: string[];
}

interface PublicChallenge {
  schemaVersion: number;
  id: string;
  level: number;
  variant: string;
  subtype?: string;
  type: string;
  instruction: string;
  seed: number;
  assets: string[];
  ui: PublicUiConfig;
}

interface RawAnswer {
  challengeId: string;
  levelKey: string;
  datasetSource?: string;
  correctSelection?: number[];
  answer?: string;
  source_image_id?: string;
  subtype?: string;
  routing?: unknown;
  transformation?: {
    resolution?: number;
    type?: string;
  };
  degradation?: {
    downsampleWidth?: number;
  };
}

export interface CatalogEntry {
  id: string;
  level: number;
  levelKey: string;
  variant: string;
  subtype?: string;
  displayName: string;
  levelLabel: string;
  type: string;
  instruction: string;
  ui: PublicUiConfig;
  assetCount: number;
  assets: string[];
  challengeUrl: string;
  resolution?: number;
  seriesId?: string;
}

export interface PrivateAnswerRecord {
  challengeId: string;
  levelKey: string;
  variant: string;
  subtype?: string;
  type: string;
  correctSelection?: number[];
  answer?: string;
}

const FORBIDDEN_PUBLIC_KEYS = new Set([
  "answer",
  "correctanswer",
  "correctselection",
  "ispositive",
  "groundtruth",
  "connections",
  "sourcetodestination",
  "annotations",
  "classes",
  "bbox",
  "boundingboxes",
  "difficulty",
  "targetclass",
  "routing",
  "finaltarget",
  "rayspath",
  "raysegments",
  "mirrorhits",
  "solutionpath",
  "switchstates",
  "openvalves",
  "closedvalves",
]);

const FORBIDDEN_FILENAME_TERMS = [
  "positive",
  "negative",
  "correct",
  "wrong",
  "groundtruth",
  "target",
];

function getLevelLabel(variant: string): string {
  switch (variant) {
    case "street-grid":
      return "Level 1";
    case "hard-street-grid":
      return "Level 2A";
    case "checker-shadow":
      return "Level 2B";
    case "tangled-cables":
    case "routing-puzzle":
      return "Level 3A";
    case "degraded-vision":
      return "Level 3B";
    default:
      return "Unknown Level";
  }
}

function getDisplayName(variant: string): string {
  switch (variant) {
    case "street-grid":
      return "Normal Street CAPTCHA";
    case "hard-street-grid":
      return "Hard Street CAPTCHA";
    case "checker-shadow":
      return "Visual Illusion";
    case "tangled-cables":
      return "Tangled Cables";
    case "routing-puzzle":
      return "Routing Puzzles";
    case "degraded-vision":
      return "Degraded Vision";
    default:
      return variant;
  }
}

function findGeneratedDir(): string | null {
  const candidates = [
    path.resolve(process.cwd(), "../challenges/generated"),
    path.resolve(process.cwd(), "../Challenges/generated"),
    path.resolve(__dirname, "../../challenges/generated"),
    path.resolve(__dirname, "../../Challenges/generated"),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
      return candidate;
    }
  }
  return null;
}

function auditObjectForLeaks(obj: unknown, pathTrail = ""): void {
  if (!obj || typeof obj !== "object") return;

  if (Array.isArray(obj)) {
    obj.forEach((item, index) => auditObjectForLeaks(item, `${pathTrail}[${index}]`));
    return;
  }

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase();
    if (FORBIDDEN_PUBLIC_KEYS.has(lowerKey)) {
      throw new Error(`[LEAK DETECTED] Forbidden key "${key}" found in public challenge data at ${pathTrail}`);
    }
    auditObjectForLeaks(value, pathTrail ? `${pathTrail}.${key}` : key);
  }
}

function auditAssetFilenames(assets: string[], challengeId: string): void {
  for (const assetPath of assets) {
    const filename = path.basename(assetPath).toLowerCase();
    for (const term of FORBIDDEN_FILENAME_TERMS) {
      if (filename.includes(term)) {
        throw new Error(
          `[LEAK DETECTED] Asset filename "${assetPath}" in challenge "${challengeId}" contains forbidden term "${term}"`
        );
      }
    }
  }
}

function copyDirectoryRecursive(src: string, dest: string): void {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDirectoryRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

export function syncChallenges(): { totalSynced: number; catalogCount: number } {
  console.log("=================================================");
  console.log("  BUILD-TIME CHALLENGE SYNCHRONIZATION PIPELINE  ");
  console.log("=================================================");

  const generatedDir = findGeneratedDir();
  if (!generatedDir) {
    console.error("No generated challenges found.\nRun the Challenge Engine first.");
    process.exit(1);
  }

  console.log(`Source directory: ${generatedDir}`);

  const publicDestDir = path.resolve(process.cwd(), "public/challenges");
  const privateDestDir = path.resolve(process.cwd(), "src/generated-private");

  // 1. Clean ONLY Web-generated output directories from previous sync
  if (fs.existsSync(publicDestDir)) {
    console.log(`Cleaning previous public challenges at ${publicDestDir}...`);
    fs.rmSync(publicDestDir, { recursive: true, force: true });
  }
  if (fs.existsSync(privateDestDir)) {
    console.log(`Cleaning previous private registry at ${privateDestDir}...`);
    fs.rmSync(privateDestDir, { recursive: true, force: true });
  }

  fs.mkdirSync(publicDestDir, { recursive: true });
  fs.mkdirSync(privateDestDir, { recursive: true });

  const catalog: CatalogEntry[] = [];
  const privateRegistry: Record<string, PrivateAnswerRecord> = {};

  // For Level 3B anonymous series tracking (so series navigation works without leaking real image IDs)
  const imageSourceToSeriesMap = new Map<string, string>();
  let nextSeriesId = 1;

  // Level folders in generatedDir
  const levelDirs = fs
    .readdirSync(generatedDir, { withFileTypes: true })
    .filter((d) => d.isDirectory() && d.name.startsWith("level-"))
    .map((d) => d.name)
    .sort();

  let totalSynced = 0;

  for (const levelDirName of levelDirs) {
    const levelPath = path.join(generatedDir, levelDirName);
    const challengeFolders = fs
      .readdirSync(levelPath, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .sort();

    console.log(`Syncing ${levelDirName}: ${challengeFolders.length} challenges...`);

    for (const folderName of challengeFolders) {
      const challengeFolder = path.join(levelPath, folderName);
      const challengeJsonPath = path.join(challengeFolder, "challenge.json");
      const answerJsonPath = path.join(challengeFolder, "answer.json");
      const assetsDir = path.join(challengeFolder, "assets");

      if (!fs.existsSync(challengeJsonPath) || !fs.existsSync(answerJsonPath)) {
        throw new Error(`Malformed challenge directory: ${challengeFolder} missing challenge.json or answer.json`);
      }

      const challengeRaw = fs.readFileSync(challengeJsonPath, "utf-8");
      const answerRaw = fs.readFileSync(answerJsonPath, "utf-8");

      const challenge = JSON.parse(challengeRaw) as PublicChallenge;
      const answer = JSON.parse(answerRaw) as RawAnswer;

      // AUDIT 1: Ensure public challenge.json does not leak answers or ground-truth
      auditObjectForLeaks(challenge);

      // AUDIT 2: Ensure asset filenames do not encode answer status
      auditAssetFilenames(challenge.assets, challenge.id);

      // Copy public data: <publicDestDir>/<id>/challenge.json and <publicDestDir>/<id>/assets/
      const targetChallengeDir = path.join(publicDestDir, challenge.id);
      fs.mkdirSync(targetChallengeDir, { recursive: true });

      // Rewrite asset URLs in the copied challenge.json to be absolute web paths: /challenges/<id>/assets/<name>
      const webAssets = challenge.assets.map((assetRel) => {
        const cleanRel = assetRel.startsWith("/") ? assetRel.slice(1) : assetRel;
        return `/challenges/${challenge.id}/${cleanRel}`;
      });

      const publicChallengeData: PublicChallenge = {
        ...challenge,
        assets: webAssets,
      };

      fs.writeFileSync(
        path.join(targetChallengeDir, "challenge.json"),
        JSON.stringify(publicChallengeData, null, 2),
        "utf-8"
      );

      if (fs.existsSync(assetsDir)) {
        const targetAssetsDir = path.join(targetChallengeDir, "assets");
        copyDirectoryRecursive(assetsDir, targetAssetsDir);
      }

      // Handle anonymous series mapping for Level 3B
      let seriesId: string | undefined = undefined;
      const resolution =
        answer.transformation?.resolution ?? answer.degradation?.downsampleWidth;

      if (challenge.variant === "degraded-vision" && answer.source_image_id) {
        if (!imageSourceToSeriesMap.has(answer.source_image_id)) {
          imageSourceToSeriesMap.set(
            answer.source_image_id,
            `series-${String(nextSeriesId++).padStart(2, "0")}`
          );
        }
        seriesId = imageSourceToSeriesMap.get(answer.source_image_id);
      }

      // Catalog entry (SAFE for participant)
      const catalogEntry: CatalogEntry = {
        id: challenge.id,
        level: challenge.level,
        levelKey: answer.levelKey,
        variant: challenge.variant,
        subtype: challenge.subtype || answer.subtype,
        displayName: getDisplayName(challenge.variant),
        levelLabel: getLevelLabel(challenge.variant),
        type: challenge.type,
        instruction: challenge.instruction,
        ui: challenge.ui,
        assetCount: challenge.assets.length,
        assets: webAssets,
        challengeUrl: `/challenges/${challenge.id}/challenge.json`,
        resolution,
        seriesId,
      };
      catalog.push(catalogEntry);

      // Private Answer Registry (SERVER-ONLY)
      privateRegistry[challenge.id] = {
        challengeId: challenge.id,
        levelKey: answer.levelKey,
        variant: challenge.variant,
        subtype: challenge.subtype || answer.subtype,
        type: challenge.type,
        correctSelection: answer.correctSelection,
        answer: answer.answer,
      };

      totalSynced++;
    }
  }

  // AUDIT 3: Final verification that answer.json NEVER exists in public/
  const checkAnswerLeakInDir = (dir: string) => {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        checkAnswerLeakInDir(fullPath);
      } else if (entry.name.toLowerCase() === "answer.json") {
        throw new Error(`CRITICAL SECURITY FAILURE: answer.json leaked into public directory at ${fullPath}`);
      }
    }
  };
  checkAnswerLeakInDir(publicDestDir);

  // Write public catalog
  fs.writeFileSync(
    path.join(publicDestDir, "catalog.json"),
    JSON.stringify(catalog, null, 2),
    "utf-8"
  );
  console.log(`Public catalog written to ${path.join(publicDestDir, "catalog.json")} (${catalog.length} challenges)`);

  // Write private answers JSON
  fs.writeFileSync(
    path.join(privateDestDir, "answers.json"),
    JSON.stringify(privateRegistry, null, 2),
    "utf-8"
  );

  // Write private answers TypeScript server module
  const tsContent = `// SERVER-ONLY FILE. DO NOT IMPORT INTO CLIENT COMPONENTS.
import type { PrivateAnswerRecord } from "../../scripts/sync-challenges";

export const ANSWERS_REGISTRY: Record<string, PrivateAnswerRecord> = ${JSON.stringify(
    privateRegistry,
    null,
    2
  )} as const;

export function getPrivateAnswer(challengeId: string): PrivateAnswerRecord | undefined {
  return ANSWERS_REGISTRY[challengeId];
}
`;
  fs.writeFileSync(path.join(privateDestDir, "answers.ts"), tsContent, "utf-8");
  console.log(`Private answers registry written to ${path.join(privateDestDir, "answers.ts")}`);

  console.log("-------------------------------------------------");
  console.log(`Sync completed successfully. Total challenges: ${totalSynced}`);
  console.log("Answer-leak check: PASSED (Zero leakage).");
  console.log("=================================================");

  return { totalSynced, catalogCount: catalog.length };
}

// When executed directly via tsx/node
if (require.main === module || process.argv[1]?.endsWith("sync-challenges.ts")) {
  try {
    syncChallenges();
  } catch (err) {
    console.error("Sync failed:", err);
    process.exit(1);
  }
}
