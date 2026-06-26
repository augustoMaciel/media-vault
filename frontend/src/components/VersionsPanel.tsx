import { useEffect, useState } from "react";
import type { MediaVersion } from "../types";
import Thumb from "./Thumb";

interface Props {
  mediaId: string | null;
  versions: MediaVersion[];
  selectedVersionNo: number | null;
  onSelectVersion: (v: MediaVersion) => void;
  onUploadVersion: () => Promise<void>;
  onUpdateDescription: (versionNo: number, description: string) => Promise<void>;
  loading: boolean;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const u = ["KB", "MB", "GB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${u[i]}`;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function VersionsPanel({
  mediaId,
  versions,
  selectedVersionNo,
  onSelectVersion,
  onUploadVersion,
  onUpdateDescription,
  loading,
}: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [descDraft, setDescDraft] = useState("");
  const [savingDesc, setSavingDesc] = useState(false);

  const selected = versions.find((v) => v.versionNo === selectedVersionNo) ?? null;

  // Prefill the editor when the selected version (or its saved text) changes.
  useEffect(() => {
    setDescDraft(selected?.description ?? "");
  }, [selectedVersionNo, selected?.description]);

  if (!mediaId) {
    return (
      <aside className="panel versions-panel">
        <h2 className="panel-title">Versions</h2>
        <p className="sub">Select a file to see its versions.</p>
      </aside>
    );
  }

  const handleNewVersion = async () => {
    setUploading(true);
    setError(null);
    try {
      await onUploadVersion();
    } catch {
      setError("Couldn't add a version.");
    } finally {
      setUploading(false);
    }
  };

  const saveDescription = async () => {
    if (selectedVersionNo === null) return;
    setSavingDesc(true);
    setError(null);
    try {
      await onUpdateDescription(selectedVersionNo, descDraft.trim());
    } catch {
      setError("Couldn't save description.");
    } finally {
      setSavingDesc(false);
    }
  };

  return (
    <aside className="panel versions-panel">
      <h2 className="panel-title">Versions</h2>
      {loading && <p className="sub">Loading…</p>}

      <ul className="version-list">
        {versions.map((v) => (
          <li
            key={v.versionNo}
            className={v.versionNo === selectedVersionNo ? "selected" : ""}
            onClick={() => onSelectVersion(v)}
          >
            <Thumb
              mediaId={mediaId}
              versionNo={v.versionNo}
              hasThumbnail={v.hasThumbnail}
              mimeType={v.mimeType}
            />
            <div className="version-meta">
              <strong>
                v{v.versionNo}
                {v.isCurrent && <span className="badge"> current</span>}
              </strong>
              <span className="sub">{v.originalName}</span>
              <span className="sub">
                {fmtSize(v.sizeBytes)} · {fmtDate(v.uploadedAt)}
              </span>
            </div>
          </li>
        ))}
      </ul>

      <div className="version-actions">
        <button type="button" className="new-version" disabled={uploading} onClick={handleNewVersion}>
          {uploading ? "Adding…" : "+ New version"}
        </button>
        <button type="button" disabled={selectedVersionNo === null || savingDesc} onClick={saveDescription}>
          {savingDesc ? "Saving…" : "Save description"}
        </button>
      </div>
      <textarea
        className="desc-input version-desc"
        rows={3}
        placeholder={
          selectedVersionNo === null ? "Select a version to edit its description" : "Version description"
        }
        value={descDraft}
        disabled={selectedVersionNo === null || savingDesc}
        onChange={(e) => setDescDraft(e.target.value)}
      />
      {error && <p className="error">{error}</p>}
    </aside>
  );
}
