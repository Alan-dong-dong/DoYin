import assert from "node:assert/strict";

import {
  resolveFeedPresentation,
  resolveFeedVideoShape,
} from "../src/lib/feedPresentation.ts";

type PresentationExpectation = {
  name: string;
  sourceAspectRatio: number;
  stageAspectRatio: number;
  expected: ReturnType<typeof resolveFeedPresentation>;
};

const cases: PresentationExpectation[] = [
  {
    name: "portrait video stays portrait-led and can cover when crop is modest",
    sourceAspectRatio: 9 / 16,
    stageAspectRatio: 0.58,
    expected: {
      fitMode: "cover",
      shape: "portrait",
      stageLayout: "portrait",
      overlayLayout: "portrait",
      backdropMode: "soft",
    },
  },
  {
    name: "square video keeps a balanced stage and immersive backdrop",
    sourceAspectRatio: 1,
    stageAspectRatio: 0.76,
    expected: {
      fitMode: "contain",
      shape: "square",
      stageLayout: "balanced",
      overlayLayout: "balanced",
      backdropMode: "immersive",
    },
  },
  {
    name: "landscape video never switches to cover and gets a wider stage",
    sourceAspectRatio: 16 / 9,
    stageAspectRatio: 1.06,
    expected: {
      fitMode: "contain",
      shape: "landscape",
      stageLayout: "landscape",
      overlayLayout: "landscape",
      backdropMode: "immersive",
    },
  },
  {
    name: "ultra-wide video gets a cinematic layout with immersive backdrop",
    sourceAspectRatio: 2.39,
    stageAspectRatio: 1.22,
    expected: {
      fitMode: "contain",
      shape: "ultra-wide",
      stageLayout: "cinematic",
      overlayLayout: "cinematic",
      backdropMode: "immersive",
    },
  },
  {
    name: "ultra-tall video still preserves portrait stage semantics",
    sourceAspectRatio: 0.5,
    stageAspectRatio: 0.58,
    expected: {
      fitMode: "cover",
      shape: "ultra-tall",
      stageLayout: "portrait",
      overlayLayout: "portrait",
      backdropMode: "soft",
    },
  },
];

for (const testCase of cases) {
  const result = resolveFeedPresentation(testCase.sourceAspectRatio, testCase.stageAspectRatio);

  assert.deepStrictEqual(
    result,
    testCase.expected,
    `${testCase.name}: expected ${JSON.stringify(testCase.expected)}, got ${JSON.stringify(result)}`,
  );

  assert.notStrictEqual(
    resolveFeedVideoShape(testCase.sourceAspectRatio),
    "unknown",
    `${testCase.name}: source ratio should resolve to a known bucket`,
  );

  assert.ok(
    result.fitMode === "contain" || result.fitMode === "cover",
    `${testCase.name}: fit mode must preserve aspect ratio rather than stretch`,
  );
}

console.log("Feed presentation verification passed for portrait, square, landscape, ultra-wide, and ultra-tall cases.");
