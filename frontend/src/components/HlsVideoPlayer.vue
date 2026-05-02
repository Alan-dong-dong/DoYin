<template>
  <div
    ref="playerRoot"
    class="feed-player"
    :data-state="playerState"
    :data-load-mode="loadMode"
    :data-controls-visible="String(controlsVisible)"
    :data-fit-mode="resolvedFitMode"
    :data-video-shape="videoShape"
    :data-stage-layout="stageLayout"
    :data-overlay-layout="overlayLayout"
    :data-backdrop-mode="backdropMode"
    @mouseenter="handlePlayerMouseEnter"
    @mouseleave="handlePlayerMouseLeave"
  >
    <div class="feed-player__backdrop-layer" aria-hidden="true">
      <div class="feed-player__backdrop feed-player__backdrop--image" :style="backdropStyle" />
      <div class="feed-player__backdrop feed-player__backdrop--ambient" />
      <div class="feed-player__backdrop feed-player__backdrop--mesh" />
    </div>

    <div class="feed-player__media-shell" @click="handleSurfaceToggle">
      <div class="feed-player__media-plane">
        <video
          ref="videoElement"
          class="feed-player__media"
          :poster="posterUrl ?? undefined"
          :preload="videoPreloadMode"
          :aria-label="title"
          :style="mediaStyle"
          playsinline
          @loadedmetadata="handleLoadedMetadata"
          @durationchange="handleDurationChange"
          @timeupdate="handleTimeUpdate"
          @playing="handlePlaying"
          @pause="handlePause"
          @loadeddata="handleLoadedData"
          @waiting="handleWaiting"
          @error="handleNativeError"
        />
      </div>
    </div>

    <div class="feed-player__shade" />

    <div
      v-if="isPreparingOverlayVisible"
      class="feed-player__overlay feed-player__overlay--loading"
    >
      <p class="feed-player__eyebrow">准备播放</p>
      <h3>正在加载当前视频</h3>
      <p>正在准备当前流媒体，同时保持刷流位置稳定。</p>
    </div>

    <div
      v-else-if="active && processingMessage"
      class="feed-player__overlay feed-player__overlay--processing"
      role="status"
    >
      <p class="feed-player__eyebrow">仍在处理</p>
      <h3>这段视频暂时还不能播放</h3>
      <p>{{ processingMessage }}</p>
      <div class="feed-player__action-row">
        <button class="feed-player__action" type="button" @click="retryPlayback">重试</button>
      </div>
    </div>

    <div
      v-else-if="active && playbackError"
      class="feed-player__overlay feed-player__overlay--error"
      role="alert"
    >
      <p class="feed-player__eyebrow">播放异常</p>
      <h3>无法播放这段视频</h3>
      <p>{{ playbackError }}</p>
      <div class="feed-player__action-row">
        <button class="feed-player__action" type="button" @click="retryPlayback">重试</button>
      </div>
    </div>

    <div
      v-else-if="active && requiresManualPlay"
      class="feed-player__overlay feed-player__overlay--manual"
    >
      <p class="feed-player__eyebrow">等待播放</p>
      <h3>需要你手动开始播放</h3>
      <p>点击播放即可继续观看，当前刷流位置不会改变。</p>
      <div class="feed-player__action-row">
        <button class="feed-player__action" type="button" @click="handleManualPlay">
          播放视频
        </button>
      </div>
    </div>

    <div v-if="active" class="feed-player__control-bar" @click.stop>
      <div class="feed-player__control-shell">
        <div
          class="feed-player__progress-shell"
          :class="{ 'feed-player__progress-shell--interactive': canSeek }"
          :aria-disabled="String(!canSeek)"
          @pointerdown.stop="handleSeekPointerDown"
          @pointermove.stop="handleSeekPointerMove"
          @pointerup.stop="handleSeekPointerUp"
          @pointercancel.stop="handleSeekPointerCancel"
        >
          <div class="feed-player__progress-rail" />
          <div class="feed-player__progress-fill" :style="progressFillStyle" />
          <div class="feed-player__progress-thumb" :style="progressThumbStyle" />
        </div>

        <div class="feed-player__transport-row">
          <button
            class="feed-player__transport-button feed-player__transport-button--primary"
            type="button"
            :disabled="!canTogglePlayback"
            :aria-label="playbackToggleLabel"
            @click.stop="handleTransportToggle"
          >
            <svg
              v-if="showsPauseIcon"
              viewBox="0 0 24 24"
              aria-hidden="true"
              class="feed-player__transport-icon"
            >
              <rect x="6.5" y="5.5" width="4" height="13" rx="1.2" />
              <rect x="13.5" y="5.5" width="4" height="13" rx="1.2" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              aria-hidden="true"
              class="feed-player__transport-icon"
            >
              <path d="M8 6.4a1 1 0 0 1 1.54-.84l7.82 5.6a1 1 0 0 1 0 1.62l-7.82 5.6A1 1 0 0 1 8 17.54z" />
            </svg>
          </button>

          <div class="feed-player__time-group" aria-live="off">
            <span>{{ elapsedTimeLabel }}</span>
            <span class="feed-player__time-separator">/</span>
            <span>{{ durationTimeLabel }}</span>
          </div>

          <div class="feed-player__volume-group">
            <button
              class="feed-player__transport-button feed-player__transport-button--ghost"
              type="button"
              :aria-label="volumeButtonLabel"
              :aria-pressed="String(props.muted)"
              @click.stop="handleMuteToggle"
            >
              <svg
                v-if="volumeIcon === 'muted'"
                viewBox="0 0 24 24"
                aria-hidden="true"
                class="feed-player__transport-icon"
              >
                <path
                  d="M5 9.5h3.2l4.1-3.6a.8.8 0 0 1 1.32.61v11a.8.8 0 0 1-1.32.61L8.2 14.5H5a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1Z"
                />
                <path d="M16.5 9.5 20 13" />
                <path d="m20 9.5-3.5 3.5" />
              </svg>
              <svg
                v-else-if="volumeIcon === 'low'"
                viewBox="0 0 24 24"
                aria-hidden="true"
                class="feed-player__transport-icon"
              >
                <path
                  d="M5 9.5h3.2l4.1-3.6a.8.8 0 0 1 1.32.61v11a.8.8 0 0 1-1.32.61L8.2 14.5H5a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1Z"
                />
                <path d="M17 9.4a4.1 4.1 0 0 1 0 5.2" />
              </svg>
              <svg
                v-else
                viewBox="0 0 24 24"
                aria-hidden="true"
                class="feed-player__transport-icon"
              >
                <path
                  d="M5 9.5h3.2l4.1-3.6a.8.8 0 0 1 1.32.61v11a.8.8 0 0 1-1.32.61L8.2 14.5H5a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1Z"
                />
                <path d="M16.6 8.4a5.8 5.8 0 0 1 0 7.2" />
                <path d="M18.9 6.5a8.6 8.6 0 0 1 0 11" />
              </svg>
            </button>

            <label class="feed-player__volume-slider">
              <span class="feed-player__sr-only">{{ volumeLabel }}</span>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                :value="volumePercent"
                :aria-label="volumeLabel"
                @click.stop
                @pointerdown.stop="handleVolumePointerDown"
                @pointerup.stop="handleVolumePointerUp"
                @pointercancel.stop="handleVolumePointerCancel"
                @input="handleVolumeInput"
              />
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type Hls from "hls.js";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import {
  resolveFeedPresentation,
  type FeedPlayerBackdropMode,
  type FeedPlayerFitMode,
  type FeedPlayerLoadMode,
  type FeedPlayerOverlayLayout,
  type FeedPlayerPresentation,
  type FeedPlayerStageLayout,
  type FeedPlayerVideoShape,
} from "@/lib/feedPresentation";

const props = withDefaults(
  defineProps<{
    manifestUrl: string;
    posterUrl?: string | null;
    title: string;
    active: boolean;
    muted?: boolean;
    volume?: number;
    loadMode?: FeedPlayerLoadMode;
  }>(),
  {
    posterUrl: null,
    muted: true,
    volume: 0.6,
    loadMode: "distant",
  },
);

const emit = defineEmits<{
  (event: "playing"): void;
  (event: "error", message: string): void;
  (event: "audio-change", payload: { volume: number; muted: boolean }): void;
  (event: "presentation-change", payload: FeedPlayerPresentation): void;
}>();

const playerRoot = ref<HTMLElement | null>(null);
const videoElement = ref<HTMLVideoElement | null>(null);
const playbackError = ref<string | null>(null);
const processingMessage = ref<string | null>(null);
const requiresManualPlay = ref(false);
const isPlaybackPaused = ref(false);
const isPreparing = ref(false);
const isWaitingForData = ref(false);
const hasLoadedMedia = ref(false);
const videoAspectRatio = ref<number | null>(null);
const stageAspectRatio = ref<number | null>(null);
const currentTimeSeconds = ref(0);
const durationSeconds = ref(0);
const isScrubbing = ref(false);
const scrubTimeSeconds = ref<number | null>(null);
const activeScrubPointerId = ref<number | null>(null);
const isPointerInsidePlayer = ref(false);
const activeVolumePointerId = ref<number | null>(null);

let hls: Hls | null = null;
let currentLoadToken = 0;
let attachedManifestUrl: string | null = null;
let resizeObserver: ResizeObserver | null = null;

const videoPreloadMode = computed<"none" | "metadata" | "auto">(() => {
  if (props.loadMode === "distant") {
    return "none";
  }

  return props.loadMode === "nearby" ? "metadata" : "auto";
});

const isPreparingOverlayVisible = computed(() => {
  return (
    props.active &&
    props.loadMode !== "distant" &&
    !playbackError.value &&
    !processingMessage.value &&
    !requiresManualPlay.value &&
    (isPreparing.value || isWaitingForData.value || !hasLoadedMedia.value)
  );
});

const videoShape = computed<FeedPlayerVideoShape>(() => {
  return resolvedPresentation.value.shape;
});

const resolvedPresentation = computed<FeedPlayerPresentation>(() =>
  resolveFeedPresentation(videoAspectRatio.value, stageAspectRatio.value),
);
const resolvedFitMode = computed<FeedPlayerFitMode>(() => resolvedPresentation.value.fitMode);
const stageLayout = computed<FeedPlayerStageLayout>(() => resolvedPresentation.value.stageLayout);
const overlayLayout = computed<FeedPlayerOverlayLayout>(() => resolvedPresentation.value.overlayLayout);
const backdropMode = computed<FeedPlayerBackdropMode>(() => resolvedPresentation.value.backdropMode);

const mediaStyle = computed(() => ({
  objectFit: resolvedFitMode.value,
}));

const backdropStyle = computed(() => {
  if (!props.posterUrl) {
    return undefined;
  }

  return {
    backgroundImage: `url("${props.posterUrl}")`,
  };
});

const playerState = computed(() => {
  if (props.loadMode === "distant") {
    return "distant";
  }

  if (playbackError.value) {
    return "error";
  }

  if (processingMessage.value) {
    return "processing";
  }

  if (requiresManualPlay.value) {
    return "manual";
  }

  if (isPreparingOverlayVisible.value) {
    return "loading";
  }

  if (props.active && isPlaybackPaused.value) {
    return "paused";
  }

  if (props.loadMode === "nearby") {
    return "nearby";
  }

  return props.active ? "active" : "idle";
});

const volumePercent = computed(() => Math.round(props.volume * 100));

const volumeLabel = computed(() => {
  if (props.muted || props.volume === 0) {
    return "音量 0%";
  }

  return `音量 ${volumePercent.value}%`;
});

const canTogglePlayback = computed(() => {
  return (
    props.active &&
    props.loadMode !== "distant" &&
    !processingMessage.value &&
    !playbackError.value
  );
});

const canSeek = computed(() => {
  return (
    canTogglePlayback.value &&
    !isPreparingOverlayVisible.value &&
    !requiresManualPlay.value &&
    durationSeconds.value > 0
  );
});

const effectiveCurrentTime = computed(() => {
  if (isScrubbing.value && scrubTimeSeconds.value !== null) {
    return scrubTimeSeconds.value;
  }

  return currentTimeSeconds.value;
});

const progressRatio = computed(() => {
  if (durationSeconds.value <= 0) {
    return 0;
  }

  return Math.min(Math.max(effectiveCurrentTime.value / durationSeconds.value, 0), 1);
});

const progressPercent = computed(() => progressRatio.value * 100);

const progressFillStyle = computed(() => ({
  transform: `scaleX(${progressRatio.value})`,
}));

const progressThumbStyle = computed(() => ({
  left: `${progressPercent.value}%`,
}));

const elapsedTimeLabel = computed(() => formatPlaybackTime(effectiveCurrentTime.value));

const durationTimeLabel = computed(() => {
  if (durationSeconds.value <= 0) {
    return "--:--";
  }

  return formatPlaybackTime(durationSeconds.value);
});

const showsPauseIcon = computed(() => {
  return (
    canTogglePlayback.value &&
    !isPreparingOverlayVisible.value &&
    !requiresManualPlay.value &&
    !isPlaybackPaused.value
  );
});

const playbackToggleLabel = computed(() => {
  return showsPauseIcon.value ? "暂停视频" : "播放视频";
});

const volumeIcon = computed<"muted" | "low" | "high">(() => {
  if (props.muted || props.volume === 0) {
    return "muted";
  }

  return props.volume < 0.5 ? "low" : "high";
});

const volumeButtonLabel = computed(() => {
  return props.muted || props.volume === 0 ? "取消静音" : "静音";
});

const controlsVisible = computed(() => {
  return (
    props.active &&
    (isPointerInsidePlayer.value || isScrubbing.value || activeVolumePointerId.value !== null)
  );
});

function emitPresentationChange() {
  emit("presentation-change", resolvedPresentation.value);
}

function formatPlaybackTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "0:00";
  }

  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainderSeconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainderSeconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(remainderSeconds).padStart(2, "0")}`;
}

function destroyHls() {
  if (hls) {
    hls.destroy();
    hls = null;
  }
}

function getVideoElement(): HTMLVideoElement | null {
  return videoElement.value;
}

function updateStageAspectRatio() {
  const player = playerRoot.value;
  if (!player) {
    stageAspectRatio.value = null;
    emitPresentationChange();
    return;
  }

  const { width, height } = player.getBoundingClientRect();
  if (width > 0 && height > 0) {
    stageAspectRatio.value = width / height;
  } else {
    stageAspectRatio.value = null;
  }

  emitPresentationChange();
}

function applyAudioPreferences(video: HTMLVideoElement) {
  video.muted = props.muted;
  video.volume = props.volume;
}

function syncControlVisibilityFromDom() {
  isPointerInsidePlayer.value = !!(props.active && playerRoot.value?.matches(":hover"));
}

function resetTimingState() {
  currentTimeSeconds.value = 0;
  durationSeconds.value = 0;
  isScrubbing.value = false;
  scrubTimeSeconds.value = null;
  activeScrubPointerId.value = null;
}

function clearPlaybackStates() {
  playbackError.value = null;
  processingMessage.value = null;
  requiresManualPlay.value = false;
  isPlaybackPaused.value = false;
  isWaitingForData.value = false;
}

function markProcessingState(
  message = "播放资源仍在生成或同步中，请稍后重试。",
) {
  processingMessage.value = message;
  playbackError.value = null;
  requiresManualPlay.value = false;
  isPreparing.value = false;
  isWaitingForData.value = false;
}

function detachSource() {
  currentLoadToken += 1;
  attachedManifestUrl = null;
  destroyHls();
  videoAspectRatio.value = null;
  resetTimingState();

  const video = getVideoElement();
  if (!video) {
    return;
  }

  video.pause();
  video.removeAttribute("src");
  video.load();
  hasLoadedMedia.value = false;
  isPreparing.value = false;
  isWaitingForData.value = false;
  isPlaybackPaused.value = false;
  emitPresentationChange();
}

async function attemptPlayback(trigger: "auto" | "user" = "auto") {
  const video = getVideoElement();
  if (
    !video ||
    !props.active ||
    props.loadMode === "distant" ||
    playbackError.value ||
    processingMessage.value
  ) {
    return;
  }

  applyAudioPreferences(video);
  isPreparing.value = trigger === "auto" || !hasLoadedMedia.value;

  try {
    await video.play();
    requiresManualPlay.value = false;
    isPlaybackPaused.value = false;
    isPreparing.value = false;
    isWaitingForData.value = false;
  } catch (error) {
    isPreparing.value = false;

    if (error instanceof Error && error.name === "NotAllowedError") {
      requiresManualPlay.value = true;
      return;
    }

    const message = "浏览器无法继续播放这段视频。";

    playbackError.value = message;
    emit("error", message);
  }
}

function pausePlayback() {
  const video = getVideoElement();
  if (!video) {
    return;
  }

  video.pause();
  isPreparing.value = false;
  isWaitingForData.value = false;
}

function handleSurfaceToggle() {
  const video = getVideoElement();
  if (!video || !props.active || playbackError.value || processingMessage.value) {
    return;
  }

  if (requiresManualPlay.value) {
    void handleManualPlay();
    return;
  }

  if (video.paused) {
    void attemptPlayback("user");
    return;
  }

  video.pause();
}

function handlePlayerMouseEnter() {
  if (!props.active) {
    return;
  }

  isPointerInsidePlayer.value = true;
}

function handlePlayerMouseLeave() {
  isPointerInsidePlayer.value = false;
}

function handleLoadedMetadata() {
  const video = getVideoElement();
  if (!video) {
    return;
  }

  if (video.videoWidth > 0 && video.videoHeight > 0) {
    videoAspectRatio.value = video.videoWidth / video.videoHeight;
    emitPresentationChange();
  }

  durationSeconds.value = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0;
  currentTimeSeconds.value = Number.isFinite(video.currentTime) ? video.currentTime : 0;
}

function handleDurationChange() {
  const video = getVideoElement();
  if (!video) {
    return;
  }

  durationSeconds.value = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0;
}

function handleTimeUpdate() {
  if (isScrubbing.value) {
    return;
  }

  const video = getVideoElement();
  if (!video) {
    return;
  }

  currentTimeSeconds.value = Number.isFinite(video.currentTime) ? video.currentTime : 0;
}

function classifyHlsError(details: string | undefined, responseCode?: number) {
  if (details === "manifestLoadError" || responseCode === 404 || responseCode === 403) {
    return {
      type: "processing" as const,
      message: "HLS 清单暂时不可用，视频可能仍在转码处理中。",
    };
  }

  if (details === "manifestParsingError") {
    return {
      type: "processing" as const,
      message: "这段视频的播放资源仍在准备中。",
    };
  }

  return {
    type: "error" as const,
    message:
      details === "bufferStalledError"
        ? "播放已卡住，暂时无法恢复。"
        : "HLS 播放器遇到无法恢复的错误。",
  };
}

function attachNativeSource(video: HTMLVideoElement) {
  video.src = props.manifestUrl;
  video.load();
}

function attachHlsSource(video: HTMLVideoElement, HlsConstructor: typeof Hls, loadToken: number) {
  destroyHls();

  const nextHls = new HlsConstructor();
  hls = nextHls;
  nextHls.loadSource(props.manifestUrl);
  nextHls.attachMedia(video);

  nextHls.on(HlsConstructor.Events.MANIFEST_PARSED, () => {
    if (loadToken !== currentLoadToken) {
      return;
    }

    hasLoadedMedia.value = true;
    isPreparing.value = false;
    isWaitingForData.value = false;

    if (props.active) {
      void attemptPlayback();
    }
  });

  nextHls.on(HlsConstructor.Events.ERROR, (_event, data) => {
    if (loadToken !== currentLoadToken || !data.fatal) {
      return;
    }

    const result = classifyHlsError(data.details, data.response?.code);
    if (result.type === "processing") {
      markProcessingState(result.message);
    } else {
      playbackError.value = result.message;
      processingMessage.value = null;
      requiresManualPlay.value = false;
      isPreparing.value = false;
      isWaitingForData.value = false;
      emit("error", result.message);
    }

    attachedManifestUrl = null;
    destroyHls();
  });
}

async function ensureMediaReady(forceReload = false) {
  const video = getVideoElement();
  if (!video) {
    return;
  }

  if (props.loadMode === "distant") {
    clearPlaybackStates();
    detachSource();
    return;
  }

  applyAudioPreferences(video);

  if (!forceReload && attachedManifestUrl === props.manifestUrl) {
    if (props.active) {
      void attemptPlayback();
    } else {
      pausePlayback();
    }

    return;
  }

  currentLoadToken += 1;
  const loadToken = currentLoadToken;
  attachedManifestUrl = props.manifestUrl;

  clearPlaybackStates();
  resetTimingState();
  hasLoadedMedia.value = false;
  isPreparing.value = true;

  destroyHls();
  video.pause();
  video.removeAttribute("src");
  video.load();

  if (video.canPlayType("application/vnd.apple.mpegurl")) {
    attachNativeSource(video);
    await nextTick();

    if (loadToken === currentLoadToken && props.active) {
      void attemptPlayback();
    }

    return;
  }

  const { default: HlsConstructor } = await import("hls.js");
  if (loadToken !== currentLoadToken) {
    return;
  }

  if (HlsConstructor.isSupported()) {
    attachHlsSource(video, HlsConstructor, loadToken);
  } else {
    const message = "当前浏览器无法播放刷流中的 HLS 视频。";
    playbackError.value = message;
    isPreparing.value = false;
    emit("error", message);
  }
}

function handleLoadedData() {
  handleLoadedMetadata();
  hasLoadedMedia.value = true;
  isPreparing.value = false;
  isWaitingForData.value = false;
}

function handleWaiting() {
  if (!props.active || requiresManualPlay.value || playbackError.value || processingMessage.value) {
    return;
  }

  isWaitingForData.value = true;
}

function handlePlaying() {
  requiresManualPlay.value = false;
  playbackError.value = null;
  processingMessage.value = null;
  isPlaybackPaused.value = false;
  isPreparing.value = false;
  isWaitingForData.value = false;
  hasLoadedMedia.value = true;

  const video = getVideoElement();
  if (video) {
    currentTimeSeconds.value = Number.isFinite(video.currentTime) ? video.currentTime : 0;
    durationSeconds.value = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 0;
  }

  emit("playing");
}

function handlePause() {
  if (!props.active || playbackError.value || processingMessage.value || requiresManualPlay.value) {
    return;
  }

  isPlaybackPaused.value = true;
  isPreparing.value = false;
  isWaitingForData.value = false;

  const video = getVideoElement();
  if (video) {
    currentTimeSeconds.value = Number.isFinite(video.currentTime) ? video.currentTime : 0;
  }
}

function handleNativeError() {
  if (playbackError.value || processingMessage.value) {
    return;
  }

  const video = getVideoElement();
  if (props.active && video && !hasLoadedMedia.value) {
    markProcessingState();
    return;
  }

  const message = "浏览器无法继续播放这段视频。";
  playbackError.value = message;
  requiresManualPlay.value = false;
  isPreparing.value = false;
  isWaitingForData.value = false;
  emit("error", message);
}

async function handleManualPlay() {
  requiresManualPlay.value = false;
  await attemptPlayback("user");
}

function handleTransportToggle() {
  if (!canTogglePlayback.value) {
    return;
  }

  if (requiresManualPlay.value || isPlaybackPaused.value) {
    void handleManualPlay();
    return;
  }

  pausePlayback();
}

function handleMuteToggle() {
  emit("audio-change", {
    muted: !props.muted,
    volume: props.volume,
  });
}

function resolveSeekTimeFromPointer(clientX: number, element: HTMLElement) {
  if (durationSeconds.value <= 0) {
    return 0;
  }

  const rect = element.getBoundingClientRect();
  if (rect.width <= 0) {
    return currentTimeSeconds.value;
  }

  const ratio = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
  return ratio * durationSeconds.value;
}

function commitSeek(timeInSeconds: number) {
  const video = getVideoElement();
  if (!video || durationSeconds.value <= 0) {
    return;
  }

  const nextTime = Math.min(Math.max(timeInSeconds, 0), durationSeconds.value);
  video.currentTime = nextTime;
  currentTimeSeconds.value = nextTime;
}

function clearScrubState() {
  isScrubbing.value = false;
  scrubTimeSeconds.value = null;
  activeScrubPointerId.value = null;
}

function handleSeekPointerDown(event: PointerEvent) {
  if (!canSeek.value) {
    return;
  }

  const element = event.currentTarget;
  if (!(element instanceof HTMLElement)) {
    return;
  }

  activeScrubPointerId.value = event.pointerId;
  isScrubbing.value = true;
  scrubTimeSeconds.value = resolveSeekTimeFromPointer(event.clientX, element);
  element.setPointerCapture?.(event.pointerId);
}

function handleSeekPointerMove(event: PointerEvent) {
  if (!isScrubbing.value || activeScrubPointerId.value !== event.pointerId) {
    return;
  }

  const element = event.currentTarget;
  if (!(element instanceof HTMLElement)) {
    return;
  }

  scrubTimeSeconds.value = resolveSeekTimeFromPointer(event.clientX, element);
}

function handleSeekPointerUp(event: PointerEvent) {
  if (!isScrubbing.value || activeScrubPointerId.value !== event.pointerId) {
    return;
  }

  const element = event.currentTarget;
  if (element instanceof HTMLElement) {
    const nextTime = resolveSeekTimeFromPointer(event.clientX, element);
    commitSeek(nextTime);
    element.releasePointerCapture?.(event.pointerId);
  }

  clearScrubState();
  syncControlVisibilityFromDom();
}

function handleSeekPointerCancel(event: PointerEvent) {
  const element = event.currentTarget;
  if (element instanceof HTMLElement && activeScrubPointerId.value === event.pointerId) {
    element.releasePointerCapture?.(event.pointerId);
  }

  clearScrubState();
  syncControlVisibilityFromDom();
}

function handleVolumePointerDown(event: PointerEvent) {
  const element = event.currentTarget;
  if (!(element instanceof HTMLElement)) {
    return;
  }

  activeVolumePointerId.value = event.pointerId;
  element.setPointerCapture?.(event.pointerId);
}

function handleVolumePointerUp(event: PointerEvent) {
  const element = event.currentTarget;
  if (!(element instanceof HTMLElement) || activeVolumePointerId.value !== event.pointerId) {
    return;
  }

  activeVolumePointerId.value = null;
  element.releasePointerCapture?.(event.pointerId);
  syncControlVisibilityFromDom();
}

function handleVolumePointerCancel(event: PointerEvent) {
  const element = event.currentTarget;
  if (element instanceof HTMLElement && activeVolumePointerId.value === event.pointerId) {
    element.releasePointerCapture?.(event.pointerId);
  }

  activeVolumePointerId.value = null;
  syncControlVisibilityFromDom();
}

function handleVolumeInput(event: Event) {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }

  const nextVolume = Number(target.value) / 100;
  emit("audio-change", {
    volume: nextVolume,
    muted: nextVolume === 0 ? true : false,
  });
}

function retryPlayback() {
  void ensureMediaReady(true);
}

watch(
  () => [props.manifestUrl, props.loadMode] as const,
  () => {
    void ensureMediaReady();
  },
  { immediate: true },
);

watch(
  () =>
    [
      resolvedFitMode.value,
      videoShape.value,
      stageLayout.value,
      overlayLayout.value,
      backdropMode.value,
    ] as const,
  () => {
    emitPresentationChange();
  },
  { immediate: true },
);

watch(videoElement, (element) => {
  if (element) {
    void ensureMediaReady();
  }
});

watch(playerRoot, (element, previousElement) => {
  if (resizeObserver && previousElement) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }

  if (element && typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      updateStageAspectRatio();
    });
    resizeObserver.observe(element);
    updateStageAspectRatio();
  }

  syncControlVisibilityFromDom();
});

watch(
  () => props.active,
  (active) => {
    syncControlVisibilityFromDom();

    if (props.loadMode === "distant") {
      if (!active) {
        activeVolumePointerId.value = null;
        clearScrubState();
      }

      return;
    }

    if (active) {
      if (attachedManifestUrl !== props.manifestUrl) {
        void ensureMediaReady();
        return;
      }

      void attemptPlayback();
      return;
    }

    isPlaybackPaused.value = false;
    requiresManualPlay.value = false;
    activeVolumePointerId.value = null;
    isPointerInsidePlayer.value = false;
    clearScrubState();
    pausePlayback();
  },
  { immediate: true },
);

watch(
  () => props.muted,
  (muted) => {
    const video = getVideoElement();
    if (video) {
      video.muted = muted;
    }
  },
  { immediate: true },
);

watch(
  () => props.volume,
  (volume) => {
    const video = getVideoElement();
    if (video) {
      video.volume = volume;
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  currentLoadToken += 1;
  activeVolumePointerId.value = null;
  isPointerInsidePlayer.value = false;
  clearScrubState();
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  destroyHls();
});
</script>

<style scoped>
.feed-player {
  --feed-player-inline-padding: clamp(12px, 2vw, 20px);
  --feed-player-block-padding: clamp(12px, 2.2vh, 20px);
  --feed-player-plane-radius: clamp(8px, 1.6vw, 12px);
  --feed-player-control-bar-reserve: var(
    --feed-player-controls-reserve,
    clamp(88px, 14vh, 112px)
  );
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(9, 12, 18, 0.94), rgba(7, 10, 15, 0.98));
  isolation: isolate;
}

.feed-player__backdrop-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.feed-player__backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at center, rgba(143, 174, 255, 0.08), transparent 46%),
    linear-gradient(180deg, rgba(7, 10, 15, 0.94), rgba(7, 10, 15, 0.98));
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  filter: blur(24px) saturate(0.75);
  transform: scale(1.08);
  opacity: 0.54;
}

.feed-player__backdrop--image {
  opacity: 0.62;
}

.feed-player__backdrop--ambient {
  background:
    radial-gradient(circle at 18% 18%, rgba(143, 174, 255, 0.14), transparent 26%),
    radial-gradient(circle at 82% 20%, rgba(155, 215, 199, 0.08), transparent 24%),
    radial-gradient(circle at 50% 84%, rgba(197, 183, 255, 0.08), transparent 28%);
  filter: blur(40px);
  opacity: 0.4;
  transform: scale(1.04);
}

.feed-player__backdrop--mesh {
  background:
    linear-gradient(120deg, rgba(10, 14, 22, 0.12), transparent 34%, rgba(10, 14, 22, 0.18) 100%),
    linear-gradient(180deg, rgba(8, 11, 17, 0.12), rgba(8, 11, 17, 0.34));
}

.feed-player__media-shell {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
  padding: var(--feed-player-block-padding) var(--feed-player-inline-padding);
}

.feed-player__media-plane {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: var(--feed-player-plane-radius);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.24);
}

.feed-player__media-plane::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border: 1px solid rgba(255, 255, 255, 0.03);
  pointer-events: none;
}

.feed-player__media {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: block;
  background: transparent;
  transition:
    transform 220ms ease,
    filter 220ms ease,
    opacity 220ms ease;
}

.feed-player[data-fit-mode="contain"] .feed-player__media {
  object-position: center;
}

.feed-player[data-fit-mode="contain"][data-backdrop-mode="immersive"] .feed-player__backdrop--image {
  opacity: 0.7;
}

.feed-player[data-fit-mode="cover"] .feed-player__backdrop--image,
.feed-player[data-backdrop-mode="soft"] .feed-player__backdrop--image {
  opacity: 0.28;
}

.feed-player[data-video-shape="landscape"] .feed-player__backdrop--image,
.feed-player[data-video-shape="ultra-wide"] .feed-player__backdrop--image {
  filter: blur(28px) saturate(0.74);
}

.feed-player[data-stage-layout="portrait"] {
  --feed-player-inline-padding: clamp(12px, 2vw, 20px);
  --feed-player-block-padding: clamp(12px, 2.2vh, 22px);
}

.feed-player[data-stage-layout="balanced"] {
  --feed-player-inline-padding: clamp(14px, 2.2vw, 22px);
  --feed-player-block-padding: clamp(14px, 2.6vh, 24px);
}

.feed-player[data-stage-layout="landscape"] {
  --feed-player-inline-padding: clamp(10px, 1.6vw, 16px);
  --feed-player-block-padding: clamp(10px, 1.6vh, 16px);
}

.feed-player[data-stage-layout="cinematic"] {
  --feed-player-inline-padding: clamp(8px, 1.4vw, 14px);
  --feed-player-block-padding: clamp(10px, 1.8vh, 18px);
}

.feed-player[data-load-mode="nearby"] .feed-player__media {
  transform: scale(1.008);
  filter: saturate(0.92);
}

.feed-player[data-load-mode="distant"] .feed-player__media {
  opacity: 0.92;
  filter: saturate(0.82) brightness(0.9);
}

.feed-player__shade {
  position: absolute;
  inset: 0;
  z-index: 2;
  background:
    linear-gradient(180deg, rgba(7, 10, 15, 0.12), rgba(7, 10, 15, 0.02) 26%),
    linear-gradient(0deg, rgba(7, 10, 15, 0.66), rgba(7, 10, 15, 0.08) 42%);
  pointer-events: none;
}

.feed-player__overlay {
  position: absolute;
  inset: 0;
  z-index: 4;
  display: grid;
  align-content: end;
  gap: 10px;
  padding:
    clamp(20px, 3vw, 28px)
    clamp(20px, 3vw, 28px)
    calc(var(--feed-player-control-bar-reserve) + clamp(22px, 4vh, 38px));
  background: linear-gradient(180deg, rgba(7, 10, 15, 0.02), rgba(7, 10, 15, 0.52));
}

.feed-player__overlay h3 {
  margin: 0;
  font-size: clamp(1.26rem, 2.3vw, 1.62rem);
  line-height: 1.12;
}

.feed-player__overlay p {
  max-width: 32ch;
  color: rgba(234, 239, 247, 0.78);
}

.feed-player__eyebrow {
  color: rgba(191, 208, 255, 0.88);
  letter-spacing: 0;
  font-size: 0.72rem;
  font-weight: 800;
}

.feed-player__action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feed-player__action {
  width: fit-content;
  min-height: 40px;
  padding: 10px 16px;
  border: 1px solid rgba(205, 216, 240, 0.18);
  border-radius: 8px;
  color: #0c1420;
  background: linear-gradient(180deg, rgba(191, 208, 255, 0.94), rgba(143, 174, 255, 0.96));
  cursor: pointer;
  font-weight: 800;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    filter 180ms ease;
}

.feed-player__action:hover {
  transform: translateY(-1px);
  background: linear-gradient(180deg, rgba(203, 217, 255, 0.96), rgba(155, 184, 255, 0.98));
}

.feed-player__action:active {
  transform: translateY(0);
  filter: brightness(0.96);
}

.feed-player__overlay--loading {
  background: linear-gradient(180deg, rgba(7, 10, 15, 0.02), rgba(7, 10, 15, 0.56));
}

.feed-player__overlay--processing {
  background:
    linear-gradient(180deg, rgba(7, 10, 15, 0.02), rgba(48, 36, 16, 0.56)),
    linear-gradient(0deg, rgba(7, 10, 15, 0.08), rgba(7, 10, 15, 0));
}

.feed-player__overlay--error {
  background:
    linear-gradient(180deg, rgba(7, 10, 15, 0.02), rgba(52, 21, 26, 0.6)),
    linear-gradient(0deg, rgba(7, 10, 15, 0.08), rgba(7, 10, 15, 0));
}

.feed-player__control-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  pointer-events: none;
  opacity: 1;
  transform: translateY(0);
  padding:
    0
    calc(var(--feed-player-inline-padding) + 2px)
    calc(var(--feed-player-block-padding) + 2px);
  transition:
    opacity 180ms ease,
    transform 220ms ease;
  will-change: opacity, transform;
}

.feed-player__control-shell {
  display: grid;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(18, 22, 31, 0.36), rgba(18, 22, 31, 0.72)),
    rgba(18, 22, 31, 0.58);
  border: 1px solid rgba(200, 212, 235, 0.16);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(14px) saturate(1.02);
  pointer-events: auto;
}

.feed-player__progress-shell {
  position: relative;
  display: flex;
  align-items: center;
  height: 18px;
  cursor: default;
  touch-action: none;
}

.feed-player__progress-shell--interactive {
  cursor: pointer;
}

.feed-player__progress-rail,
.feed-player__progress-fill {
  position: absolute;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 999px;
  transform-origin: left center;
}

.feed-player__progress-rail {
  background: rgba(255, 255, 255, 0.14);
}

.feed-player__progress-fill {
  background: linear-gradient(90deg, rgba(191, 208, 255, 0.94), rgba(143, 174, 255, 0.9));
}

.feed-player__progress-thumb {
  position: absolute;
  top: 50%;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #eef3ff;
  box-shadow:
    0 0 0 3px rgba(191, 208, 255, 0.12),
    0 6px 14px rgba(0, 0, 0, 0.22);
  transform: translate(-50%, -50%);
}

.feed-player__transport-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.feed-player__transport-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 999px;
  color: #f8fafc;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition:
    transform 180ms ease,
    background-color 180ms ease,
    border-color 180ms ease,
    opacity 180ms ease,
    color 180ms ease;
}

.feed-player__transport-button:hover:not(:disabled) {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(200, 212, 235, 0.16);
}

.feed-player__transport-button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.feed-player__transport-button--primary {
  color: #0c1420;
  background: linear-gradient(180deg, rgba(191, 208, 255, 0.94), rgba(143, 174, 255, 0.96));
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.22);
}

.feed-player__transport-button--primary:hover:not(:disabled) {
  background: linear-gradient(180deg, rgba(203, 217, 255, 0.96), rgba(155, 184, 255, 0.98));
}

.feed-player__transport-button--ghost {
  width: 34px;
  height: 34px;
}

.feed-player__transport-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.feed-player__time-group {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: rgba(239, 243, 250, 0.84);
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
}

.feed-player__time-separator {
  color: rgba(226, 232, 240, 0.34);
}

.feed-player__volume-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.feed-player__volume-slider {
  display: inline-flex;
  align-items: center;
  width: clamp(72px, 11vw, 96px);
}

.feed-player__volume-slider input {
  width: 100%;
  margin: 0;
  accent-color: #bfd0ff;
  cursor: pointer;
}

.feed-player__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.feed-player__volume-slider input::-webkit-slider-runnable-track {
  height: 3px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}

.feed-player__volume-slider input::-webkit-slider-thumb {
  width: 9px;
  height: 9px;
  margin-top: -3px;
  border: 0;
  border-radius: 999px;
  background: #eef3ff;
  box-shadow: 0 0 0 3px rgba(191, 208, 255, 0.12);
  -webkit-appearance: none;
}

.feed-player__volume-slider input::-moz-range-track {
  height: 3px;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}

.feed-player__volume-slider input::-moz-range-thumb {
  width: 9px;
  height: 9px;
  border: 0;
  border-radius: 999px;
  background: #eef3ff;
  box-shadow: 0 0 0 3px rgba(191, 208, 255, 0.12);
}

.feed-player__volume-slider input:focus-visible,
.feed-player__transport-button:focus-visible,
.feed-player__progress-shell:focus-visible {
  outline: 2px solid rgba(191, 208, 255, 0.74);
  outline-offset: 2px;
}

.feed-player__volume-slider input:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

@media (prefers-reduced-motion: reduce) {
  .feed-player__media,
  .feed-player__action,
  .feed-player__transport-button,
  .feed-player__control-bar {
    transition: none;
  }
}

@media (hover: hover) and (pointer: fine) {
  .feed-player__control-bar {
    opacity: 0;
    transform: translateY(10px);
  }

  .feed-player__control-shell {
    pointer-events: none;
  }

  .feed-player[data-controls-visible="true"] .feed-player__control-bar {
    opacity: 1;
    transform: translateY(0);
  }

  .feed-player[data-controls-visible="true"] .feed-player__control-shell {
    pointer-events: auto;
  }
}

@media (max-width: 720px) {
  .feed-player__control-bar {
    padding:
      0
      calc(var(--feed-player-inline-padding) - 2px)
      calc(var(--feed-player-block-padding) - 2px);
  }

  .feed-player__control-shell {
    gap: 10px;
    padding: 9px 11px;
    border-radius: 8px;
  }

  .feed-player__transport-row {
    gap: 10px;
  }

  .feed-player__time-group {
    gap: 6px;
    font-size: 0.82rem;
  }

  .feed-player__volume-group {
    gap: 6px;
  }

  .feed-player__volume-slider {
    width: 64px;
  }

  .feed-player__overlay {
    padding:
      20px
      20px
      calc(var(--feed-player-control-bar-reserve) + 22px);
  }
}

@media (max-width: 520px) {
  .feed-player__volume-slider {
    width: 54px;
  }

  .feed-player__transport-button {
    width: 36px;
    height: 36px;
  }

  .feed-player__transport-button--ghost {
    width: 32px;
    height: 32px;
  }

  .feed-player__transport-icon {
    width: 16px;
    height: 16px;
  }
}
</style>
