import { useEffect, useState } from "react";
import { fetchThumbnailUrl, fetchVersionThumbnailUrl } from "../api/media";

interface Props {
  mediaId: string;
  versionNo?: number; // when set, loads that version's thumbnail
  hasThumbnail: boolean;
  mimeType: string;
}

function typeIcon(mime: string): string {
  if (mime.startsWith("image/")) return "🖼️";
  if (mime === "application/pdf") return "📄";
  if (mime.startsWith("text/")) return "📝";
  return "📁";
}

export default function Thumb({ mediaId, versionNo, hasThumbnail, mimeType }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  // Load the (auth-protected) thumbnail as an object URL; revoke on unmount.
  useEffect(() => {
    if (!hasThumbnail) return;
    let active = true;
    let created: string | null = null;
    const fetcher =
      versionNo === undefined
        ? fetchThumbnailUrl(mediaId)
        : fetchVersionThumbnailUrl(mediaId, versionNo);
    fetcher
      .then((u) => {
        if (active) {
          created = u;
          setUrl(u);
        } else {
          URL.revokeObjectURL(u);
        }
      })
      .catch(() => setFailed(true));
    return () => {
      active = false;
      if (created) URL.revokeObjectURL(created);
    };
  }, [mediaId, versionNo, hasThumbnail]);

  const show = hasThumbnail && url && !failed;
  return (
    <div className="thumb">
      {show ? (
        <img src={url} alt="" onError={() => setFailed(true)} />
      ) : (
        <span className="icon">{typeIcon(mimeType)}</span>
      )}
    </div>
  );
}
