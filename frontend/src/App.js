import React, { useState } from "react";
import axios from "axios";
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    // Verify file is an image
    if (selectedFile && !selectedFile.type.startsWith('image/')) {
      setError("Please select an image file");
      return;
    }
    
    setFile(selectedFile);
    setReport(null);
    setError("");
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select an image file!");
      return;
    }

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://127.0.0.1:5000/upload", formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      setReport(response.data);
    } catch (error) {
      console.error("Error uploading file:", error);
      setError(
        error.response?.data?.error || 
        error.message || 
        "Error processing image"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fortnite-container">
      <div className="fortnite-header">
        <h1>FORTNITE STATS EXTRACTOR</h1>
      </div>
      
      <div className="fortnite-card">
        <div className="upload-section">
          <input 
            type="file" 
            accept="image/*" 
            onChange={handleFileChange} 
            id="file-upload"
            className="file-input"
          />
          <label htmlFor="file-upload" className="fortnite-button file-label">
            SELECT IMAGE
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

        {/* Error message */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Results */}
        {report && !loading && (
          <div className="results-container">
            <h2 className="results-header">MATCH SUMMARY</h2>
            
            {/* Placement */}
            {report.placement && (
              <div className="placement-box">
                {report.placement}
              </div>
            )}
            
            {/* Match Stats */}
            {report.match_stats && Object.keys(report.match_stats).length > 0 && (
              <div className="stats-grid">
                {Object.entries(report.match_stats).map(([key, value]) => (
                  <div className="stat-box" key={key}>
                    <div className="stat-label">{key}</div>
                    <div className="stat-value">
                      {key === "Accuracy" ? `${value}%` : 
                       key === "Distance Traveled" ? `${value}km` :
                       value}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
