import { useState } from "react";
import Link from "next/link";
import { searchVideos, formatTimestamp } from "@/lib/api";

export default function Search() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("semantic");
  const [results, setResults] = useState<ReturnType<typeof searchVideos> extends Promise<infer T> ? T : never>([]);
  const [searching, setSearching] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const data = await searchVideos(query, mode);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div>
      <h1>Semantic Search</h1>
      <p className="subtitle">Find exact timestamps — e.g. &quot;where does the speaker explain Kubernetes?&quot;</p>

      <form onSubmit={handleSearch} className="search-form">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search transcripts..."
          className="search-input"
        />
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="semantic">Semantic</option>
          <option value="keyword">Keyword</option>
          <option value="hybrid">Hybrid</option>
        </select>
        <button type="submit" disabled={searching}>
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      <div className="results">
        {results.map((r, i) => (
          <div key={i} className="result-card">
            <div className="result-meta">
              <Link href={`/video/${r.video_id}?t=${r.start_time}`}>
                Jump to {formatTimestamp(r.start_time)}
              </Link>
              <span className="score">{Math.round(r.score * 100)}% match</span>
            </div>
            <p>{r.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
