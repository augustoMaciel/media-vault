import type { Media } from "../types";
import Thumb from "./Thumb";

interface Props {
  query: string;
  onQueryChange: (q: string) => void;
  onSearch: () => void;
  results: Media[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  onSelect: (m: Media) => void;
}

export default function SearchPanel({
  query,
  onQueryChange,
  onSearch,
  results,
  loading,
  error,
  selectedId,
  onSelect,
}: Props) {
  return (
    <aside className="panel search-panel">
      <h2 className="panel-title">Search</h2>

      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault();
          onSearch();
        }}
      >
        <input
          type="search"
          placeholder="Search my media…"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
        />
        <button type="submit">Search</button>
      </form>

      {loading && <p className="sub">Searching…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && results.length === 0 && <p className="sub">No files found.</p>}

      <ul className="result-list">
        {results.map((m) => (
          <li
            key={m.id}
            className={m.id === selectedId ? "selected" : ""}
            onClick={() => onSelect(m)}
          >
            <Thumb mediaId={m.id} hasThumbnail={m.hasThumbnail} mimeType={m.mimeType} />
            <div className="result-meta">
              <strong>{m.title || m.originalName}</strong>
              <span className="sub">{m.originalName}</span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
