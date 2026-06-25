import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import { fetchVideos, Video, formatTimestamp } from "@/lib/api";

export default function VideoPage() {
  const router = useRouter();
  const { id, t } = router.query;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [video, setVideo] = useState<Video | null>(null);

  useEffect(() => {
    if (!id) return;
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost"}/api/videos/${id}`)
      .then((r) => r.json())
      .then(setVideo)
      .catch(console.error);
  }, [id]);

  useEffect(() => {
    if (videoRef.current && t) {
      videoRef.current.currentTime = parseFloat(t as string);
    }
  }, [video, t]);

  if (!video) return <p className="loading">Loading video...</p>;

  return (
    <div className="video-page">
      <h1>{video.title}</h1>
      {video.description && <p className="subtitle">{video.description}</p>}

      <div className="player-wrapper">
        {video.playback_url ? (
          <video ref={videoRef} controls src={video.playback_url} className="player" />
        ) : (
          <div className="processing">
            <span className={`status status-${video.status}`}>{video.status}</span>
            <p>Video is being processed...</p>
          </div>
        )}
      </div>

      <div className="video-meta">
        <span className={`status status-${video.status}`}>{video.status}</span>
        {video.duration_seconds && (
          <span>Duration: {formatTimestamp(video.duration_seconds)}</span>
        )}
      </div>
    </div>
  );
}
