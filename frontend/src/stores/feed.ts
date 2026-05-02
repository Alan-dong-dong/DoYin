import { defineStore } from "pinia";

import { ApiError } from "@/lib/api";
import {
  reportVideoPlaybackStart,
  requestVideoFeed,
  type FeedVideoItem,
} from "@/lib/videos";

const DEFAULT_FEED_PAGE_SIZE = 5;
const PREFETCH_THRESHOLD = 2;
const DEFAULT_PLAYER_VOLUME = 0.6;
const PLAYER_PRELOAD_RADIUS = 1;

export type FeedItemLoadState = "active" | "nearby" | "distant";

interface FeedState {
  items: FeedVideoItem[];
  currentIndex: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
  isInitialLoading: boolean;
  isLoadingMore: boolean;
  initialErrorMessage: string | null;
  appendErrorMessage: string | null;
  playbackReportState: Record<number, "pending" | "done">;
  playerVolume: number;
  playerMuted: boolean;
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function mergeUniqueVideos(
  existingItems: FeedVideoItem[],
  incomingItems: FeedVideoItem[],
): FeedVideoItem[] {
  const seenIds = new Set(existingItems.map((item) => item.id));
  const appendedItems = incomingItems.filter((item) => !seenIds.has(item.id));
  return [...existingItems, ...appendedItems];
}

function clampVolume(volume: number): number {
  if (!Number.isFinite(volume)) {
    return DEFAULT_PLAYER_VOLUME;
  }

  return Math.min(Math.max(volume, 0), 1);
}

function clampIndex(index: number, itemCount: number): number {
  if (itemCount === 0) {
    return 0;
  }

  if (!Number.isFinite(index)) {
    return 0;
  }

  return Math.min(Math.max(Math.trunc(index), 0), itemCount - 1);
}

export const useFeedStore = defineStore("feed", {
  state: (): FeedState => ({
    items: [],
    currentIndex: 0,
    page: 0,
    pageSize: DEFAULT_FEED_PAGE_SIZE,
    hasMore: true,
    isInitialLoading: false,
    isLoadingMore: false,
    initialErrorMessage: null,
    appendErrorMessage: null,
    playbackReportState: {},
    playerVolume: DEFAULT_PLAYER_VOLUME,
    playerMuted: true,
  }),
  getters: {
    currentVideo(state): FeedVideoItem | null {
      return state.items[state.currentIndex] ?? null;
    },
    playbackWindowStart(state): number {
      return clampIndex(state.currentIndex - PLAYER_PRELOAD_RADIUS, state.items.length);
    },
    playbackWindowEnd(state): number {
      return clampIndex(state.currentIndex + PLAYER_PRELOAD_RADIUS, state.items.length);
    },
    navigationStatusLabel(state): string {
      if (state.items.length === 0) {
        return "";
      }

      if (state.appendErrorMessage) {
        return "重试后继续加载";
      }

      if (state.items.length === 1 && !state.hasMore) {
        return "仅有一个视频";
      }

      if (state.currentIndex === 0) {
        return "第一个视频";
      }

      if (state.currentIndex >= state.items.length - 1) {
        if (state.isLoadingMore || state.hasMore) {
          return "正在加载下一个";
        }

        return "最后一个视频";
      }

      return "继续滑动浏览";
    },
    isEmpty(state): boolean {
      return !state.isInitialLoading && !state.initialErrorMessage && state.items.length === 0;
    },
    getItemLoadState(state): (index: number) => FeedItemLoadState {
      return (index: number) => {
        if (state.items.length === 0) {
          return "distant";
        }

        const normalizedIndex = clampIndex(index, state.items.length);
        if (normalizedIndex === state.currentIndex) {
          return "active";
        }

        return Math.abs(normalizedIndex - state.currentIndex) <= PLAYER_PRELOAD_RADIUS
          ? "nearby"
          : "distant";
      };
    },
  },
  actions: {
    resetFeed() {
      this.items = [];
      this.currentIndex = 0;
      this.page = 0;
      this.hasMore = true;
      this.isInitialLoading = false;
      this.isLoadingMore = false;
      this.initialErrorMessage = null;
      this.appendErrorMessage = null;
      this.playbackReportState = {};
    },
    setCurrentIndex(index: number) {
      this.currentIndex = clampIndex(index, this.items.length);
      return this.currentIndex;
    },
    setPlayerVolume(volume: number) {
      const nextVolume = clampVolume(volume);
      this.playerVolume = nextVolume;
      this.playerMuted = nextVolume === 0;
    },
    setPlayerMuted(muted: boolean) {
      this.playerMuted = muted;

      if (!muted && this.playerVolume === 0) {
        this.playerVolume = DEFAULT_PLAYER_VOLUME;
      }
    },
    togglePlayerMuted() {
      this.setPlayerMuted(!this.playerMuted);
    },
    shouldPrefetchForIndex(index: number): boolean {
      return this.hasMore && index >= Math.max(this.items.length - PREFETCH_THRESHOLD, 0);
    },
    async loadInitialFeed(accessToken: string) {
      this.resetFeed();
      this.isInitialLoading = true;

      try {
        const response = await requestVideoFeed(accessToken, 1, this.pageSize);
        this.items = response.items;
        this.page = response.page;
        this.pageSize = response.page_size;
        this.hasMore = response.has_more;
        this.initialErrorMessage = null;
        this.currentIndex = 0;
      } catch (error) {
        this.initialErrorMessage = getErrorMessage(error, "无法加载视频刷流。");
      } finally {
        this.isInitialLoading = false;
      }
    },
    async loadNextPage(accessToken: string) {
      if (!this.hasMore || this.isInitialLoading || this.isLoadingMore) {
        return;
      }

      this.isLoadingMore = true;
      this.appendErrorMessage = null;

      try {
        const nextPage = this.page + 1;
        const response = await requestVideoFeed(accessToken, nextPage, this.pageSize);
        this.items = mergeUniqueVideos(this.items, response.items);
        this.page = response.page;
        this.pageSize = response.page_size;
        this.hasMore = response.has_more;
      } catch (error) {
        this.appendErrorMessage = getErrorMessage(error, "无法加载更多视频。");
      } finally {
        this.isLoadingMore = false;
      }
    },
    async reportPlaybackStarted(accessToken: string, videoId: number) {
      const status = this.playbackReportState[videoId];
      if (status === "pending" || status === "done") {
        return;
      }

      this.playbackReportState = {
        ...this.playbackReportState,
        [videoId]: "pending",
      };

      try {
        await reportVideoPlaybackStart(accessToken, videoId);
        this.playbackReportState = {
          ...this.playbackReportState,
          [videoId]: "done",
        };
      } catch {
        const nextPlaybackState = { ...this.playbackReportState };
        delete nextPlaybackState[videoId];
        this.playbackReportState = nextPlaybackState;
      }
    },
  },
});
