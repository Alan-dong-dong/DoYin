<template>
  <main class="admin-shell">
    <header class="admin-shell__header">
      <div class="admin-shell__intro">
        <p class="admin-shell__eyebrow">后台管理</p>
        <h1>审核上传内容、查看转码状态并管理刷流可见性</h1>
        <p class="admin-shell__lead">
          这里保留最小可用的管理能力：筛选视频、检查最新处理状态，并隐藏或恢复公开视频。
        </p>
      </div>

      <div class="admin-shell__actions">
        <div v-if="currentUser" class="admin-shell__user">
          <span>{{ currentUser.display_name }}</span>
          <small>{{ currentUser.email }}</small>
        </div>
        <RouterLink class="admin-shell__link" to="/">刷流</RouterLink>
        <RouterLink class="admin-shell__link" to="/publish">发布</RouterLink>
        <RouterLink class="admin-shell__link admin-shell__link--active" to="/admin/videos">
          后台
        </RouterLink>
      </div>
    </header>

    <section class="admin-panel admin-panel--filters">
      <form class="admin-filters" @submit.prevent="handleApplyFilters">
        <label class="admin-filters__field">
          <span>关键词</span>
          <input
            v-model="keyword"
            type="text"
            placeholder="搜索标题、邮箱、用户名或昵称"
          />
        </label>

        <label class="admin-filters__field">
          <span>转码状态</span>
          <select v-model="statusFilter">
            <option value="all">全部状态</option>
            <option value="pending">排队中</option>
            <option value="processing">处理中</option>
            <option value="ready">已就绪</option>
            <option value="failed">失败</option>
          </select>
        </label>

        <label class="admin-filters__field">
          <span>可见性</span>
          <select v-model="visibilityFilter">
            <option value="all">全部可见性</option>
            <option value="public">公开</option>
            <option value="hidden">已隐藏</option>
          </select>
        </label>

        <div class="admin-filters__actions">
          <button class="admin-filters__button" type="submit">应用筛选</button>
          <button
            class="admin-filters__button admin-filters__button--ghost"
            type="button"
            @click="handleResetFilters"
          >
            重置
          </button>
        </div>
      </form>
    </section>

    <section v-if="isLoading" class="admin-panel admin-state">
      <p class="admin-state__eyebrow">正在加载</p>
      <h2>正在获取最新管理列表</h2>
      <p>正在读取视频条目、处理状态和可见性控制。</p>
    </section>

    <section v-else-if="errorMessage" class="admin-panel admin-state admin-state--error">
      <p class="admin-state__eyebrow">加载失败</p>
      <h2>无法加载视频管理列表</h2>
      <p>{{ errorMessage }}</p>
      <button class="admin-filters__button" type="button" @click="handleRetryLoad">
        重新加载
      </button>
    </section>

    <section v-else-if="isEmpty" class="admin-panel admin-state admin-state--empty">
      <p class="admin-state__eyebrow">没有结果</p>
      <h2>当前筛选条件没有匹配的视频</h2>
      <p>调整关键词、处理状态或可见性后再试一次。</p>
    </section>

    <section v-else class="admin-panel admin-panel--inventory">
      <div class="admin-inventory__summary">
        <div>
          <p class="admin-state__eyebrow">视频列表</p>
          <h2>{{ inventory?.total_items ?? 0 }} 个匹配视频</h2>
        </div>
        <p>第 {{ currentPage }} 页</p>
      </div>

      <p v-if="actionErrorMessage" class="admin-inventory__error" role="alert">
        {{ actionErrorMessage }}
      </p>

      <div class="admin-table-wrapper">
        <table class="admin-table">
          <thead>
            <tr>
              <th scope="col">视频</th>
              <th scope="col">创作者</th>
              <th scope="col">可见性</th>
              <th scope="col">转码</th>
              <th scope="col">失败原因</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="video in inventory?.items ?? []" :key="video.id">
              <td>
                <div class="admin-video-cell">
                  <strong>{{ video.title }}</strong>
                  <p v-if="video.caption">{{ video.caption }}</p>
                  <small>视频 #{{ video.id }} · 更新于 {{ formatTimestamp(video.updated_at) }}</small>
                </div>
              </td>
              <td>
                <div class="admin-creator-cell">
                  <strong>{{ video.creator.display_name }}</strong>
                  <small>@{{ video.creator.username }}</small>
                  <small>{{ video.creator.email }}</small>
                </div>
              </td>
              <td>
                <span class="admin-pill" :data-tone="video.visibility">
                  {{ formatVisibility(video.visibility) }}
                </span>
              </td>
              <td>
                <span class="admin-pill" :data-tone="video.latest_upload_status ?? 'unknown'">
                  {{ formatUploadStatus(video.latest_upload_status) }}
                </span>
              </td>
              <td class="admin-table__failure">
                {{ video.failure_message ?? "暂无失败记录" }}
              </td>
              <td>
                <button
                  class="admin-filters__button"
                  :class="
                    video.visibility === 'public'
                      ? 'admin-filters__button--danger'
                      : 'admin-filters__button--positive'
                  "
                  type="button"
                  :disabled="pendingVideoId === video.id"
                  @click="handleToggleVisibility(video)"
                >
                  {{
                    pendingVideoId === video.id
                      ? "更新中..."
                      : video.visibility === "public"
                        ? "隐藏视频"
                        : "恢复公开"
                  }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="admin-pagination">
        <button
          class="admin-filters__button admin-filters__button--ghost"
          type="button"
          :disabled="currentPage <= 1"
          @click="handlePreviousPage"
        >
          上一页
        </button>
        <button
          class="admin-filters__button admin-filters__button--ghost"
          type="button"
          :disabled="!(inventory?.has_more)"
          @click="handleNextPage"
        >
          下一页
        </button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";

import { ApiError } from "@/lib/api";
import {
  requestAdminVideoInventory,
  updateAdminVideoVisibility,
  type AdminVideoListItem,
  type AdminVideoListResponse,
  type AdminVideoVisibility,
  type VideoUploadJobStatus,
} from "@/lib/videos";
import { useAuthStore } from "@/stores/auth";

const PAGE_SIZE = 10;

const authStore = useAuthStore();
const { accessToken, currentUser } = storeToRefs(authStore);

const keyword = ref("");
const statusFilter = ref<VideoUploadJobStatus | "all">("all");
const visibilityFilter = ref<AdminVideoVisibility | "all">("all");
const currentPage = ref(1);
const inventory = ref<AdminVideoListResponse | null>(null);
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
const actionErrorMessage = ref<string | null>(null);
const pendingVideoId = ref<number | null>(null);

const isEmpty = computed(
  () => !isLoading.value && !errorMessage.value && (inventory.value?.items.length ?? 0) === 0,
);

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function formatUploadStatus(status: VideoUploadJobStatus | null | undefined): string {
  switch (status) {
    case "pending":
      return "排队中";
    case "processing":
      return "处理中";
    case "ready":
      return "已就绪";
    case "failed":
      return "失败";
    default:
      return "未知";
  }
}

function formatVisibility(visibility: AdminVideoVisibility): string {
  return visibility === "public" ? "公开" : "已隐藏";
}

function buildFilters(page = currentPage.value) {
  return {
    page,
    pageSize: PAGE_SIZE,
    q: keyword.value.trim() || undefined,
    status: statusFilter.value === "all" ? undefined : statusFilter.value,
    visibility: visibilityFilter.value === "all" ? undefined : visibilityFilter.value,
  };
}

async function loadInventory(page = currentPage.value) {
  if (!accessToken.value) {
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;
  try {
    inventory.value = await requestAdminVideoInventory(accessToken.value, buildFilters(page));
    currentPage.value = page;
  } catch (error) {
    errorMessage.value = getErrorMessage(error, "无法加载后台视频列表。");
  } finally {
    isLoading.value = false;
  }
}

function handleApplyFilters() {
  void loadInventory(1);
}

function handleResetFilters() {
  keyword.value = "";
  statusFilter.value = "all";
  visibilityFilter.value = "all";
  void loadInventory(1);
}

function handleRetryLoad() {
  void loadInventory(currentPage.value);
}

async function handleToggleVisibility(video: AdminVideoListItem) {
  if (!accessToken.value) {
    return;
  }

  pendingVideoId.value = video.id;
  actionErrorMessage.value = null;
  try {
    await updateAdminVideoVisibility(
      accessToken.value,
      video.id,
      video.visibility === "public" ? "hidden" : "public",
    );
    await loadInventory(currentPage.value);
  } catch (error) {
    actionErrorMessage.value = getErrorMessage(error, "无法更新该视频的可见性。");
  } finally {
    pendingVideoId.value = null;
  }
}

function handlePreviousPage() {
  if (currentPage.value <= 1) {
    return;
  }

  void loadInventory(currentPage.value - 1);
}

function handleNextPage() {
  if (!inventory.value?.has_more) {
    return;
  }

  void loadInventory(currentPage.value + 1);
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "不可用";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN");
}

onMounted(() => {
  void loadInventory();
});
</script>
