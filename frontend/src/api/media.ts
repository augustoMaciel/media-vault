import api from "./client";
import type { Media, MediaVersion, UploadMeta } from "../types";

interface RawMedia {
  id: string;
  title: string | null;
  description: string | null;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  has_thumbnail: boolean;
}

const mapMedia = (m: RawMedia): Media => ({
  id: m.id,
  title: m.title,
  description: m.description,
  originalName: m.original_name,
  mimeType: m.mime_type,
  sizeBytes: m.size_bytes,
  uploadedAt: m.uploaded_at,
  hasThumbnail: m.has_thumbnail,
});

export type { UploadMeta };

export async function listMedia(q?: string): Promise<Media[]> {
  const { data } = await api.get<RawMedia[]>("/media", { params: q ? { q } : {} });
  return data.map(mapMedia);
}

export async function uploadMedia(
  file: File,
  meta: UploadMeta,
  onProgress?: (percent: number) => void
): Promise<Media> {
  const form = new FormData();
  form.append("file", file);
  if (meta.title) form.append("title", meta.title);
  if (meta.description) form.append("description", meta.description);

  const { data } = await api.post<RawMedia>("/media", form, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
  return mapMedia(data);
}

// Trigger a browser "Save as" for a blob.
function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Authenticated blob download -> triggers a browser "Save as" with the real name.
export async function downloadMedia(id: string, filename: string): Promise<void> {
  const { data } = await api.get(`/media/${id}/download`, { responseType: "blob" });
  saveBlob(data as Blob, filename);
}

export interface DownloadLink {
  url: string;
  expiresIn: number;
}

// Expiring presigned link (bonus): a temporary URL the user can copy/share.
export async function getDownloadLink(id: string): Promise<DownloadLink> {
  const { data } = await api.get<{ url: string; expires_in: number }>(`/media/${id}/link`);
  return { url: data.url, expiresIn: data.expires_in };
}

// Thumbnail route is JWT-protected, so fetch as a blob and return an object URL
// (the caller must revoke it when done).
export async function fetchThumbnailUrl(id: string): Promise<string> {
  const { data } = await api.get(`/media/${id}/thumbnail`, { responseType: "blob" });
  return URL.createObjectURL(data as Blob);
}

// Per-version thumbnail (JWT-protected) -> object URL; caller revokes it.
export async function fetchVersionThumbnailUrl(
  id: string,
  versionNo: number
): Promise<string> {
  const { data } = await api.get(`/media/${id}/versions/${versionNo}/thumbnail`, {
    responseType: "blob",
  });
  return URL.createObjectURL(data as Blob);
}

export async function deleteMedia(id: string): Promise<void> {
  await api.delete(`/media/${id}`);
}

// --- Versioning ---------------------------------------------------------------

interface RawVersion {
  version_no: number;
  original_name: string;
  description: string | null;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  has_thumbnail: boolean;
  is_current: boolean;
}

const mapVersion = (v: RawVersion): MediaVersion => ({
  versionNo: v.version_no,
  originalName: v.original_name,
  description: v.description,
  mimeType: v.mime_type,
  sizeBytes: v.size_bytes,
  uploadedAt: v.uploaded_at,
  hasThumbnail: v.has_thumbnail,
  isCurrent: v.is_current,
});

export async function listVersions(id: string): Promise<MediaVersion[]> {
  const { data } = await api.get<RawVersion[]>(`/media/${id}/versions`);
  return data.map(mapVersion);
}

export async function uploadVersion(
  id: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<Media> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<RawMedia>(`/media/${id}/versions`, form, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
  return mapMedia(data);
}

export async function downloadVersion(
  id: string,
  versionNo: number,
  filename: string
): Promise<void> {
  const { data } = await api.get(`/media/${id}/versions/${versionNo}/download`, {
    responseType: "blob",
  });
  saveBlob(data as Blob, filename);
}

export async function updateVersionDescription(
  id: string,
  versionNo: number,
  description: string
): Promise<MediaVersion> {
  const { data } = await api.patch<RawVersion>(`/media/${id}/versions/${versionNo}`, { description });
  return mapVersion(data);
}

export interface VersionDeleteResult {
  mediaDeleted: boolean;
  versions: MediaVersion[];
}

export async function deleteVersion(id: string, versionNo: number): Promise<VersionDeleteResult> {
  const { data } = await api.delete<{ media_deleted: boolean; versions?: RawVersion[] }>(
    `/media/${id}/versions/${versionNo}`
  );
  return { mediaDeleted: data.media_deleted, versions: (data.versions ?? []).map(mapVersion) };
}
