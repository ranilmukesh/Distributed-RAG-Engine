from datetime import datetime, timedelta
import jwt
import logging
from typing import Dict, Optional
from redis import Redis
import hashlib
import os
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import Counter, Gauge

# Metrics
login_attempts = Counter('login_attempts_total', 'Total login attempts')
active_sessions = Gauge('active_sessions', 'Number of active sessions')
auth_failures = Counter('auth_failures_total', 'Number of authentication failures')

class EnterpriseAuthManager:
    def __init__(self, config: Dict):
        """Initialize auth manager with enterprise features"""
        self.redis = Redis.from_url(config.get('REDIS_URL', 'redis://localhost:6379'))
        self.mongo = AsyncIOMotorClient(config.get('MONGODB_URL', 'mongodb://localhost:27017'))
        self.db = self.mongo.enterprise_auth
        self.jwt_secret = config.get('JWT_SECRET_KEY', os.urandom(32).hex())
        self.session_timeout = int(config.get('SESSION_TIMEOUT', 28800))  # 8 hours default

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Enhanced user authentication"""
        try:
            login_attempts.inc()
            
            # Hash password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Check user in MongoDB
            user = await self.db.users.find_one({
                'username': username,
                'password': hashed_password,
                'active': True
            })
            
            if not user:
                auth_failures.inc()
                logging.warning(f"Failed login attempt for user: {username}")
                return None
                
            # Generate session token
            session_token = self._generate_session_token(user)
            
            # Store session in Redis
            await self._store_session(session_token, user)
            
            active_sessions.inc()
            
            return {
                'token': session_token,
                'user': {
                    'username': user['username'],
                    'roles': user.get('roles', []),
                    'permissions': user.get('permissions', [])
                }
            }
            
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")
            return None

    def _generate_session_token(self, user: Dict) -> str:
        """Generate JWT session token"""
        payload = {
            'user_id': str(user['_id']),
            'username': user['username'],
            'roles': user.get('roles', []),
            'exp': datetime.utcnow() + timedelta(seconds=self.session_timeout)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    async def _store_session(self, token: str, user: Dict):
        """Store session in Redis"""
        session_key = f"session:{token}"
        session_data = {
            'user_id': str(user['_id']),
            'username': user['username'],
            'created_at': datetime.utcnow().isoformat()
        }
        self.redis.setex(session_key, self.session_timeout, str(session_data))

    async def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session token"""
        try:
            # Verify JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check Redis session
            session_key = f"session:{token}"
            if not self.redis.exists(session_key):
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            active_sessions.dec()
            return None
        except Exception as e:
            logging.error(f"Session validation error: {str(e)}")
            return None

    async def logout(self, token: str):
        """Handle user logout"""
        try:
            session_key = f"session:{token}"
            if self.redis.delete(session_key):
                active_sessions.dec()
                
        except Exception as e:
            logging.error(f"Logout error: {str(e)}")
