# AI Surveillance Dashboard

A real-time theft detection system using AI-powered object detection with TensorFlow.js and Flask backend.

## Features

- **Real-time Object Detection**: Uses COCO-SSD model for detecting persons, objects, and weapons
- **Multiple Detection Modes**: Person detection, object detection, and weapon detection
- **Web-based Interface**: Modern HTML/CSS/JavaScript frontend
- **Flask Backend**: Python server with SQLite database
- **Face Detection**: Enhanced person detection using Tiny Face Detector
- **Detection History**: Tracks and displays recent detections
- **React Version**: Modern React implementation available

## Project Structure

```
project/
├── backend/
│   ├── app.py             # Flask application entry point
│   ├── requirements.txt      # Backend Python dependencies
│   ├── Procfile              # Deployment web process configuration
│   ├── config.py             # Configuration parameters
│   ├── create_db.py          # Database initialization helper
│   ├── modals.py             # Server modal utilities
│   └── data/
│       ├── locations.csv     # Surveillance location data
│       └── roads.csv         # Monitored road network data
├── frontend/
│   ├── index.html            # Main surveillance dashboard interface
│   ├── script.js             # Main frontend script & AI model detection logic
│   ├── style.css             # Primary application stylesheet
│   ├── styles.css            # Stylesheet alias
│   ├── login.html            # User authentication page
│   ├── object.html           # Object detection dashboard
│   ├── weapon.html           # Weapon detection dashboard
│   ├── mask.html             # Face mask detection dashboard
│   ├── db.js                 # Frontend database handler
│   ├── login.js              # Authentication UI handlers
│   └── modals.js             # Client modal UI components
└── README.md                 # Project documentation
```

## Installation

1. **Clone or navigate to the project directory**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   ```bash
   python create_db.py
   ```

## Running the Application

### Option 1: Run from project root (Recommended)
```bash
python run.py
```

### Option 2: Run from backend directory
```bash
cd backend
python app.py
```

Both methods will start the Flask server at `http://localhost:5000`

## API Endpoints

- `GET /` - Main person detection page
- `GET /object` - Object detection page
- `GET /weapon` - Weapon detection page
- `GET /login` - Login page
- `GET /api/target-classes/<mode>` - Get target classes for detection mode
- `GET/POST /api/detection-history` - Get/store detection history
- `GET /api/modals` - Get modal HTML
- `GET /api/system-status` - Get system status

## Detection Modes

### Person Detection
- Detects human presence using AI
- Enhanced with face detection model
- Real-time confidence scoring

### Object Detection
- Detects various objects (vehicles, furniture, etc.)
- 20+ object classes supported
- Configurable confidence thresholds

### Weapon Detection
- Specialized detection for knives and baseball bats
- High-precision alerting
- Security-focused monitoring

## Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **AI/ML**: TensorFlow.js, COCO-SSD, Tiny Face Detector
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Real-time**: WebRTC for camera access
- **UI Framework**: Custom responsive design

## Browser Requirements

- Modern browser with WebRTC support (Chrome, Firefox, Safari, Edge)
- Camera access permissions
- JavaScript enabled

## Development

The application includes both vanilla JavaScript and React implementations. The React version (`DetectionDashboard.jsx`) demonstrates modern frontend architecture with hooks and state management.

## Security Notes

- This is a development/demo application
- Camera access requires user permission
- No authentication implemented in basic version
- Use HTTPS in production environments

## License

This project is for educational and demonstration purposes.</content>
<parameter name="filePath">c:\Users\Yash Vishwakarma\OneDrive\Desktop\theft-detection\theft-detection-frontend\README.md