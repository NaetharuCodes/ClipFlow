import React, { useState, useEffect } from "react";
import "./App.css";

interface VideoClip {
  id: string;
  filename: string;
  file_path: string;
  file_size: number;
}

interface ConcatResult {
  message: string;
  output_filename: string;
  output_path: string;
  had_audio: boolean;
  clips_processed: number;
}

function App() {
  const [clips, setClips] = useState<VideoClip[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ConcatResult | null>(null);
  const [error, setError] = useState<string>("");

  // Load clips on mount
  useEffect(() => {
    loadClips();
  }, []);

  const loadClips = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/clips/");
      const data = await response.json();
      setClips(data.clips || []);
    } catch (err) {
      setError("Failed to load clips");
      console.error("Error loading clips:", err);
    }
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setError("");

    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("http://localhost:8000/api/clips/upload", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }
      }

      // Reload clips after upload
      await loadClips();

      // Clear the input
      event.target.value = "";
    } catch (err) {
      setError(`Upload failed: ${err}`);
      console.error("Upload error:", err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleConcatenate = async () => {
    if (clips.length < 2) {
      setError("Need at least 2 clips to concatenate");
      return;
    }

    setIsProcessing(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        "http://localhost:8000/api/clips/concatenate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            clip_ids: clips.map((clip) => clip.id),
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Concatenation failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(`Concatenation failed: ${err}`);
      console.error("Concatenation error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <div
      style={{
        maxWidth: "800px",
        margin: "0 auto",
        padding: "20px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      {/* Header */}
      <header
        style={{
          textAlign: "center",
          marginBottom: "40px",
          borderBottom: "2px solid #ddd",
          paddingBottom: "20px",
        }}
      >
        <h1 style={{ fontSize: "2.5rem", margin: "0", color: "#333" }}>
          🎬 ClipFlow
        </h1>
        <p style={{ color: "#666", margin: "10px 0 0 0" }}>
          AI Video Concatenation Tool
        </p>
      </header>

      {/* Upload Section */}
      <section
        style={{
          marginBottom: "40px",
          padding: "20px",
          border: "2px dashed #ccc",
          borderRadius: "8px",
          textAlign: "center",
        }}
      >
        <h2 style={{ marginTop: "0" }}>📁 Upload Video Clips</h2>
        <input
          type="file"
          multiple
          accept="video/*"
          onChange={handleFileUpload}
          disabled={isUploading}
          style={{ marginBottom: "10px" }}
        />
        <br />
        <small style={{ color: "#666" }}>
          {isUploading
            ? "Uploading..."
            : "Select multiple MP4 files (16fps recommended)"}
        </small>
      </section>

      {/* Clips List */}
      <section style={{ marginBottom: "40px" }}>
        <h2>📋 Uploaded Clips ({clips.length})</h2>
        {clips.length === 0 ? (
          <p style={{ color: "#666", fontStyle: "italic" }}>
            No clips uploaded yet
          </p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: "15px",
            }}
          >
            {clips.map((clip, index) => (
              <div
                key={clip.id}
                style={{
                  padding: "15px",
                  border: "1px solid #ddd",
                  borderRadius: "8px",
                  backgroundColor: "#f9f9f9",
                }}
              >
                <div style={{ fontWeight: "bold", marginBottom: "10px" }}>
                  #{index + 1}
                </div>

                {/* Video Preview */}
                <video
                  width="180"
                  height="120"
                  controls
                  style={{ marginBottom: "10px", borderRadius: "4px" }}
                  src={`http://localhost:8000/api/clips/${clip.id}/video`}
                >
                  Your browser doesn't support video playback.
                </video>

                <div
                  style={{
                    fontSize: "14px",
                    wordBreak: "break-word",
                    marginBottom: "5px",
                  }}
                >
                  {clip.filename}
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  {formatFileSize(clip.file_size)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Concatenate Button */}
      <section style={{ textAlign: "center", marginBottom: "40px" }}>
        <button
          onClick={handleConcatenate}
          disabled={isProcessing || clips.length < 2}
          style={{
            fontSize: "1.5rem",
            padding: "15px 40px",
            backgroundColor:
              clips.length >= 2 && !isProcessing ? "#007bff" : "#ccc",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor:
              clips.length >= 2 && !isProcessing ? "pointer" : "not-allowed",
            fontWeight: "bold",
          }}
        >
          {isProcessing ? "🔄 Processing..." : "🔄 CONCATENATE"}
        </button>
        <br />
        <small style={{ color: "#666", marginTop: "10px", display: "block" }}>
          {clips.length < 2
            ? `Need ${2 - clips.length} more clips`
            : `Ready to join ${clips.length} clips`}
        </small>
      </section>

      {/* Error Display */}
      {error && (
        <section
          style={{
            padding: "15px",
            backgroundColor: "#f8d7da",
            color: "#721c24",
            border: "1px solid #f5c6cb",
            borderRadius: "8px",
            marginBottom: "20px",
          }}
        >
          <strong>Error:</strong> {error}
        </section>
      )}

      {/* Results Section */}
      {result && (
        <section
          style={{
            padding: "20px",
            backgroundColor: "#d4edda",
            color: "#155724",
            border: "1px solid #c3e6cb",
            borderRadius: "8px",
          }}
        >
          <h2 style={{ marginTop: "0" }}>🎥 Video Created Successfully!</h2>

          {/* Video Player for Result */}
          <div style={{ textAlign: "center", marginBottom: "20px" }}>
            <video
              width="400"
              height="300"
              controls
              style={{ borderRadius: "8px", border: "2px solid #28a745" }}
              src={`http://localhost:8000/api/clips/output/${result.output_filename}`}
            >
              Your browser doesn't support video playback.
            </video>
          </div>

          <p>
            <strong>Output File:</strong> {result.output_filename}
          </p>
          <p>
            <strong>Clips Processed:</strong> {result.clips_processed}
          </p>
          <p>
            <strong>Audio:</strong> {result.had_audio ? "Yes" : "No"}
          </p>

          {/* Download Link */}
          <div style={{ textAlign: "center", marginTop: "15px" }}>
            <a
              href={`http://localhost:8000/api/clips/output/${result.output_filename}`}
              download={result.output_filename}
              style={{
                padding: "10px 20px",
                backgroundColor: "#28a745",
                color: "white",
                textDecoration: "none",
                borderRadius: "5px",
                fontWeight: "bold",
              }}
            >
              📥 Download Video
            </a>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
