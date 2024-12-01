from typing import Dict, List, Optional
from datetime import datetime
import logging
from redis import Redis
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import Counter
import hashlib
import json
from cryptography.fernet import Fernet

# Governance metrics
data_access_events = Counter('data_access_total', 'Total data access events', ['action'])
compliance_violations = Counter('compliance_violations_total', 'Total compliance violations', ['type'])
retention_events = Counter('retention_events_total', 'Data retention events')

class DataGovernance:
    def __init__(self, config: Dict):
        """Initialize data governance system"""
        self.redis = Redis.from_url(config.get('REDIS_URL', 'redis://localhost:6379'))
        self.mongo = AsyncIOMotorClient(config.get('MONGODB_URL', 'mongodb://localhost:27017'))
        self.db = self.mongo.governance
        
        # Initialize encryption
        self.cipher = Fernet(config['ENCRYPTION_KEY'].encode())
        
        # Configure retention policies
        self.retention_policies = {
            'document': config.get('DOC_RETENTION_DAYS', 365),
            'audit_logs': config.get('AUDIT_RETENTION_DAYS', 730),
            'user_data': config.get('USER_DATA_RETENTION_DAYS', 365)
        }

    async def track_data_access(self, user_id: str, data_id: str, action: str):
        """Track data access events"""
        access_event = {
            'user_id': user_id,
            'data_id': data_id,
            'action': action,
            'timestamp': datetime.utcnow(),
            'ip_address': self._get_client_ip()
        }
        
        await self.db.access_logs.insert_one(access_event)
        data_access_events.labels(action=action).inc()

    async def enforce_retention_policy(self, data_type: str):
        """Enforce data retention policies"""
        retention_days = self.retention_policies.get(data_type)
        if not retention_days:
            return
            
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        result = await self.db[data_type].delete_many({
            'created_at': {'$lt': cutoff_date}
        })
        
        retention_events.inc()
        logging.info(f"Removed {result.deleted_count} expired {data_type} records")

    def encrypt_sensitive_data(self, data: Dict) -> Dict:
        """Encrypt sensitive fields in data"""
        sensitive_fields = ['ssn', 'credit_card', 'password']
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data:
                encrypted_data[field] = self.cipher.encrypt(
                    str(encrypted_data[field]).encode()
                ).decode()
                
        return encrypted_data

    def decrypt_sensitive_data(self, data: Dict) -> Dict:
        """Decrypt sensitive fields in data"""
        sensitive_fields = ['ssn', 'credit_card', 'password']
        decrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in decrypted_data:
                decrypted_data[field] = self.cipher.decrypt(
                    decrypted_data[field].encode()
                ).decode()
                
        return decrypted_data

    async def validate_compliance(self, document: Dict) -> bool:
        """Validate document compliance"""
        try:
            # Check required fields
            required_fields = ['owner', 'classification', 'retention_period']
            for field in required_fields:
                if field not in document:
                    compliance_violations.labels(type='missing_field').inc()
                    return False
            
            # Check classification level
            valid_classifications = ['public', 'internal', 'confidential', 'restricted']
            if document['classification'] not in valid_classifications:
                compliance_violations.labels(type='invalid_classification').inc()
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"Compliance validation error: {str(e)}")
            return False

    async def get_data_lineage(self, data_id: str) -> List[Dict]:
        """Get data lineage information"""
        return await self.db.data_lineage.find({
            'data_id': data_id
        }).sort('timestamp', 1).to_list(None)

    def _get_client_ip(self) -> str:
        """Get client IP address"""
        # Implement your IP detection logic here
        return "0.0.0.0" 