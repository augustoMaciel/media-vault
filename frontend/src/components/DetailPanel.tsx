import type { Media, MediaVersion } from "../types";
import Thumb from "./Thumb";

interface Props {
  media: Media | null;
  version: MediaVersion | null;
  error: string | null;
  onDownload: () => void;
  onDeleteFile: () => void;
  onDeleteVersion: () => void;
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

export default function DetailPanel({
  media,
  version,
  error,
  onDownload,
  onDeleteFile,
  onDeleteVersion,
}: Props) {
  if (!media || !version) {
    return (
      <section className="panel detail-panel">
        <p className="sub detail-empty">Select a file, then a version, to see details here.</p>
      </section>
    );
  }

  const confirmDeleteFile = () => {
    if (window.confirm(`Delete "${media.title || version.originalName}" and all its versions?`)) {
      onDeleteFile();
    }
  };

  const confirmDeleteVersion = () => {
    if (window.confirm(`Delete v${version.versionNo}?`)) {
      onDeleteVersion();
    }
  };

  return (
    <section className="panel detail-panel">
      <div className="detail-body">
        <Thumb
          mediaId={media.id}
          versionNo={version.versionNo}
          hasThumbnail={version.hasThumbnail}
          mimeType={version.mimeType}
        />
        <h2 className="detail-title">{media.title || version.originalName}</h2>
        <dl className="detail-info">
          <div>
            <dt>Version</dt>
            <dd>
              v{version.versionNo}
              {version.isCurrent ? " (current)" : ""}
            </dd>
          </div>
          <div>
            <dt>File</dt>
            <dd>{version.originalName}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{version.mimeType}</dd>
          </div>
          <div>
            <dt>Size</dt>
            <dd>{fmtSize(version.sizeBytes)}</dd>
          </div>
          <div>
            <dt>Uploaded</dt>
            <dd>{fmtDate(version.uploadedAt)}</dd>
          </div>
          {version.description && (
            <div>
              <dt>Description</dt>
              <dd>{version.description}</dd>
            </div>
          )}
        </dl>
      </div>

      {error && <p className="error">{error}</p>}
      <div className="detail-actions">
        <button className="danger" onClick={confirmDeleteFile}>Delete file</button>
        <button className="danger" onClick={confirmDeleteVersion}>Delete version</button>
        <button className="download-btn" onClick={onDownload}>Download</button>
      </div>
    </section>
  );
}
