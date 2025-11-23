# DateNow Development Guide

## Project Structure

```
DateNow/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── config.py       # Configuration settings
│   │   ├── database.py     # Database configuration
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── auth.py         # Authentication utilities
│   │   ├── ai_service.py   # Gemini AI integration
│   │   └── routes/         # API routes
│   │       ├── auth.py     # Authentication endpoints
│   │       ├── users.py    # User profile endpoints
│   │       └── matches.py  # Matching & AI conversation endpoints
│   ├── requirements.txt
│   ├── Dockerfile
│   └── seed_data.py        # Database seeding script
├── frontend/               # React frontend
│   ├── src/
│   │   ├── main.tsx       # Application entry point
│   │   ├── App.tsx        # Main app component with routing
│   │   ├── index.css      # Global styles
│   │   ├── lib/
│   │   │   └── api.ts     # API client
│   │   ├── store/
│   │   │   └── authStore.ts  # Authentication state
│   │   └── pages/         # Page components
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml      # Docker services configuration
└── README.md              # Project documentation
```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Google Gemini API Key

### Backend Setup

1. **Create virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL
# - REDIS_URL
# - GEMINI_API_KEY
# - JWT_SECRET_KEY
```

4. **Initialize database:**
```bash
# The database will be created automatically on first run
python seed_data.py  # Optional: seed with initial data
```

5. **Run development server:**
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env:
# VITE_API_URL=http://localhost:8000
# VITE_WS_URL=ws://localhost:8000
```

3. **Run development server:**
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

### Docker Setup (Recommended)

1. **Set environment variables:**
```bash
# Create .env in project root
echo "GEMINI_API_KEY=your_api_key_here" > .env
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env
```

2. **Start all services:**
```bash
docker-compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Backend API** on port 8000
- **Frontend** on port 3000

## Database Models

### Core Models

1. **User** - Authentication and basic user info
2. **UserProfile** - Extended profile information
3. **PsychologicalProfile** - Psychological assessment data
4. **Interest** - User interests/hobbies
5. **Match** - Matching between two users
6. **AISession** - AI mediation session data
7. **Conversation** - Conversation container
8. **Message** - Individual messages
9. **AIPromptTemplate** - Reusable AI prompts
10. **AIConversationLog** - AI interaction logs

### Database Schema

```sql
users
├── id (PK)
├── email (unique)
├── hashed_password
├── is_active
├── is_verified
└── timestamps

user_profiles
├── id (PK)
├── user_id (FK -> users.id)
├── first_name, last_name
├── date_of_birth, gender
├── bio, location
├── preferences (gender, age, distance)
└── timestamps

psychological_profiles
├── id (PK)
├── user_id (FK -> users.id)
├── big_five_traits (O, C, E, A, N)
├── values (family, career, adventure, etc.)
├── communication_style
├── love_languages
├── attachment_style
└── ai_insights

matches
├── id (PK)
├── user1_id, user2_id (FK -> users.id)
├── status (pending, ai_mediation, direct_chat, etc.)
├── compatibility_scores
├── compatibility_report
└── timestamps

ai_sessions
├── id (PK)
├── match_id (FK -> matches.id)
├── user_id (FK -> users.id)
├── status
├── questions_asked, responses_collected
├── session_data (JSON with Q&A pairs)
└── timestamps
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### User Profile
- `GET /api/v1/users/me/profile` - Get current user profile
- `POST /api/v1/users/me/profile` - Create profile
- `PATCH /api/v1/users/me/profile` - Update profile
- `GET /api/v1/users/me/psychological-profile` - Get psych profile
- `POST /api/v1/users/me/psychological-profile` - Create psych profile
- `GET /api/v1/interests` - Get all interests
- `GET /api/v1/users/me/interests` - Get user interests
- `POST /api/v1/users/me/interests` - Update interests

### Matching
- `GET /api/v1/matches/suggestions` - Get match suggestions
- `GET /api/v1/matches` - Get all user matches
- `GET /api/v1/matches/{id}` - Get specific match
- `POST /api/v1/matches/{id}/action` - Perform match action

### AI Conversation
- `GET /api/v1/matches/{id}/ai-session` - Get AI session
- `POST /api/v1/matches/{id}/ai-session/question` - Get next question
- `POST /api/v1/matches/{id}/ai-session/response` - Submit answer

## AI Service

The AI service (`app/ai_service.py`) handles all Gemini API interactions:

### Key Functions

1. **`analyze_psychological_profile()`** - Generate insights from psych profile
2. **`calculate_compatibility()`** - Calculate multi-dimensional compatibility
3. **`generate_conversation_question()`** - Generate personalized questions
4. **`analyze_conversation_response()`** - Analyze user responses
5. **`generate_compatibility_report()`** - Final compatibility assessment
6. **`generate_conversation_starter()`** - Create opening messages

### Compatibility Calculation

Compatibility is calculated across 4 dimensions:
1. **Personality** (30%) - Big Five trait alignment
2. **Values** (30%) - Core values similarity
3. **Interests** (20%) - Shared hobbies/interests
4. **Lifestyle** (20%) - Location, goals, preferences

## Testing

### Backend Tests
```bash
cd backend
pytest
pytest --cov=app  # With coverage
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Code Style

### Python (Backend)
- Follow PEP 8
- Use type hints
- Docstrings for functions
- Use async/await for I/O operations

### TypeScript (Frontend)
- Follow Airbnb style guide
- Use TypeScript strict mode
- Functional components with hooks
- Props type definitions

## Common Development Tasks

### Adding a New API Endpoint

1. Define Pydantic schema in `app/schemas.py`
2. Create route function in appropriate file in `app/routes/`
3. Add business logic in service file if needed
4. Update API client in `frontend/src/lib/api.ts`
5. Test the endpoint

### Adding a New Page

1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Update navigation as needed

### Modifying Database Schema

1. Update model in `app/models.py`
2. Create Alembic migration (if using)
3. Update Pydantic schemas
4. Update API endpoints
5. Update frontend types

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

### API Not Responding
```bash
# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Frontend Build Issues
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite
```

## Performance Optimization

### Backend
- Use database connection pooling
- Implement caching with Redis
- Optimize database queries (use indexes)
- Batch AI API calls when possible

### Frontend
- Lazy load routes with React.lazy()
- Implement virtual scrolling for long lists
- Use React Query for efficient data fetching
- Optimize images and assets

## Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Validate all inputs** - Use Pydantic schemas
3. **Sanitize user content** - Prevent XSS
4. **Use HTTPS in production**
5. **Implement rate limiting**
6. **Keep dependencies updated**
7. **Use strong JWT secrets**

## Contributing

1. Create feature branch from `main`
2. Make changes with clear commit messages
3. Write tests for new features
4. Update documentation
5. Submit pull request

## License

MIT License - see LICENSE file for details
