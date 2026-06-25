import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchVideos, fetchRecommendations, Video, formatTimestamp } from "@/lib/api";

export default function Home() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [recs, setRecs] = useState<{ video_id: string; title: string; score: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchVideos(), fetchRecommendations()])
      .then(([v, r]) => { setVideos(v); setRecs(r); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="loading">Loading...</p>;

  return (
    <div>
      <h1>AI Video Intelligence Platform</h1>
      <p className="subtitle">Upload, transcribe, search by timestamp, and get AI summaries</p>

      {recs.length > 0 && (
        <section className="section">
          <h2>Recommended</h2>
          <div className="grid">
            {recs.map((r) => (
              <Link key={r.video_id} href={`/video/${r.video_id}`} className="card">
                <div className="thumb-placeholder">▶</div>
                <h3>{r.title}</h3>
                <span className="badge">{Math.round(r.score * 100)}% match</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <h2>All Videos</h2>
        {videos.length === 0 ? (
          <p>No videos yet. <Link href="/upload">Upload your first video</Link></p>
        ) : (
          <div className="grid">
            {videos.map((v) => (
              <Link key={v.id} href={`/video/${v.id}`} className="card">
                {v.thumbnail_url ? (
                  <img src={v.thumbnail_url} alt={v.title} className="thumb" />
                ) : (
                  <div className="thumb-placeholder">▶</div>
                )}
                <h3>{v.title}</h3>
                <span className={`status status-${v.status}`}>{v.status}</span>
                {v.duration_seconds && (
                  <span className="duration">{formatTimestamp(v.duration_seconds)}</span>
                )}
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
