export type FeedPlayerFitMode = "contain" | "cover";
export type FeedPlayerLoadMode = "active" | "nearby" | "distant";
export type FeedPlayerVideoShape =
  | "portrait"
  | "square"
  | "landscape"
  | "ultra-wide"
  | "ultra-tall"
  | "unknown";
export type FeedPlayerStageLayout = "portrait" | "balanced" | "landscape" | "cinematic";
export type FeedPlayerOverlayLayout = "portrait" | "balanced" | "landscape" | "cinematic";
export type FeedPlayerBackdropMode = "soft" | "immersive";

export interface FeedPlayerPresentation {
  fitMode: FeedPlayerFitMode;
  shape: FeedPlayerVideoShape;
  stageLayout: FeedPlayerStageLayout;
  overlayLayout: FeedPlayerOverlayLayout;
  backdropMode: FeedPlayerBackdropMode;
}

const FALLBACK_PRESENTATION: FeedPlayerPresentation = {
  fitMode: "contain",
  shape: "unknown",
  stageLayout: "balanced",
  overlayLayout: "balanced",
  backdropMode: "immersive",
};

function isKnownAspectRatio(value: number | null): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

export function resolveFeedVideoShape(
  aspectRatio: number | null,
): FeedPlayerVideoShape {
  if (!isKnownAspectRatio(aspectRatio)) {
    return "unknown";
  }

  if (aspectRatio <= 0.52) {
    return "ultra-tall";
  }

  if (aspectRatio <= 0.88) {
    return "portrait";
  }

  if (aspectRatio <= 1.18) {
    return "square";
  }

  if (aspectRatio <= 1.9) {
    return "landscape";
  }

  return "ultra-wide";
}

export function resolveFeedFitMode(
  sourceAspectRatio: number | null,
  stageAspectRatio: number | null,
): FeedPlayerFitMode {
  if (!isKnownAspectRatio(sourceAspectRatio) || !isKnownAspectRatio(stageAspectRatio)) {
    return FALLBACK_PRESENTATION.fitMode;
  }

  if (sourceAspectRatio >= 1) {
    return "contain";
  }

  const cropRatio =
    sourceAspectRatio > stageAspectRatio
      ? 1 - stageAspectRatio / sourceAspectRatio
      : 1 - sourceAspectRatio / stageAspectRatio;

  if (sourceAspectRatio <= 0.9 && cropRatio <= 0.15) {
    return "cover";
  }

  return "contain";
}

export function resolveFeedPresentation(
  sourceAspectRatio: number | null,
  stageAspectRatio: number | null,
): FeedPlayerPresentation {
  const shape = resolveFeedVideoShape(sourceAspectRatio);
  const fitMode = resolveFeedFitMode(sourceAspectRatio, stageAspectRatio);

  switch (shape) {
    case "ultra-tall":
      return {
        fitMode,
        shape,
        stageLayout: "portrait",
        overlayLayout: "portrait",
        backdropMode: fitMode === "cover" ? "soft" : "immersive",
      };
    case "portrait":
      return {
        fitMode,
        shape,
        stageLayout: "portrait",
        overlayLayout: fitMode === "cover" ? "portrait" : "balanced",
        backdropMode: fitMode === "cover" ? "soft" : "immersive",
      };
    case "square":
      return {
        fitMode,
        shape,
        stageLayout: "balanced",
        overlayLayout: "balanced",
        backdropMode: "immersive",
      };
    case "landscape":
      return {
        fitMode: "contain",
        shape,
        stageLayout: "landscape",
        overlayLayout: "landscape",
        backdropMode: "immersive",
      };
    case "ultra-wide":
      return {
        fitMode: "contain",
        shape,
        stageLayout: "cinematic",
        overlayLayout: "cinematic",
        backdropMode: "immersive",
      };
    default:
      return FALLBACK_PRESENTATION;
  }
}
