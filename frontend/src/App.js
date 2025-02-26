import React, { useState } from "react";
import axios from "axios";
import './App.css'; // We'll create this file next

function App() {
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setReport(null);
    setProgress(0);
    setStatus("");
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a file!");

    setLoading(true);
    setStatus("Uploading video...");
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("debug", "true");

    try {
      const response = await axios.post("http://127.0.0.1:5000/upload", formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const uploadProgress = Math.round(
            (progressEvent.loaded / progressEvent.total) * 50
          );
          setProgress(uploadProgress);
          setStatus("Uploading video... " + uploadProgress + "%");
        },
      });

      setProgress(100);
      setStatus("Processing complete!");
      setReport(response.data);
    } catch (error) {
      console.error("Error uploading file:", error);
      setStatus(
        error.response?.data?.error || 
        error.message || 
        "Error processing video"
      );
      setProgress(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fortnite-container">
      <div className="fortnite-header">
        <h1>FORTNITE AIM TRACKER</h1>
      </div>
      
      <div className="fortnite-card">
        <div className="upload-section">
          <input 
            type="file" 
            accept="video/*" 
            onChange={handleFileChange} 
            id="file-upload"
            className="file-input"
          />
          <label htmlFor="file-upload" className="fortnite-button file-label">
            SELECT VIDEO
          </label>
          <button 
            onClick={handleUpload} 
            disabled={loading}
            className={`fortnite-button ${loading ? 'disabled' : ''}`}
          >
            {loading ? "PROCESSING..." : "ANALYZE"}
          </button>
        </div>

        {/* File name display */}
        {file && (
          <div className="file-name">
            Selected: {file.name}
          </div>
        )}

        {/* Progress Bar */}
        {(loading || status) && (
          <div className="progress-container">
            <div className="status-text">
              {status}
            </div>
            <div className="progress-bar-bg">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Results */}
        {report && !loading && (
          <div className="results-container">
            <h2 className="results-header">BATTLE REPORT</h2>
            <div className="stats-grid">
              <div className="stat-box">
                <div className="stat-label">SHOTS FIRED</div>
                <div className="stat-value">{report.total_shots}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">HITS LANDED</div>
                <div className="stat-value">{report.total_hits}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">ACCURACY</div>
                <div className="stat-value">{typeof report.accuracy === 'number' ? report.accuracy.toFixed(2) : '0.00'}%</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">SHIELD HITS</div>
                <div className="stat-value">{report.shield_hits}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">HEALTH HITS</div>
                <div className="stat-value">{report.health_hits}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">DURATION</div>
                <div className="stat-value">{typeof report.video_duration === 'number' ? report.video_duration.toFixed(2) : '0.00'}s</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
