import { buildApiUrl, requestJson, resolveBackendUrl } from "@/lib/api";

export type VideoUploadJobStatus = "pending" | "processing" | "ready" | "failed";
export type AdminVideoVisibility = "public" | "hidden";

export interface FeedCreatorSummary {
  id: number;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface AdminVideoCreatorSummary {
  id: number;
  email: string;
  username: string;
  display_name: string;
}

export interface AdminVideoListItem {
  id: number;
  title: string;
  caption: string | null;
  creator: AdminVideoCreatorSummary;
  visibility: AdminVideoVisibility;
  latest_upload_job_id: number | null;
  latest_upload_status: VideoUploadJobStatus | null;
  failure_message: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminVideoListResponse {
  items: AdminVideoListItem[];
  page: number;
  page_size: number;
  has_more: boolean;
  total_items: number;
}

export interface AdminVideoInventoryFilters {
  page?: number;
  pageSize?: number;
  q?: string;
  status?: VideoUploadJobStatus;
  visibility?: AdminVideoVisibility;
}

export interface AdminVideoVisibilityUpdateResponse {
  video_id: number;
  visibility: AdminVideoVisibility;
}

export interface FeedVideoItem {
  id: number;
  title: string;
  caption: string | null;
  hls_manifest_url: string;
  cover_image_url: string;
  creator: FeedCreatorSummary;
}

export interface VideoFeedResponse {
  items: FeedVideoItem[];
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface VideoPlaybackStartResponse {
  video_id: number;
  view_count: number;
}

export interface CreateVideoUploadPayload {
  title: string;
  caption?: string;
  videoFile: File;
}

export interface VideoUploadAcceptedResponse {
  video_id: number;
  upload_job_id: number;
  status: VideoUploadJobStatus;
}

export interface VideoUploadStatusResponse {
  upload_job_id: number;
  video_id: number;
  status: VideoUploadJobStatus;
  failure_message: string | null;
  hls_manifest_url: string | null;
  cover_image_url: string | null;
}

const VIDEO_UPLOADS_PATH = "/api/videos/uploads";
const VIDEO_FEED_PATH = "/api/videos/feed";
const ADMIN_VIDEOS_PATH = "/api/videos/admin";

function normalizeFeedVideoItem(item: FeedVideoItem): FeedVideoItem {
  return {
    ...item,
    hls_manifest_url: resolveBackendUrl(item.hls_manifest_url),
    cover_image_url: resolveBackendUrl(item.cover_image_url),
    creator: {
      ...item.creator,
      avatar_url: item.creator.avatar_url ? resolveBackendUrl(item.creator.avatar_url) : null,
    },
  };
}

function normalizeVideoUploadStatusResponse(
  response: VideoUploadStatusResponse,
): VideoUploadStatusResponse {
  return {
    ...response,
    hls_manifest_url: response.hls_manifest_url
      ? resolveBackendUrl(response.hls_manifest_url)
      : null,
    cover_image_url: response.cover_image_url ? resolveBackendUrl(response.cover_image_url) : null,
  };
}

export function getVideoUploadCreateEndpoint(): string {
  return buildApiUrl(VIDEO_UPLOADS_PATH);
}

export function getVideoUploadStatusEndpoint(uploadJobId: number): string {
  return buildApiUrl(`${VIDEO_UPLOADS_PATH}/${uploadJobId}`);
}

export function getVideoFeedEndpoint(page = 1, pageSize = 5): string {
  return buildApiUrl(`${VIDEO_FEED_PATH}?page=${page}&page_size=${pageSize}`);
}

export function getAdminVideoInventoryEndpoint(
  filters: AdminVideoInventoryFilters = {},
): string {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(filters.page ?? 1));
  searchParams.set("page_size", String(filters.pageSize ?? 20));

  if (filters.q) {
    searchParams.set("q", filters.q);
  }

  if (filters.status) {
    searchParams.set("status", filters.status);
  }

  if (filters.visibility) {
    searchParams.set("visibility", filters.visibility);
  }

  return buildApiUrl(`${ADMIN_VIDEOS_PATH}?${searchParams.toString()}`);
}

export function getVideoPlaybackStartEndpoint(videoId: number): string {
  return buildApiUrl(`/api/videos/${videoId}/playbacks`);
}

export async function createVideoUpload(
  accessToken: string,
  payload: CreateVideoUploadPayload,
): Promise<VideoUploadAcceptedResponse> {
  const formData = new FormData();
  formData.set("title", payload.title);
  formData.set("video_file", payload.videoFile);

  if (payload.caption && payload.caption.trim()) {
    formData.set("caption", payload.caption.trim());
  }

  const response = await requestJson<VideoUploadAcceptedResponse>(VIDEO_UPLOADS_PATH, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });

  if (!response.payload) {
    throw new Error("Video upload response did not include a payload.");
  }

  return response.payload;
}

export async function requestVideoUploadStatus(
  accessToken: string,
  uploadJobId: number,
): Promise<VideoUploadStatusResponse> {
  const response = await requestJson<VideoUploadStatusResponse>(
    `${VIDEO_UPLOADS_PATH}/${uploadJobId}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  if (!response.payload) {
    throw new Error("Video upload-status response did not include a payload.");
  }

  return normalizeVideoUploadStatusResponse(response.payload);
}

export async function requestVideoFeed(
  accessToken: string,
  page = 1,
  pageSize = 5,
): Promise<VideoFeedResponse> {
  const response = await requestJson<VideoFeedResponse>(
    `${VIDEO_FEED_PATH}?page=${page}&page_size=${pageSize}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  if (!response.payload) {
    throw new Error("Video feed response did not include a payload.");
  }

  return {
    ...response.payload,
    items: response.payload.items.map(normalizeFeedVideoItem),
  };
}

export async function reportVideoPlaybackStart(
  accessToken: string,
  videoId: number,
): Promise<VideoPlaybackStartResponse> {
  const response = await requestJson<VideoPlaybackStartResponse>(`/api/videos/${videoId}/playbacks`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.payload) {
    throw new Error("Playback-start response did not include a payload.");
  }

  return response.payload;
}

export async function requestAdminVideoInventory(
  accessToken: string,
  filters: AdminVideoInventoryFilters = {},
): Promise<AdminVideoListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(filters.page ?? 1));
  searchParams.set("page_size", String(filters.pageSize ?? 20));

  if (filters.q) {
    searchParams.set("q", filters.q);
  }

  if (filters.status) {
    searchParams.set("status", filters.status);
  }

  if (filters.visibility) {
    searchParams.set("visibility", filters.visibility);
  }

  const response = await requestJson<AdminVideoListResponse>(
    `${ADMIN_VIDEOS_PATH}?${searchParams.toString()}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  if (!response.payload) {
    throw new Error("Admin video inventory response did not include a payload.");
  }

  return response.payload;
}

export async function updateAdminVideoVisibility(
  accessToken: string,
  videoId: number,
  visibility: AdminVideoVisibility,
): Promise<AdminVideoVisibilityUpdateResponse> {
  const response = await requestJson<AdminVideoVisibilityUpdateResponse>(
    `${ADMIN_VIDEOS_PATH}/${videoId}/visibility`,
    {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ visibility }),
    },
  );

  if (!response.payload) {
    throw new Error("Admin video visibility update did not include a payload.");
  }

  return response.payload;
}
