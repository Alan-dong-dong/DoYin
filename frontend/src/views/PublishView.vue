<template>
  <main class="publish-shell">
    <section class="publish-shell__intro">
      <p class="publish-shell__eyebrow">创作者发布</p>
      <h1>上传源视频并开始本地处理</h1>
      <p class="publish-shell__lead">
        选择视频文件，填写标题和可选说明，系统会创建上传任务并异步转码为 HLS。
      </p>
    </section>

    <section class="publish-shell__panel">
      <form class="publish-form" @submit.prevent="handleSubmit">
        <div class="publish-form__field-group">
          <label class="publish-form__field">
            <span>视频文件</span>
            <input type="file" accept="video/*" @change="handleFileChange" required />
          </label>
          <p v-if="selectedFileName" class="publish-form__hint">
            已选择：<strong>{{ selectedFileName }}</strong>
          </p>
        </div>

        <label class="publish-form__field">
          <span>标题</span>
          <input
            v-model="title"
            type="text"
            name="title"
            maxlength="120"
            placeholder="为这段视频写一个清晰标题"
            required
          />
        </label>

        <label class="publish-form__field">
          <span>说明</span>
          <textarea
            v-model="caption"
            name="caption"
            rows="4"
            maxlength="500"
            placeholder="可选，补充这段视频的简介"
          />
        </label>

        <p v-if="errorMessage" class="publish-form__error" role="alert">
          {{ errorMessage }}
        </p>

        <button class="publish-form__submit" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? "上传中..." : "创建上传任务" }}
        </button>
      </form>

      <article v-if="latestUpload" class="publish-result">
        <p class="publish-result__eyebrow">最近提交</p>
        <h2>上传请求已接收</h2>
        <dl>
          <div>
            <dt>视频 ID</dt>
            <dd>{{ latestUpload.video_id }}</dd>
          </div>
          <div>
            <dt>上传任务 ID</dt>
            <dd>{{ latestUpload.upload_job_id }}</dd>
          </div>
          <div>
            <dt>初始状态</dt>
            <dd>{{ formatUploadStatus(latestUpload.status) }}</dd>
          </div>
        </dl>
      </article>

      <article v-if="latestStatus" class="publish-status" :data-status="latestStatus.status">
        <p class="publish-result__eyebrow">处理状态</p>
        <h2>{{ statusHeading }}</h2>
        <p>{{ statusDetail }}</p>

        <div
          v-if="statusRefreshErrorMessage && !isTerminalStatus(latestStatus.status)"
          class="publish-status__refresh-error"
          role="alert"
        >
          <p>{{ statusRefreshErrorMessage }}</p>
          <button type="button" @click="handleRetryStatusRefresh">重新检查状态</button>
        </div>

        <dl class="publish-status__meta">
          <div>
            <dt>当前状态</dt>
            <dd>{{ formatUploadStatus(latestStatus.status) }}</dd>
          </div>
          <div v-if="latestStatus.hls_manifest_url">
            <dt>HLS 清单</dt>
            <dd>{{ latestStatus.hls_manifest_url }}</dd>
          </div>
          <div v-if="latestStatus.cover_image_url">
            <dt>封面图</dt>
            <dd>{{ latestStatus.cover_image_url }}</dd>
          </div>
          <div v-if="latestStatus.failure_message">
            <dt>失败原因</dt>
            <dd>{{ latestStatus.failure_message }}</dd>
          </div>
        </dl>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { ApiError } from "@/lib/api";
import {
  createVideoUpload,
  requestVideoUploadStatus,
  type VideoUploadAcceptedResponse,
  type VideoUploadStatusResponse,
} from "@/lib/videos";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
const POLL_INTERVAL_MS = 1500;

const selectedFile = ref<File | null>(null);
const title = ref("");
const caption = ref("");
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const statusRefreshErrorMessage = ref<string | null>(null);
const latestUpload = ref<VideoUploadAcceptedResponse | null>(null);
const latestStatus = ref<VideoUploadStatusResponse | null>(null);

const selectedFileName = computed(() => selectedFile.value?.name ?? null);
let pollingHandle: number | null = null;

function formatUploadStatus(status: VideoUploadStatusResponse["status"]): string {
  switch (status) {
    case "ready":
      return "已就绪";
    case "failed":
      return "处理失败";
    case "processing":
      return "处理中";
    default:
      return "排队中";
  }
}

const statusHeading = computed(() => {
  switch (latestStatus.value?.status) {
    case "ready":
      return "播放资源已就绪";
    case "failed":
      return "处理失败";
    case "processing":
      return "正在转码";
    default:
      return "上传任务已排队";
  }
});

const statusDetail = computed(() => {
  switch (latestStatus.value?.status) {
    case "ready":
      return "后端已完成 HLS 和封面生成，这段视频可以进入播放链路。";
    case "failed":
      return latestStatus.value.failure_message ?? "后端未能完成处理。";
    case "processing":
      return "源视频正在转码为 HLS，并生成封面资源。";
    default:
      return "上传请求已接收，正在等待后端开始处理。";
  }
});

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
}

function clearPolling() {
  if (pollingHandle !== null) {
    window.clearTimeout(pollingHandle);
    pollingHandle = null;
  }
}

function isTerminalStatus(status: VideoUploadStatusResponse["status"]): boolean {
  return status === "ready" || status === "failed";
}

async function refreshUploadStatus(uploadJobId: number) {
  if (!authStore.accessToken) {
    return;
  }

  try {
    latestStatus.value = await requestVideoUploadStatus(authStore.accessToken, uploadJobId);
    statusRefreshErrorMessage.value = null;
  } catch (error) {
    statusRefreshErrorMessage.value =
      error instanceof ApiError ? error.message : "无法刷新上传状态。";
    clearPolling();
    return;
  }

  if (!latestStatus.value || isTerminalStatus(latestStatus.value.status)) {
    clearPolling();
    return;
  }

  pollingHandle = window.setTimeout(() => {
    void refreshUploadStatus(uploadJobId);
  }, POLL_INTERVAL_MS);
}

async function handleSubmit() {
  errorMessage.value = null;
  statusRefreshErrorMessage.value = null;

  if (!authStore.accessToken) {
    errorMessage.value = "请先登录，再创建上传任务。";
    return;
  }

  if (!selectedFile.value) {
    errorMessage.value = "请选择一个视频文件。";
    return;
  }

  if (!title.value.trim()) {
    errorMessage.value = "请填写视频标题。";
    return;
  }

  isSubmitting.value = true;
  try {
    clearPolling();
    latestUpload.value = await createVideoUpload(authStore.accessToken, {
      title: title.value.trim(),
      caption: caption.value,
      videoFile: selectedFile.value,
    });
    latestStatus.value = {
      upload_job_id: latestUpload.value.upload_job_id,
      video_id: latestUpload.value.video_id,
      status: latestUpload.value.status,
      failure_message: null,
      hls_manifest_url: null,
      cover_image_url: null,
    };
    if (!isTerminalStatus(latestStatus.value.status)) {
      void refreshUploadStatus(latestStatus.value.upload_job_id);
    }
  } catch (error) {
    errorMessage.value =
      error instanceof ApiError ? error.message : "无法创建上传任务。";
  } finally {
    isSubmitting.value = false;
  }
}

function handleRetryStatusRefresh() {
  if (!latestStatus.value) {
    return;
  }

  statusRefreshErrorMessage.value = null;
  void refreshUploadStatus(latestStatus.value.upload_job_id);
}

onBeforeUnmount(() => {
  clearPolling();
});
</script>
