const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost";

export interface Video {
  id: string;
  title: string;
  description?: string;
  status: string;
  playback_url?: string;
  thumbnail_url?: string;
  duration_seconds?: number;
  created_at: string;
}

export interface SearchResult {
  video_id: string;
  start_time: number;
  end_time: number;
  text: string;
  score: number;
}

export async function fetchVideos(): Promise<Video[]> {
  const res = await fetch(`${API_BASE}/api/videos`);
  if (!res.ok) throw new Error("Failed to fetch videos");
  return res.json();
}

export async function uploadVideo(formData: FormData): Promise<Video> {
  const res = await fetch(`${API_BASE}/api/videos/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function searchVideos(query: string, mode = "semantic"): Promise<SearchResult[]> {
  const res = await fetch(
    `${API_BASE}/api/search?q=${encodeURIComponent(query)}&mode=${mode}`
  );
  if (!res.ok) throw new Error("Search failed");
  const data = await res.json();
  return data.results;
}

export async function fetchRecommendations(): Promise<{ video_id: string; title: string; score: number }[]> {
  const res = await fetch(`${API_BASE}/api/recommendations`);
  if (!res.ok) return [];
  return res.json();
}

export function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
