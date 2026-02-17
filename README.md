# Email Outreach System V2 (Python + React + Kafka)

A robust, asynchronous email extraction and outreach automation system.

## Stack
- **Frontend**: React (Vite) + Glassmorphism CSS.
- **Backend**: Python FastAPI (Async).
- **Scraper**: `aiohttp` + `BeautifulSoup` + Recursive Crawling, Regex Extraction.
- **Queue**: Kafka (via `aiokafka`).
- **Database**: PostgreSQL (via `asyncpg`).
- **Worker**: Independent Python worker for email sending (AWS SES / Mock).

## Prerequisites
- Docker & Docker Compose
- Node.js (for frontend)
- Python 3.9+

## 🚀 Quick Start

### 1. Start Infrastructure
Launch Kafka, Zookeeper, and Postgres:
```bash
docker-compose up -d
```

### 2. Backend Setup
install dependencies and start the API + Worker:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run API (Worker runs as a background task for demo simplicity)
uvicorn src.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Usage
- Go to `http://localhost:5173`.
- Enter a URL to scrape.
- The system will:
  1. Crawl the site recursively.
  2. Extract and validate emails.
  3. Push to Kafka.
  4. Worker picks up and "sends" emails.
  5. Check logs in UI.

## Environment Variables
Create a `.env` in `backend/` if needed:
```
KAFKA_BROKER=localhost:9092
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
```
