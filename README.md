# DateNow - AI-Moderated Dating Platform

## 🎯 Overview

DateNow is a revolutionary dating platform that uses AI to facilitate meaningful connections. Unlike traditional dating apps, DateNow employs an AI moderator that conducts structured conversations with both users, helping them get to know each other through intelligent questioning before allowing direct interaction.

## 🌟 Key Features

### 1. **AI-Moderated Conversations**
- AI acts as a mediator between potential matches
- Asks thoughtful questions to both users separately
- Facilitates natural conversation flow
- Assesses compatibility in real-time

### 2. **Psychological Profiling**
- Science-based onboarding questionnaire
- Personality assessment using validated frameworks
- Values, interests, and relationship goals analysis
- Continuous learning from user interactions

### 3. **Smart Matching Algorithm**
- Multi-dimensional compatibility scoring
- Considers psychological profiles, interests, values, and goals
- AI-powered match suggestions
- Quality over quantity approach

### 4. **Dual-Session System**
- AI creates separate conversation sessions for each user
- Gathers information from both parties simultaneously
- Builds comprehensive understanding before introduction
- Ensures both parties are genuinely interested

### 5. **Gradual Reveal System**
- Starts with AI-mediated conversations
- Gradually reveals information based on compatibility
- Smooth transition to direct messaging
- AI continues to provide relationship insights

## 🏗️ Architecture

```
┌─────────────────┐
│   React Web     │
│   Application   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │
│  Backend API    │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Postgres│ │ Redis  │ │Gemini  │ │WebSocket│
│   DB   │ │ Cache  │ │  AI    │ │ Server  │
└────────┘ └────────┘ └────────┘ └────────┘
```

## 🚀 Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **AI**: Google Gemini API
- **Frontend**: React 18+ with TypeScript
- **Real-time**: WebSockets
- **Authentication**: JWT
- **Deployment**: Docker + Docker Compose

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Google Gemini API Key

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

### Docker Setup (Recommended)

```bash
# Build and start all services
docker-compose up --build

# The application will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## 🔑 Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/datenow
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your_gemini_api_key_here
JWT_SECRET_KEY=your_secret_key_here
ENVIRONMENT=development
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 📚 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 🎯 How It Works

1. **User Registration**: Users sign up and complete psychological profiling
2. **AI Profiling**: System analyzes personality, values, and preferences
3. **Smart Matching**: Algorithm suggests compatible matches
4. **AI Mediation**: When users express mutual interest:
   - AI creates dual conversation sessions
   - Asks personalized questions to both users
   - Gathers deeper insights about compatibility
   - Facilitates natural conversation flow
5. **Compatibility Assessment**: AI analyzes responses and compatibility
6. **Gradual Reveal**: If compatible, AI gradually transitions to direct chat
7. **Ongoing Support**: AI continues to provide relationship insights

## 🔒 Security & Privacy

- End-to-end encryption for messages
- Secure password hashing (bcrypt)
- JWT token authentication
- GDPR compliant data handling
- User data anonymization in AI processing
- Regular security audits

## 🤝 Contributing

We welcome contributions! Please see CONTRIBUTING.md for details.

## 📄 License

MIT License - see LICENSE file for details

## 📞 Support

For support, email support@datenow.app or join our Discord community.

## 🗺️ Roadmap

- [ ] Voice-based AI conversations
- [ ] Video date scheduling with AI facilitation
- [ ] Multi-language support
- [ ] Mobile applications (iOS & Android)
- [ ] Advanced compatibility analytics dashboard
- [ ] Integration with relationship counseling services

---

Built with ❤️ using AI to create meaningful human connections
