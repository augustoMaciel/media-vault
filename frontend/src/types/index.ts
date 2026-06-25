// Frontend-facing models. The backend speaks snake_case; the api/ layer maps
// responses into these camelCase shapes so components stay clean.

export interface User {
  id: number;
  email: string;
  createdAt: string;
}

export interface Media {
  id: string;
  title: string | null;
  description: string | null;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  uploadedAt: string;
  hasThumbnail: boolean;
}

export interface AuthResponse {
  accessToken: string;
  user: User;
}

export interface MediaVersion {
  versionNo: number;
  originalName: string;
  description: string | null;
  mimeType: string;
  sizeBytes: number;
  uploadedAt: string;
  hasThumbnail: boolean;
  isCurrent: boolean;
}

export interface UploadMeta {
  title?: string;
  description?: string;
}
