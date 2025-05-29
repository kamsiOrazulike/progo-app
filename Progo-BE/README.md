# Progo ML Backend

A comprehensive machine learning-enabled backend for IoT sensor data collection and exercise classification. This FastAPI-based backend receives 9-DOF IMU sensor data from ESP32 devices, stores it in a database, performs real-time feature extraction, and trains/serves ML models to classify exercise movements (squats vs bicep curls).

## 🚀 Features

- **Real-time Sensor Data Ingestion**: Receive 9-DOF IMU data (accelerometer, gyroscope, magnetometer) from ESP32 devices via HTTP POST
- **Exercise Session Management**: Create, track, and manage exercise sessions
- **Advanced Feature Extraction**: 200+ features extracted from sensor data including statistical, frequency domain, and time-series features
- **Machine Learning Pipeline**: Train Random Forest classifiers to distinguish between different exercise types
- **Real-time Predictions**: Classify exercise movements in real-time with confidence scores
- **RESTful API**: Comprehensive FastAPI endpoints with automatic documentation
- **Database Storage**: SQLite (development) / PostgreSQL (production) for data persistence
- **Health Monitoring**: Built-in health checks and system status monitoring

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd progo-app/Progo-BE
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` file with your settings:

```properties
# Database (SQLite for development)
DATABASE_URL=sqlite:///./progo_dev.db
DATABASE_URL_ASYNC=sqlite+aiosqlite:///./progo_dev.db

# Security
SECRET_KEY=your-secret-key-change-in-production

# Debug mode
DEBUG=True
LOG_LEVEL=INFO

# ML Configuration
FEATURE_WINDOW_SIZE=200
WINDOW_OVERLAP=0.5
MIN_TRAINING_SAMPLES=100

# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=Progo ML Backend
```

### 5. Initialize Database

The database will be automatically created when you start the application for the first time.

## 🚀 Running the Application

### Development Mode

```bash
# Make sure you're in the Progo-BE directory and virtual environment is activated
cd /path/to/progo-app/Progo-BE
source venv/bin/activate

# Start the FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
python app/main.py
```

The server will start on `http://localhost:8000`

### Production Mode

```bash
# Install gunicorn for production
pip install gunicorn

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📚 API Documentation

Once the server is running, you can access:

- **Interactive API Documentation**: http://localhost:8000/docs
- **Alternative Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Key Endpoints

#### Health & Status
- `GET /health` - System health check
- `GET /api/v1/info` - System information

#### Sensor Data
- `POST /api/v1/sensor-data/` - Submit sensor data from ESP32
- `GET /api/v1/sensor-data/` - Retrieve sensor readings (with pagination)

#### Exercise Sessions
- `POST /api/v1/sessions/` - Create new exercise session
- `GET /api/v1/sessions/` - List exercise sessions
- `PUT /api/v1/sessions/{id}` - Update session details

#### Machine Learning
- `GET /api/v1/ml/status` - ML system status
- `POST /api/v1/ml/train` - Start model training
- `POST /api/v1/ml/predict` - Get exercise predictions
- `GET /api/v1/ml/models` - List trained models

## 🧪 Testing

### Run API Tests

A comprehensive test suite is included to verify all endpoints:

```bash
# Make sure the server is running in another terminal
python test_api.py
```

This will test:
- Health check endpoints
- Sensor data ingestion and retrieval
- Exercise session management
- ML system functionality
- Model training and prediction

### Expected Test Results

```
🎯 Total: 9/9 tests passed
🎉 All tests passed! API is working correctly.
```

## 📊 Sensor Data Format

The API expects sensor data in the following format:

```json
{
  "device_id": "ESP32_TEST_001",
  "timestamp": 1640995200000,
  "magnetometer_available": true,
  "accelerometer": {
    "x": 0.23,
    "y": -0.01,
    "z": 9.85
  },
  "gyroscope": {
    "x": 0.01,
    "y": 0.01,
    "z": -0.00
  },
  "magnetometer": {
    "x": 1617.00,
    "y": 1119.00,
    "z": -14421.00
  },
  "temperature": 26.82
}
```

## 🤖 Machine Learning Workflow

### 1. Data Collection
- Collect sensor data during exercise sessions
- Label sessions with exercise type (squat, bicep_curl)

### 2. Feature Extraction
- Window-based feature extraction (200 samples per window)
- Statistical features (mean, std, min, max, etc.)
- Frequency domain features (FFT-based)
- Time-series features (autocorrelation, etc.)

### 3. Model Training
```json
POST /api/v1/ml/train
{
  "model_name": "exercise_classifier",
  "model_type": "random_forest",
  "device_id": "ESP32_001"
}
```

### 4. Real-time Prediction
```json
POST /api/v1/ml/predict
{
  "sensor_data": [
    {
      "device_id": "ESP32_001",
      "timestamp": 1640995200000,
      "accelerometer": {"x": 0.23, "y": -0.01, "z": 9.85},
      "gyroscope": {"x": 0.01, "y": 0.01, "z": -0.00},
      "magnetometer": {"x": 1617.00, "y": 1119.00, "z": -14421.00}
    }
  ]
}
```

## 📁 Project Structure

```
Progo-BE/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup and sessions
│   ├── models/
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic models for API
│   ├── routers/
│   │   ├── sensor_data.py   # Sensor data endpoints
│   │   ├── sessions.py      # Exercise session endpoints
│   │   └── ml.py           # Machine learning endpoints
│   ├── ml/
│   │   ├── preprocessing.py # Feature extraction
│   │   ├── training.py      # Model training pipeline
│   │   ├── inference.py     # Real-time inference engine
│   │   └── models/         # Saved ML models
│   └── utils/
│       ├── logging.py       # Logging configuration
│       └── helpers.py       # Utility functions
├── logs/                    # Application logs
├── test_api.py             # API test suite
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./progo_dev.db` |
| `SECRET_KEY` | Secret key for security | Required |
| `DEBUG` | Enable debug mode | `True` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FEATURE_WINDOW_SIZE` | Sensor readings per ML window | `200` |
| `WINDOW_OVERLAP` | Overlap between windows | `0.5` |
| `MIN_TRAINING_SAMPLES` | Minimum samples for training | `100` |

### ML Model Configuration

- **Algorithm**: Random Forest Classifier
- **Features**: 200+ engineered features from sensor data
- **Window Size**: 200 sensor readings (~4 seconds at 50Hz)
- **Exercise Types**: Squat, Bicep Curl, Unknown

## 🚀 Deployment

### Using Docker

```bash
# Build the Docker image
docker build -t progo-backend .

# Run the container
docker run -p 8000:8000 progo-backend
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d
```

### Railway/Render Deployment

1. Set environment variables in your deployment platform
2. Use PostgreSQL for production database
3. Update `DATABASE_URL` and `DATABASE_URL_ASYNC` accordingly

## 🐛 Troubleshooting

### Common Issues

1. **Module Import Errors**
   ```bash
   # Make sure you're in the correct directory and virtual environment is activated
   cd Progo-BE
   source venv/bin/activate
   ```

2. **Database Connection Issues**
   ```bash
   # Check if SQLite file is created
   ls -la progo_dev.db
   
   # For PostgreSQL, verify connection string
   ```

3. **Port Already in Use**
   ```bash
   # Find and kill process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

4. **Python Version Issues**
   ```bash
   # Verify Python version
   python --version  # Should be 3.8+
   ```

## 📝 Development

### Adding New Features

1. Create new routes in `app/routers/`
2. Add database models in `app/models/database.py`
3. Add API schemas in `app/models/schemas.py`
4. Update tests in `test_api.py`

### Code Style

```bash
# Format code
black app/
isort app/

# Run linting
flake8 app/
```

## 📄 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the logs in the `logs/` directory

---

**Progo ML Backend** - Intelligent IoT sensor data processing for exercise classification 🏋️‍♂️
