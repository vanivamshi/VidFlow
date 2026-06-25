import { useState } from "react";
import { useRouter } from "next/router";
import { uploadVideo } from "@/lib/api";

export default function Upload() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !title) return;

    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("title", title);
      form.append("description", description);
      form.append("file", file);
      const video = await uploadVideo(form);
      router.push(`/video/${video.id}`);
    } catch {
      setError("Upload failed. Is the backend running?");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="upload-page">
      <h1>Upload Video</h1>
      <p className="subtitle">Video will be transcoded, transcribed, and indexed for semantic search</p>

      <form onSubmit={handleSubmit} className="upload-form">
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Description
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
        </label>
        <label>
          Video File
          <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={uploading}>
          {uploading ? "Uploading & Processing..." : "Upload"}
        </button>
      </form>
    </div>
  );
}
