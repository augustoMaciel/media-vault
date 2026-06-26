import { useState, useEffect, type FormEvent } from "react";
import axios from "axios";
import type { UploadMeta } from "../api/media";

const ALLOWED_EXT = ["png", "jpg", "jpeg", "pdf", "txt"];
const MAX_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB) || 10;
const MAX_BYTES = MAX_MB * 1024 * 1024;

interface Props {
  onUpload: (file: File, meta: UploadMeta, onProgress?: (p: number) => void) => Promise<unknown>;
}

function serverError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { message?: string; messages?: Record<string, string[]> } | undefined;
    if (d?.message) return d.message;
    if (d?.messages) {
      const first = Object.values(d.messages)[0];
      if (Array.isArray(first)) return String(first[0]);
    }
  }
  return "Upload failed.";
}

export default function UploadForm({ onUpload }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [errorDetail, setErrorDetail] = useState("");
  const [progress, setProgress] = useState(0);
  const [inputKey, setInputKey] = useState(0); // bump to clear the file input

  // Success auto-clears after 5s; errors persist until the next attempt.
  useEffect(() => {
    if (status !== "success") return;
    const t = setTimeout(() => setStatus("idle"), 5000);
    return () => clearTimeout(t);
  }, [status]);

  const pickFile = (f: File | null) => {
    setStatus("idle");
    setErrorDetail("");
    if (!f) {
      setFile(null);
      return;
    }
    const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXT.includes(ext)) {
      setStatus("error");
      setErrorDetail("Allowed types: png, jpg, jpeg, pdf, txt.");
      setFile(null);
      return;
    }
    if (f.size > MAX_BYTES) {
      setStatus("error");
      setErrorDetail(`File exceeds the ${MAX_MB} MB limit.`);
      setFile(null);
      return;
    }
    setFile(f);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setStatus("uploading");
    setErrorDetail("");
    setProgress(0);
    try {
      await onUpload(
        file,
        { title: title.trim() || undefined, description: description.trim() || undefined },
        setProgress
      );
      setStatus("success");
      setFile(null);
      setTitle("");
      setDescription("");
      setInputKey((k) => k + 1);
    } catch (err) {
      setStatus("error");
      setErrorDetail(serverError(err));
    }
  };

  const busy = status === "uploading";
  const canSubmit = !busy && !!file;

  const msgClass =
    status === "success" ? "upload-msg success"
    : status === "error" ? "upload-msg error"
    : status === "uploading" ? "upload-msg busy"
    : "upload-msg";
  const msgText =
    status === "success" ? "Uploaded!"
    : status === "error" ? "Error!"
    : status === "uploading" ? `Uploading… ${progress}%`
    : "";

  return (
    <form className="upload-form" onSubmit={submit}>
      <div className="upload-row">
        <label className="browse-btn">
          Browse
          <input
            key={inputKey}
            type="file"
            accept=".png,.jpg,.jpeg,.pdf,.txt"
            disabled={busy}
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            style={{ display: "none" }}
          />
        </label>
        <span className="filename" title={file?.name}>
          {file ? file.name : "No file selected"}
        </span>
        <input
          className="title-input"
          type="text"
          placeholder="Title (optional)"
          value={title}
          disabled={busy}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button type="submit" disabled={!canSubmit}>Upload</button>
        <span className="upload-msg-slot">
          <span className={msgClass} title={status === "error" ? errorDetail : undefined}>
            {msgText}
          </span>
        </span>
      </div>
      <textarea
        className="desc-input"
        rows={3}
        placeholder="Description (optional)"
        value={description}
        disabled={busy}
        onChange={(e) => setDescription(e.target.value)}
      />
    </form>
  );
}
