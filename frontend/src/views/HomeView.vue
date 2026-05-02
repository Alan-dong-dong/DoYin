<template>
  <main class="feed-shell">
    <div class="feed-shell__chrome">
      <div class="feed-shell__utility-cluster">
        <div class="feed-shell__utility-info">
          <div class="feed-shell__brand">
            <strong>{{ name }}</strong>
            <small>沉浸刷流</small>
          </div>
          <div v-if="currentUser" class="feed-shell__user">
            <span>{{ currentUser.display_name }}</span>
            <small>@{{ currentUser.username }}</small>
          </div>
        </div>
        <div class="feed-shell__actions">
          <RouterLink class="feed-shell__action" to="/publish">发布</RouterLink>
          <RouterLink v-if="currentUser?.is_admin" class="feed-shell__action" to="/admin/videos">
            后台
          </RouterLink>
        </div>
      </div>
    </div>

    <section v-if="isInitialLoading" class="feed-state">
      <p class="feed-state__eyebrow">正在加载</p>
      <h2>正在准备下一段视频</h2>
      <p>正在获取可播放内容，并把首个视频对齐到沉浸式观看位置。</p>
    </section>

    <section v-else-if="initialErrorMessage" class="feed-state feed-state--error">
      <p class="feed-state__eyebrow">加载失败</p>
      <h2>暂时无法载入首页刷流</h2>
      <p>{{ initialErrorMessage }}</p>
      <button class="feed-state__action" type="button" @click="handleRetryInitialLoad">
        重新加载
      </button>
    </section>

    <section v-else-if="isEmpty" class="feed-state feed-state--empty">
      <p class="feed-state__eyebrow">暂无内容</p>
      <h2>还没有可播放的视频</h2>
      <p>发布一段视频并等待转码完成后，它会出现在这里。</p>
      <RouterLink class="feed-state__action feed-state__action--link" to="/publish">
        去发布视频
      </RouterLink>
    </section>

    <section v-else ref="feedViewport" class="feed-stream">
      <article
        v-for="(video, index) in items"
        :key="video.id"
        :ref="(element) => setFeedItemRef(element, index)"
        class="feed-stream__item"
        :data-index="index"
        :data-active="index === currentIndex"
        :data-video-fit="resolveVideoPresentation(video.id).fitMode"
        :data-video-shape="resolveVideoPresentation(video.id).shape"
        :data-stage-layout="resolveVideoPresentation(video.id).stageLayout"
        :data-overlay-layout="resolveVideoPresentation(video.id).overlayLayout"
        :data-backdrop-mode="resolveVideoPresentation(video.id).backdropMode"
      >
        <div class="feed-stream__frame">
          <HlsVideoPlayer
            :manifest-url="video.hls_manifest_url"
            :poster-url="video.cover_image_url"
            :title="video.title"
            :active="index === currentIndex"
            :load-mode="feedStore.getItemLoadState(index)"
            :muted="playerMuted"
            :volume="playerVolume"
            @audio-change="handleAudioChange"
            @playing="handlePlayerPlaying(video.id)"
            @presentation-change="handlePresentationChange(video.id, $event)"
          />

          <div class="feed-stream__overlay">
            <div class="feed-stream__caption-shell">
              <div class="feed-stream__meta">
                <div v-if="index === currentIndex" class="feed-stream__meta-kicker">
                  <span class="feed-stream__tag">正在播放</span>
                  <span v-if="index === currentIndex" class="feed-stream__status">
                    {{ navigationStatusLabel }}
                  </span>
                </div>

                <p class="feed-stream__creator">
                  <span>{{ video.creator.display_name }}</span>
                  <small>@{{ video.creator.username }}</small>
                </p>
                <h2>{{ video.title }}</h2>
                <p v-if="video.caption" class="feed-stream__caption">{{ video.caption }}</p>
              </div>

              <div
                v-if="index === currentIndex && appendErrorMessage"
                class="feed-stream__inline-feedback feed-stream__inline-feedback--error"
              >
                <span>{{ appendErrorMessage }}</span>
                <button type="button" @click="handleRetryAppend">重试</button>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <div v-if="!isInitialLoading && !initialErrorMessage && items.length > 0" class="feed-toast-stack">
      <div v-if="isLoadingMore" class="feed-toast">
        <span>正在加载更多视频...</span>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";

import HlsVideoPlayer from "@/components/HlsVideoPlayer.vue";
import type { FeedPlayerPresentation } from "@/lib/feedPresentation";
import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";
import { useFeedStore } from "@/stores/feed";

const appStore = useAppStore();
const authStore = useAuthStore();
const feedStore = useFeedStore();

const { name } = storeToRefs(appStore);
const { accessToken, currentUser } = storeToRefs(authStore);
const {
  appendErrorMessage,
  currentIndex,
  initialErrorMessage,
  isEmpty,
  isInitialLoading,
  isLoadingMore,
  items,
  navigationStatusLabel,
  playerMuted,
  playerVolume,
} = storeToRefs(feedStore);

const feedViewport = ref<HTMLElement | null>(null);
const feedItemElements = ref<HTMLElement[]>([]);
const videoPresentationById = ref<Record<number, FeedPlayerPresentation>>({});

let intersectionObserver: IntersectionObserver | null = null;

function cleanupObserver() {
  if (intersectionObserver) {
    intersectionObserver.disconnect();
    intersectionObserver = null;
  }
}

function setFeedItemRef(element: Element | null, index: number) {
  if (element instanceof HTMLElement) {
    feedItemElements.value[index] = element;
    return;
  }

  delete feedItemElements.value[index];
}

function maybeLoadMore(index: number) {
  if (!accessToken.value || !feedStore.shouldPrefetchForIndex(index)) {
    return;
  }

  void feedStore.loadNextPage(accessToken.value);
}

function resolveVideoPresentation(videoId: number) {
  return (
    videoPresentationById.value[videoId] ?? {
      fitMode: "contain" as const,
      shape: "unknown" as const,
      stageLayout: "balanced" as const,
      overlayLayout: "balanced" as const,
      backdropMode: "immersive" as const,
    }
  );
}

function setupObserver() {
  cleanupObserver();

  if (!feedViewport.value || feedItemElements.value.length === 0) {
    return;
  }

  intersectionObserver = new IntersectionObserver(
    (entries) => {
      const visibleEntry = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];

      if (!visibleEntry) {
        return;
      }

      const nextIndex = Number((visibleEntry.target as HTMLElement).dataset.index ?? "-1");
      if (Number.isNaN(nextIndex) || nextIndex < 0) {
        return;
      }

      feedStore.setCurrentIndex(nextIndex);
      maybeLoadMore(nextIndex);
    },
    {
      root: feedViewport.value,
      threshold: [0.55, 0.75, 0.95],
    },
  );

  feedItemElements.value.forEach((element) => {
    if (element) {
      intersectionObserver?.observe(element);
    }
  });
}

async function loadInitialFeed() {
  if (!authStore.accessToken) {
    return;
  }

  await feedStore.loadInitialFeed(authStore.accessToken);
  await nextTick();
  setupObserver();
  maybeLoadMore(currentIndex.value);
}

function handlePlayerPlaying(videoId: number) {
  if (!authStore.accessToken) {
    return;
  }

  void feedStore.reportPlaybackStarted(authStore.accessToken, videoId);
}

function handleAudioChange(payload: { volume: number; muted: boolean }) {
  feedStore.setPlayerVolume(payload.volume);
  feedStore.setPlayerMuted(payload.muted);
}

function handlePresentationChange(
  videoId: number,
  payload: FeedPlayerPresentation,
) {
  videoPresentationById.value = {
    ...videoPresentationById.value,
    [videoId]: payload,
  };
}

function handleRetryInitialLoad() {
  void loadInitialFeed();
}

async function handleRetryAppend() {
  if (!authStore.accessToken) {
    return;
  }

  await feedStore.loadNextPage(authStore.accessToken);
  await nextTick();
  setupObserver();
}

onMounted(() => {
  void loadInitialFeed();
});

watch(
  () => items.value.length,
  async () => {
    await nextTick();
    setupObserver();
  },
);

watch(
  () => currentIndex.value,
  (index) => {
    maybeLoadMore(index);
  },
);

onBeforeUnmount(() => {
  cleanupObserver();
});
</script>
