import React, { useState, useEffect } from 'react';
import './App.css';

interface VideoClip {
  id: string;
  filename: string;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
  has_audio?: boolean;
  file_size?: number;
  thumbnail?: string;
}

interface ProcessingProgress {
  stage: string;
  progress: number;
  message?: string;
  output_filename?: string;
}

function App() {
  const [clips, setClips] = useState<VideoClip[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState<ProcessingProgress | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  // WebSocket connection for progress updates
  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8000/api/process/progress');
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data);
      
      if (data.stage === 'complete' || data.stage === 'error') {
        setIsProcessing(false);
      }
    };
    
    setWs(websocket);
    
    return () => {
      websocket.close();
    };
  }, []);

  // Load clips on component mount
  useEffect(() => {
    loadClips();
  }, []);

  const loadClips = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/clips/');
      const data = await response.json();
      setClips(data.clips || []);
    } catch (error) {
      console.error('Error loading clips:', error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);

    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://localhost:8000/api/clips/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('Upload successful:', result);
      } catch (error) {
        console.error('Upload error:', error);
        alert(`Failed to upload ${file.name}: ${error}`);
      }
    }

    setIsUploading(false);
    loadClips(); // Refresh clips list
    
    // Clear the input
    event.target.value = '';
  };

  const handleProcess = async () => {
    if (clips.length === 0) {
      alert('Please upload some video clips first');
      return;
    }

    setIsProcessing(true);
    setProgress({ stage: 'starting', progress: 0 });

    try {
      const response = await fetch('http://localhost:8000/api/process/concatenate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clip_ids: clips.map(clip => clip.id),
          output_filename: 'concatenated_video.mp4'
        }),
      });

      if (!response.ok) {
        throw new Error(`Processing failed: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Processing started:', result);
    } catch (error) {
      console.error('Processing error:', error);
      alert(`Processing failed: ${error}`);
      setIsProcessing(false);
    }
  };

  const handleDeleteClip = async (clipId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/clips/${clipId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Delete failed: ${response.statusText}`);
      }

      loadClips(); // Refresh clips list
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Failed to delete clip: ${error}`);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">🎬 ClipFlow</h1>
          <p className="text-gray-400">Modern video concatenation tool</p>
        </div>

        {/* Upload Section */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Upload Video Clips</h2>
          <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
            <input
              type="file"
              multiple
              accept="video/*"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
              disabled={isUploading}
            />
            <label
              htmlFor="file-upload"
              className={`cursor-pointer ${isUploading ? 'opacity-50' : 'hover:text-blue-400'}`}
            >
              <div className="text-4xl mb-4">📁</div>
              <p className="text-lg mb-2">
                {isUploading ? 'Uploading...' : 'Click to select video files'}
              </p>
              <p className="text-sm text-gray-500">
                Supports MP4, AVI, MOV, MKV, and more
              </p>
            </label>
          </div>
        </div>

        {/* Clips List */}
        {clips.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Video Clips ({clips.length})</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {clips.map((clip, index) => (
                <div key={clip.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-sm font-medium text-blue-400">#{index + 1}</span>
                    <button
                      onClick={() => handleDeleteClip(clip.id)}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      ✕
                    </button>
                  </div>
                  
                  {clip.thumbnail && (
                    <img
                      src={clip.thumbnail}
                      alt="Thumbnail"
                      className="w-full h-32 object-cover rounded mb-3"
                    />
                  )}
                  
                  <h3 className="font-medium mb-2 truncate" title={clip.filename}>
                    {clip.filename}
                  </h3>
                  
                  <div className="text-sm text-gray-400 space-y-1">
                    <div>Duration: {formatDuration(clip.duration)}</div>
                    <div>Size: {formatFileSize(clip.file_size)}</div>
                    {clip.width && clip.height && (
                      <div>Resolution: {clip.width}×{clip.height}</div>
                    )}
                    {clip.fps && (
                      <div>FPS: {clip.fps.toFixed(1)}</div>
                    )}
                    <div>Audio: {clip.has_audio ? '✅' : '❌'}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Process Section */}
        {clips.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Concatenate Videos</h2>
            
            {progress && (
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">
                    {progress.stage.charAt(0).toUpperCase() + progress.stage.slice(1)}
                  </span>
                  <span className="text-sm">{progress.progress}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress.progress}%` }}
                  ></div>
                </div>
                {progress.message && (
                  <p className="text-sm text-gray-400 mt-2">{progress.message}</p>
                )}
                {progress.output_filename && progress.stage === 'complete' && (
                  <div className="mt-4 p-3 bg-green-800 rounded">
                    <p className="text-green-200">
                      ✅ Video saved as: <strong>{progress.output_filename}</strong>
                    </p>
                    <p className="text-sm text-green-300 mt-1">
                      Check the output folder for your concatenated video!
                    </p>
                  </div>
                )}
              </div>
            )}
            
            <button
              onClick={handleProcess}
              disabled={isProcessing || clips.length === 0}
              className={`px-6 py-3 rounded-lg font-medium ${
                isProcessing || clips.length === 0
                  ? 'bg-gray-600 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isProcessing ? 'Processing...' : 'Concatenate Videos'}
            </button>
            
            <p className="text-sm text-gray-400 mt-2">
              This will combine all {clips.length} clips into a single video file.
            </p>
          </div>
        )}

        {/* Empty State */}
        {clips.length === 0 && !isUploading && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🎥</div>
            <h2 className="text-2xl font-semibold mb-2">No clips uploaded yet</h2>
            <p className="text-gray-400">
              Upload some video files to get started with concatenation
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;