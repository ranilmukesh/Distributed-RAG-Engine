from typing import Dict, Optional, List
import jwt
from datetime import datetime, timedelta
import hashlib
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis
from cryptography.fernet import Fernet

class EnterpriseSecurityManager:
    def __init__(self, config: Dict):
        """
        Initialize security manager
        Args:
            config: Security configuration containing:
                - secret_key: JWT secret key
                - mongodb_url: MongoDB connection URL
                - redis_url: Redis connection URL
                - encryption_key: Fernet encryption key
        """
        self.secret_key = config['secret_key']
        self.mongo = AsyncIOMotorClient(config['mongodb_url'])
        self.redis = Redis.from_url(config['redis_url'])
        self.cipher = Fernet(config['encryption_key'])
        
        # Initialize audit logging
        self.audit_logger = logging.getLogger('audit')
        
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with enhanced security
        """
        try:
            # Hash password before comparison
            hashed_password = self._hash_password(password)
            
            # Check user credentials
            user = await self.mongo.users.find_one({
                'username': username,
                'password': hashed_password
            })
            
            if user:
                # Generate JWT token
                token = self._generate_token(user)
                
                # Log successful login
                self._audit_log('login_success', username)
                
                return {
                    'status': 'success',
                    'token': token,
                    'permissions': user.get('permissions', [])
                }
            
            self._audit_log('login_failure', username)
            return None
            
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")
            return None

    def _generate_token(self, user: Dict) -> str:
        """Generate JWT token with role-based claims"""
        payload = {
            'user_id': str(user['_id']),
            'username': user['username'],
            'roles': user.get('roles', []),
            'exp': datetime.utcnow() + timedelta(hours=8)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    async def verify_document_access(self, user_id: str, document_id: str) -> bool:
        """
        Verify user's access to document
        """
        try:
            # Get user permissions
            user = await self.mongo.users.find_one({'_id': user_id})
            if not user:
                return False
                
            # Get document metadata
            doc = await self.mongo.documents.find_one({'_id': document_id})
            if not doc:
                return False
                
            # Check access level
            required_access = doc.get('access_level', 'public')
            user_access = user.get('access_level', 'public')
            
            has_access = self._check_access_level(required_access, user_access)
            
            # Audit log access attempt
            self._audit_log(
                'document_access',
                user['username'],
                {'document_id': document_id, 'granted': has_access}
            )
            
            return has_access
            
        except Exception as e:
            logging.error(f"Access verification error: {str(e)}")
            return False

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def _audit_log(self, action: str, user: str, details: Dict = None):
        """
        Create detailed audit log
        """
        log_entry = {
            'timestamp': datetime.utcnow(),
            'action': action,
            'user': user,
            'ip_address': self._get_client_ip(),
            'details': details or {}
        }
        self.audit_logger.info(str(log_entry))
        
        # Store in MongoDB for compliance
        self.mongo.audit_logs.insert_one(log_entry)
