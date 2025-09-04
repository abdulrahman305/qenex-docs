# Core System Documentation

## Overview

The Core System provides foundational services for application development.

## Components

### Database Manager
- SQLite with connection management
- Transaction support
- Schema migrations
- Query optimization

### Authentication System
- Secure password hashing (PBKDF2)
- Session management
- User registration and login
- Session expiration

### Cache Layer
- TTL-based caching
- Local and persistent cache
- Automatic cleanup
- Thread-safe operations

### API Framework
- Route registration
- Request handling
- Authentication middleware
- JSON responses

### Monitoring
- Metrics collection
- Performance tracking
- Event logging
- Health checks

## API Reference

### Authentication

**POST /auth/register**
```json
{
  "username": "string",
  "password": "string"
}
```

**POST /auth/login**
```json
{
  "username": "string", 
  "password": "string"
}
```

### Health

**GET /health**
```json
{
  "status": "healthy",
  "services": {},
  "metrics": {}
}
```

### Metrics

**GET /metrics**
```json
{
  "uptime": 3600,
  "memory": 45.2,
  "requests": 1234
}
```

## Configuration

```python
CONFIG = {
    'db_path': Path('data/core.db'),
    'log_path': Path('logs/core.log'),  
    'cache_ttl': 300,
    'max_workers': 10,
    'api_timeout': 30,
}
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Usage Examples

### Initialize System
```python
from core import Core

core = Core()
core.start()
```

### Create User
```python
user_id = core.auth.create_user('username', 'password')
```

### Authenticate
```python
session = core.auth.authenticate('username', 'password')
```

### Cache Operations
```python
# Set cache value
core.cache.set('key', {'data': 'value'}, ttl=300)

# Get cache value  
value = core.cache.get('key')
```

### Add API Route
```python
@core.api.route('/custom', 'GET')
def custom_handler(**kwargs):
    return {'message': 'Custom response'}
```

## Error Handling

All errors return standardized JSON:
```json
{
  "status": 500,
  "error": "Error description"
}
```

## Security Considerations

- Passwords hashed with 100,000 iterations of PBKDF2
- Session tokens use cryptographically secure random generation
- SQL queries use parameterized statements
- All inputs validated before processing
- Rate limiting on authentication endpoints