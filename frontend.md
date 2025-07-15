# ClassBackend Frontend Developer Guide

## Overview

ClassBackend is a Django REST API backend that provides AI-powered learning services, user authentication, course management, and learning analytics. This guide provides everything frontend developers need to integrate with the backend services.

## Base URL

- **Development**: `http://localhost:8000/api/v1/`
- **Production**: `https://your-domain.com/api/v1/`

## Authentication

### Authentication Method
The API uses Token-based authentication with Django Rest Framework.

### Headers Required
```http
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json
```

### Login
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "userpassword"
}
```

**Response:**
```json
{
    "status": "success",
    "token": "abc123def456...",
    "user": {
        "uuid": "12e57a8d-7cfd-458b-a233-55ddaad3da1d",
        "email": "user@example.com",
        "username": "username",
        "created_at": "2025-01-01T00:00:00Z"
    }
}
```

### Logout
```http
POST /api/v1/auth/logout/
Authorization: Token YOUR_TOKEN_HERE
```

**Response:**
```json
{
    "status": "success",
    "message": "Successfully logged out"
}
```
## API Endpoints

### 1. Health Check

#### Get System Health
```http
GET /health/
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-01T00:00:00Z",
    "version": "1.0.0"
}
```

### 2. AI Services

#### Get AI Services Status
```http
GET /api/v1/ai/status/
Authorization: Token YOUR_TOKEN_HERE
```

**Response:**
```json
{
    "status": "success",
    "services": {
        "exercise": {
            "available": true,
            "name": "Exercise Generation Service"
        },
        "teacher": {
            "available": true,
            "name": "AI Teacher Service"
        },
        "advisor": {
            "available": true,
            "name": "Learning Advisor Service"
        }
    }
}
```

#### Generate AI Exercises
```http
POST /api/v1/ai/exercises/generate/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
    "num_questions": 5,
    "difficulty": "medium",
    "topic": "Python functions"
}
```

**Response:**
```json
{
    "status": "success",
    "exercises": [
        {
            "id": 1,
            "question": "What is a function in Python?",
            "type": "multiple_choice",
            "options": ["A callable object", "A variable", "A loop", "A condition"],
            "correct_answer": "A callable object",
            "explanation": "Functions are callable objects in Python..."
        }
    ]
}
```

#### Get AI Teaching Help
```http
POST /api/v1/ai/teaching/help/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
    "question": "How do I create a function in Python?",
    "context": "I'm learning Python basics"
}
```

**Response:**
```json
{
    "status": "success",
    "response": {
        "answer": "To create a function in Python, use the 'def' keyword...",
        "examples": [
            "def my_function():\n    print('Hello World')"
        ],
        "related_concepts": ["parameters", "return values", "scope"]
    }
}
```

#### Get Learning Advice
```http
POST /api/v1/ai/advice/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
    "current_progress": {
        "completed_topics": ["variables", "loops"],
        "difficulty_level": "beginner"
    },
    "goals": ["learn functions", "build a project"]
}
```

**Response:**
```json
{
    "status": "success",
    "advice": {
        "recommendations": [
            "Focus on understanding function parameters",
            "Practice with simple function exercises"
        ],
        "next_topics": ["functions", "modules"],
        "estimated_time": "2-3 hours"
    }
}
```

### 3. User Authentication

#### Register New User
```http
POST /api/v1/auth/register/
Content-Type: application/json

{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "securepassword123"
}
```

#### Get User Profile
```http
GET /api/v1/auth/profile/
Authorization: Token YOUR_TOKEN_HERE
```

**Response:**
```json
{
    "uuid": "12e57a8d-7cfd-458b-a233-55ddaad3da1d",
    "email": "user@example.com",
    "username": "username",
    "created_at": "2025-01-01T00:00:00Z",
    "email_verified": true,
    "profile_visibility": "private"
}
```

### 4. Course Management

#### List User Courses
```http
GET /api/v1/courses/
Authorization: Token YOUR_TOKEN_HERE
```

**Response:**
```json
{
    "count": 2,
    "results": [
        {
            "course_uuid": "abc-123-def",
            "subject_name": "Python Programming",
            "proficiency_level": 25,
            "difficulty": 5,
            "learning_hour_total": 20,
            "created_at": "2025-01-01T00:00:00Z"
        }
    ]
}
```

#### Get Course Progress
```http
GET /api/v1/courses/{course_uuid}/
Authorization: Token YOUR_TOKEN_HERE
```

#### Update Course Progress
```http
PATCH /api/v1/courses/{course_uuid}/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
    "proficiency_level": 50,
    "learning_hour_week": 5
}
```

### 5. Learning Plans

#### List Learning Plans
```http
GET /api/v1/learning-plans/
Authorization: Token YOUR_TOKEN_HERE
```

#### Create Study Session
```http
POST /api/v1/learning-plans/sessions/
Authorization: Token YOUR_TOKEN_HERE
Content-Type: application/json

{
    "course_progress": "abc-123-def",
    "duration_minutes": 60,
    "content_covered": "Python functions and modules",
    "effectiveness_rating": 4
}
```

**Response:**
```json
{
    "id": 123,
    "start_time": "2025-01-01T10:00:00Z",
    "duration_minutes": 60,
    "effectiveness_rating": 4,
    "created_at": "2025-01-01T10:00:00Z"
}
```

## Data Formats

### Common Response Format
All API responses follow this structure:
```json
{
    "status": "success|error",
    "data": {...},
    "message": "Optional message",
    "errors": {...}
}
```

### Date/Time Format
All timestamps are in ISO 8601 format with UTC timezone:
```
2025-01-01T12:00:00Z
```

### UUID Format
All UUIDs are in standard format:
```
12e57a8d-7cfd-458b-a233-55ddaad3da1d
```

## Error Handling

### Error Response Format
```json
{
    "status": "error",
    "message": "Error description",
    "errors": {
        "field_name": ["Error message for this field"]
    },
    "code": "ERROR_CODE"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limiting)
- `500` - Internal Server Error

### Authentication Errors
```json
{
    "status": "error",
    "message": "Authentication credentials were not provided.",
    "code": "AUTHENTICATION_REQUIRED"
}
```

## Rate Limiting

- **General API**: 100 requests per minute per user
- **AI Services**: 10 requests per minute per user
- **Authentication**: 5 login attempts per minute per IP

When rate limit is exceeded:
```json
{
    "status": "error",
    "message": "Rate limit exceeded",
    "retry_after": 60
}
```

## Important Notes

### 1. Input Limits
- **Text fields**: Maximum 1000 characters unless specified
- **Exercise generation**: Maximum 20 questions per request
- **File uploads**: Maximum 10MB per file

### 2. Async Behavior
- AI service calls may take 5-30 seconds to complete
- Large course content generation is processed asynchronously
- Use polling or WebSocket for real-time updates

### 3. Caching
- Course data is cached for 1 hour
- AI responses are cached for 2 hours
- User profiles are cached for 30 minutes

### 4. Security
- All passwords must be at least 8 characters
- API tokens expire after 24 hours of inactivity
- Enable 2FA for production use

### 5. Pagination
Large lists are paginated with the following format:
```json
{
    "count": 100,
    "next": "http://localhost:8000/api/v1/courses/?page=2",
    "previous": null,
    "results": [...]
}
```

## Development Tips

### 1. Testing with cURL
```bash
# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# Use token in subsequent requests
curl -X GET http://localhost:8000/api/v1/courses/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### 2. Environment Variables
```javascript
// Frontend environment configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
```

### 3. Error Handling Example (React)
```javascript
const handleApiCall = async (url, options) => {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Authorization': `Token ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'API call failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};
```

## Support

For additional support or questions:
- Check the API health endpoint for system status
- Review error messages for specific guidance  
- All endpoints support OPTIONS method for CORS preflight

## Changelog

### Version 1.0.0 (Current)
- Initial API release
- AI services integration
- User authentication and profiles
- Course management system
- Learning analytics
- Real-time progress tracking

---

*Last updated: 2025-07-14*
    }>;
  };
  chapter_count: number;
  total_content_length: string;
}
```

### StudySession Model
```typescript
interface StudySession {
  id: number;
  user: string;
  subject: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  focus_score: number; // 0-1
  effectiveness_rating: number; // 1-5
  notes: string;
  topics_covered: string[];
}
```

## 🐛 Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check if token is valid and properly set in headers
2. **CORS Issues**: Ensure your frontend domain is in ALLOWED_HOSTS
3. **Slow Responses**: API uses caching, first requests may be slower
4. **Missing Data**: Some fields are optional, always check for null/undefined

### Debug Mode

For development, you can enable debug mode by adding:
```javascript
apiClient.defaults.headers['X-Debug'] = 'true';
```

## 📞 Support

- **API Documentation**: Available at `/api/schema/swagger-ui/` when server is running
- **Health Check**: `GET /health/` - Check if backend services are operational
- **Cache Stats**: `GET /api/v1/cache-stats/` - Monitor cache performance

## 🚀 Next Steps

1. Set up your frontend authentication flow
2. Implement course listing and progress tracking  
3. Integrate AI services for personalized learning
4. Add study session tracking
5. Implement error handling and loading states

Happy coding! 🎉
