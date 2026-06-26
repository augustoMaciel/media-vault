import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import type { Media, MediaVersion, UploadMeta } from "../types";
import {
  listMedia,
  uploadMedia,
  listVersions,
  uploadVersion,
  downloadVersion,
  updateVersionDescription,
  updateMediaTitle,
  deleteMedia,
  deleteVersion,
} from "../api/media";
import UploadForm from "../components/UploadForm";
import SearchPanel from "../components/SearchPanel";
import VersionsPanel from "../components/VersionsPanel";
import DetailPanel from "../components/DetailPanel";

function errMsg(e: unknown, fallback: string): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { message?: string } | undefined;
    if (d?.message) return d.message;
  }
  return fallback;
}

export default function Vault() {
  const { user, logout } = useAuth();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Media[]>([]);
  const [searching, setSearching] = useState(true);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [selectedMedia, setSelectedMedia] = useState<Media | null>(null);
  const [versions, setVersions] = useState<MediaVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<MediaVersion | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const runSearch = useCallback(async (q: string) => {
    setSearching(true);
    setSearchError(null);
    try {
      setResults(await listMedia(q.trim() || undefined));
    } catch (e) {
      setSearchError(errMsg(e, "Search failed."));
    } finally {
      setSearching(false);
    }
  }, []);

  // Initial load: show all media (most recent versions).
  useEffect(() => {
    runSearch("");
  }, [runSearch]);

  const loadVersions = useCallback(async (media: Media, keepVersionNo?: number) => {
    setVersionsLoading(true);
    try {
      const vs = await listVersions(media.id);
      setVersions(vs);
      // Keep the requested version selected (e.g. after an edit); else the current one.
      const keep = keepVersionNo != null ? vs.find((v) => v.versionNo === keepVersionNo) : undefined;
      setSelectedVersion(keep ?? vs.find((v) => v.isCurrent) ?? vs[0] ?? null);
    } catch {
      setVersions([]);
      setSelectedVersion(null);
    } finally {
      setVersionsLoading(false);
    }
  }, []);

  const selectMedia = useCallback(
    (m: Media) => {
      setSelectedMedia(m);
      setSelectedVersion(null);
      loadVersions(m);
    },
    [loadVersions]
  );

  const handleUpload = useCallback(
    async (file: File, meta: UploadMeta, onProgress?: (p: number) => void) => {
      const created = await uploadMedia(file, meta, onProgress);
      await runSearch(query); // refresh results
      selectMedia(created); // focus the new file
    },
    [runSearch, query, selectMedia]
  );

  const handleUploadVersion = useCallback(async () => {
    if (!selectedMedia) return;
    const updated = await uploadVersion(selectedMedia.id);
    setSelectedMedia(updated);
    await loadVersions(updated); // reload list + auto-select new current
    await runSearch(query); // current snapshot changed in results
  }, [selectedMedia, loadVersions, runSearch, query]);

  const handleUpdateVersionDescription = useCallback(
    async (versionNo: number, description: string) => {
      if (!selectedMedia) return;
      await updateVersionDescription(selectedMedia.id, versionNo, description);
      await loadVersions(selectedMedia, versionNo); // keep the edited version selected
      await runSearch(query); // current description may have changed
    },
    [selectedMedia, loadVersions, runSearch, query]
  );

  const handleDeleteFile = useCallback(async () => {
    if (!selectedMedia) return;
    setDetailError(null);
    try {
      await deleteMedia(selectedMedia.id);
      setSelectedMedia(null);
      setVersions([]);
      setSelectedVersion(null);
      await runSearch(query);
    } catch {
      setDetailError("Couldn't delete the file.");
    }
  }, [selectedMedia, runSearch, query]);

  const handleDeleteVersion = useCallback(async () => {
    if (!selectedMedia || !selectedVersion) return;
    setDetailError(null);
    try {
      const res = await deleteVersion(selectedMedia.id, selectedVersion.versionNo);
      if (res.mediaDeleted) {
        setSelectedMedia(null);
        setVersions([]);
        setSelectedVersion(null);
      } else {
        setVersions(res.versions);
        setSelectedVersion(res.versions.find((v) => v.isCurrent) ?? res.versions[0] ?? null);
      }
      await runSearch(query);
    } catch {
      setDetailError("Couldn't delete the version.");
    }
  }, [selectedMedia, selectedVersion, runSearch, query]);

  const handleRenameFile = useCallback(
    async (id: string, title: string) => {
      const updated = await updateMediaTitle(id, title);
      setSelectedMedia((m) => (m && m.id === id ? updated : m));
      await runSearch(query);
    },
    [runSearch, query]
  );

  const handleDownload = useCallback(async () => {
    if (!selectedMedia || !selectedVersion) return;
    setDetailError(null);
    try {
      await downloadVersion(selectedMedia.id, selectedVersion.versionNo, selectedVersion.originalName);
    } catch {
      setDetailError("Download failed. Please try again.");
    }
  }, [selectedMedia, selectedVersion]);

  return (
    <div className="vault">
      <header className="vault-header">
        <h1>My Media</h1>
        <div className="user">
          <span>{user?.email}</span>
          <button onClick={logout}>Log out</button>
        </div>
      </header>

      <UploadForm onUpload={handleUpload} />

      <div className="vault-panels">
        <VersionsPanel
          mediaId={selectedMedia?.id ?? null}
          versions={versions}
          selectedVersionNo={selectedVersion?.versionNo ?? null}
          onSelectVersion={setSelectedVersion}
          onUploadVersion={handleUploadVersion}
          onUpdateDescription={handleUpdateVersionDescription}
          loading={versionsLoading}
        />
        <DetailPanel
          media={selectedMedia}
          version={selectedVersion}
          error={detailError}
          onDownload={handleDownload}
          onDeleteFile={handleDeleteFile}
          onDeleteVersion={handleDeleteVersion}
        />
        <SearchPanel
          query={query}
          onQueryChange={setQuery}
          onSearch={() => runSearch(query)}
          results={results}
          loading={searching}
          error={searchError}
          selectedId={selectedMedia?.id ?? null}
          onSelect={selectMedia}
          onRenameFile={handleRenameFile}
        />
      </div>
    </div>
  );
}
