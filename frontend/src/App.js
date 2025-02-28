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

      // Log the structured data
      console.log("Extracted Match Data:", {
        timestamp: new Date().toISOString(),
        filename: file.name,
        data: response.data
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
            
            {/* Match Stats */}
            {report.match_summary && (
              <div className="stats-grid">
                {/* Always show Placement first */}
                <div className="stat-box placement-stat">
                  <div className="stat-label">Placement</div>
                  <div className="stat-value">{report.match_summary.placement}</div>
                </div>

                {/* Combat Stats */}
                <div className="stat-box">
                  <div className="stat-label">Eliminations</div>
                  <div className="stat-value">{report.match_summary.combat_stats.eliminations}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Damage Dealt</div>
                  <div className="stat-value">{report.match_summary.combat_stats.damage_dealt}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Damage Taken</div>
                  <div className="stat-value">{report.match_summary.combat_stats.damage_taken}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Accuracy</div>
                  <div className="stat-value">{`${report.match_summary.combat_stats.accuracy}%`}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Hits</div>
                  <div className="stat-value">{report.match_summary.combat_stats.hits}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Headshots</div>
                  <div className="stat-value">{report.match_summary.combat_stats.headshots}</div>
                </div>

                {/* Support Stats */}
                <div className="stat-box">
                  <div className="stat-label">Assists</div>
                  <div className="stat-value">{report.match_summary.support_stats.assists}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Revives</div>
                  <div className="stat-value">{report.match_summary.support_stats.revives}</div>
                </div>

                {/* Resource Stats */}
                <div className="stat-box">
                  <div className="stat-label">Materials Gathered</div>
                  <div className="stat-value">{report.match_summary.resource_stats.materials_gathered}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Materials Used</div>
                  <div className="stat-value">{report.match_summary.resource_stats.materials_used}</div>
                </div>
                <div className="stat-box">
                  <div className="stat-label">Damage to Structures</div>
                  <div className="stat-value">{report.match_summary.resource_stats.damage_to_structures}</div>
                </div>

                {/* Movement Stats */}
                <div className="stat-box">
                  <div className="stat-label">Distance Traveled</div>
                  <div className="stat-value">{`${report.match_summary.movement_stats.distance_traveled}km`}</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
