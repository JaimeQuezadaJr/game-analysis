import React, { useState } from "react";
import axios from "axios";

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
    <div style={{ textAlign: "center", padding: "20px" }}>
      <h1>Fortnite Aim & Reaction Report</h1>
      
      <div style={{ margin: "20px 0" }}>
        <input type="file" accept="video/*" onChange={handleFileChange} />
        <button 
          onClick={handleUpload} 
          disabled={loading}
          style={{
            marginLeft: "10px",
            padding: "8px 16px",
            backgroundColor: loading ? "#cccccc" : "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Processing..." : "Upload & Analyze"}
        </button>
      </div>

      {/* Progress Bar */}
      {(loading || status) && (
        <div style={{ margin: "20px auto", maxWidth: "400px" }}>
          <div style={{ marginBottom: "10px", color: "#666" }}>
            {status}
          </div>
          <div style={{ 
            width: "100%", 
            backgroundColor: "#f0f0f0",
            borderRadius: "4px",
            overflow: "hidden"
          }}>
            <div style={{
              width: `${progress}%`,
              backgroundColor: "#4CAF50",
              height: "20px",
              transition: "width 0.3s ease-in-out"
            }} />
          </div>
        </div>
      )}

      {/* Results */}
      {report && !loading && (
        <div style={{ 
          marginTop: "20px",
          padding: "20px",
          backgroundColor: "#f9f9f9",
          borderRadius: "8px",
          maxWidth: "600px",
          margin: "20px auto"
        }}>
          <h2>Analysis Report</h2>
          <div style={{ display: "grid", gap: "10px", textAlign: "left" }}>
            <p><strong>Total Shots:</strong> {report.total_shots}</p>
            <p><strong>Total Hits:</strong> {report.total_hits}</p>
            <p><strong>Accuracy:</strong> {typeof report.accuracy === 'number' ? report.accuracy.toFixed(2) : '0.00'}%</p>
            <p>
              <strong>Avg Reaction Time:</strong>{" "}
              {report.average_reaction_time
                ? typeof report.average_reaction_time === 'number' 
                  ? report.average_reaction_time.toFixed(2) + "s"
                  : "N/A"
                : "N/A"}
            </p>
            <p>
              <strong>Video Duration:</strong>{" "}
              {typeof report.video_duration === 'number' 
                ? report.video_duration.toFixed(2) 
                : '0.00'}s
            </p>
            <p><strong>Frames Processed:</strong> {report.processed_frames} / {report.total_frames}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
