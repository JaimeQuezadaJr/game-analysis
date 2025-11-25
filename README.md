# Fortnite Stats Extractor & AI Analyzer

A modern web application that extracts match statistics from Fortnite victory screenshots and provides AI-powered performance analysis. Built with a clean, Apple-inspired UI design.

## Features

- 📸 **Image Upload**: Upload Fortnite match summary screenshots
- 🔍 **OCR Text Extraction**: Automatically extracts placement and match statistics using Tesseract OCR
- 📊 **Structured Data Display**: Beautiful, organized display of all match stats including:
  - Placement (1st, 2nd, 3rd, etc.)
  - Combat stats (Eliminations, Damage, Accuracy, Headshots)
  - Support stats (Assists, Revives)
  - Resource stats (Materials Gathered/Used, Structure Damage)
  - Movement stats (Distance Traveled)
- 🤖 **AI Analysis**: GPT-3.5 Turbo powered insights about your gameplay performance
- 🎨 **Modern UI**: Clean, Apple-inspired design with smooth animations

## Tech Stack

### Backend
- **Flask** - Python web framework
- **OpenCV** - Image processing
- **Tesseract OCR** - Text extraction from images
- **OpenAI API** - AI-powered match analysis
- **Flask-CORS** - Cross-origin resource sharing

### Frontend
- **React** - UI framework
- **Axios** - HTTP client
- **CSS3** - Modern styling with gradients and animations

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** (or use Conda)
- **Node.js 14+** and npm
- **Tesseract OCR**
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
  - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- **OpenAI API Key** (Optional) - Get one from [OpenAI Platform](https://platform.openai.com/) to enable AI analysis feature

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/game-analysis.git
cd game-analysis
```

### 2. Backend Setup

#### Option A: Using Conda (Recommended)

```bash
# Navigate to backend directory
cd backend

# Create and activate conda environment
conda create -n fortnite-stats python=3.10
conda activate fortnite-stats

# Install dependencies
conda install -c conda-forge flask flask-cors opencv numpy pillow python-dotenv openai tesseract pytesseract
```

#### Option B: Using pip

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install flask flask-cors opencv-python numpy pillow python-dotenv openai pytesseract
```

### 3. Configure Environment Variables (Optional)

The OpenAI API key is **optional**. The app will work perfectly for stats extraction without it, but AI analysis will be disabled.

If you want to enable AI analysis, create a `.env` file in the `backend` directory:

```bash
cd backend
touch .env
```

Add your OpenAI API key to the `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here
```

**Note**: You can skip this step if you only want to extract stats without AI analysis.

### 4. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install
```

## Running the Application

### 1. Start the Backend Server

```bash
# Make sure you're in the backend directory and your conda/venv is activated
cd backend
conda activate fortnite-stats  # or: source venv/bin/activate

# Run Flask server
python app.py
```

The backend server will start on `http://127.0.0.1:5000`

### 2. Start the Frontend Development Server

Open a new terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Start React development server
npm start
```

The frontend will automatically open in your browser at `http://localhost:3000`

## Usage

1. **Upload Image**: Click "SELECT IMAGE" and choose a Fortnite match summary screenshot
2. **Analyze**: Click "ANALYZE" to process the image
3. **View Stats**: See all extracted match statistics displayed in organized cards
4. **AI Insights**: Get AI-powered analysis of your performance below the stats

## Project Structure

```
game-analysis/
├── backend/
│   ├── app.py              # Flask application and API endpoints
│   ├── .env                # Environment variables (create this)
│   └── uploads/            # Temporary image storage
├── frontend/
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   └── App.css         # Styling
│   └── package.json        # Frontend dependencies
└── README.md               # This file
```

## API Endpoints

### `POST /upload`
Uploads and processes a Fortnite match screenshot.

**Request**: Form data with image file
**Response**: JSON object with extracted match statistics

### `POST /analyze`
Analyzes match data using AI.

**Request**: JSON object with match data
**Response**: JSON object with AI-generated insights

## Cost Considerations

This application uses OpenAI's GPT-3.5 Turbo API:
- **Cost**: ~$0.002 per 1K tokens
- **Average per analysis**: ~500 tokens
- **Estimated monthly cost**: 
  - 100 analyses: ~$0.10
  - 1,000 analyses: ~$1.00
  - 10,000 analyses: ~$10.00

Rate limiting is implemented (10 requests per minute per IP) to prevent abuse.

## Troubleshooting

### OCR Not Working
- Ensure Tesseract is installed and accessible in your PATH
- Check that image quality is good (clear text, good contrast)

### OpenAI API Errors
- Verify your API key is correct in the `.env` file
- Check your OpenAI account has available credits
- Ensure you're using the correct API key format

### CORS Errors
- Make sure the backend is running on port 5000
- Verify Flask-CORS is installed and configured

## Future Improvements

- [ ] Support for multiple match formats
- [ ] Historical match tracking
- [ ] Performance trends over time
- [ ] Comparison with other players
- [ ] Export statistics to CSV/JSON
- [ ] User authentication and profiles

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- OpenAI for GPT-3.5 Turbo API
- Tesseract OCR for text extraction
- Fortnite community for inspiration

