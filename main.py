import os
import streamlit as st
import yaml
from streamlit_authenticator import Authenticate
from yaml.loader import SafeLoader
import logging
import shutil
from dotenv import dotenv_values
from pathlib import Path
from detectaicore import (
    set_up_logging,
)
from datetime import datetime, timedelta
import jwt
import logging
from typing import Dict, Optional
from redis import Redis
import hashlib
import os
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import Counter, Gauge
from src.monitoring import EnterpriseMonitor
from src.governance import DataGovernance
from src.high_availability import HighAvailabilityManager

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

def main(config):
    """Main page APP with enhanced security"""
    try:
        # Initialize auth manager
        auth_manager = EnterpriseAuthManager(config)
        
        # Setup Streamlit
        st.set_page_config(layout="wide", initial_sidebar_state="expanded")
        
        # Initialize session state
        for key in ["authentication_status", "name", "username", "session_id"]:
            if key not in st.session_state:
                st.session_state[key] = None

        st.title("Enterprise Document Processing System")

        # Check existing session
        if st.session_state["session_id"]:
            session = auth_manager.validate_session(st.session_state["session_id"])
            if not session:
                st.session_state["authentication_status"] = None
                st.session_state["session_id"] = None

        # Handle authentication
        if st.session_state["authentication_status"] is None:
            authenticator.login(key="Login", location="main")
            
            if st.session_state["authentication_status"]:
                # Get enhanced session token
                auth_result = auth_manager.authenticate_user(
                    st.session_state["username"],
                    st.session_state["password"]
                )
                
                if auth_result:
                    st.session_state["session_id"] = auth_result["token"]
                    st.write(f'Welcome *{auth_result["user"]["username"]}*')
                else:
                    st.session_state["authentication_status"] = False
                    st.error("Authentication failed")

        elif st.session_state["authentication_status"]:
            if st.button("Logout"):
                auth_manager.logout(st.session_state["session_id"])
                st.session_state["authentication_status"] = None
                st.session_state["session_id"] = None
                st.experimental_rerun()

    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        st.error("An error occurred. Please try again.")


if __name__ == "__main__":
    # setup environtment
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUT_FOLDER = os.path.join(ROOT_DIR, "out")
    TMP_FOLDER = os.path.join(ROOT_DIR, "tmp")
    ANSWERS_FOLDER = os.path.join(ROOT_DIR, "answers")
    SAVE_FOLDER = os.path.join(ROOT_DIR, "saves")
    # logging
    # Set up logging
    LOGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

    Path(LOGS_PATH).mkdir(parents=True, exist_ok=True)
    script_name = os.path.join(LOGS_PATH, "debug.log")
    # create loggers
    if not set_up_logging(
        console_log_output="stdout",
        console_log_level="info",
        console_log_color=True,
        logfile_file=script_name,
        logfile_log_level="info",
        logfile_log_color=False,
        log_line_template="%(color_on)s[%(asctime)s] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s",
    ):
        print("Failed to set up logging, aborting.")
        raise AttributeError("failed to create logging")
    # create folders if they don't exist
    os.makedirs(OUT_FOLDER, exist_ok=True)
    os.makedirs(TMP_FOLDER, exist_ok=True)
    os.makedirs(ANSWERS_FOLDER, exist_ok=True)
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    # read env file
    config = dotenv_values(os.path.join(ROOT_DIR, "keys", ".env"))

    # key access NVIDIA NIM
    if "NVIDIA_API_KEY" not in os.environ:
        os.environ["NVIDIA_API_KEY"] = config.get("NVIDIA_API_KEY")
    with open("keys/config.yaml") as file:
        auth = yaml.load(file, Loader=SafeLoader)

    # Initialize monitoring
    monitoring_config = {
        'METRICS_PORT': int(config.get('METRICS_PORT', 9090)),
        'LOG_PATH': config.get('LOG_PATH', 'logs'),
        'ALERT_THRESHOLD': int(config.get('ALERT_THRESHOLD', 90)),
        'REDIS_URL': config.get('REDIS_URL', 'redis://localhost:6379')
    }

    monitor = EnterpriseMonitor(monitoring_config)

    # Initialize data governance
    governance_config = {
        'ENCRYPTION_KEY': config.get('ENCRYPTION_KEY'),
        'DOC_RETENTION_DAYS': int(config.get('DOC_RETENTION_DAYS', 365)),
        'AUDIT_RETENTION_DAYS': int(config.get('AUDIT_RETENTION_DAYS', 730)),
        'USER_DATA_RETENTION_DAYS': int(config.get('USER_DATA_RETENTION_DAYS', 365)),
        'REDIS_URL': config.get('REDIS_URL'),
        'MONGODB_URL': config.get('MONGODB_URL')
    }

    governance = DataGovernance(governance_config)

    # Initialize HA manager
    ha_config = {
        'SENTINEL_HOSTS': [
            (host.split(':')[0], int(host.split(':')[1])) 
            for host in config.get('SENTINEL_HOSTS', '').split(',')
        ],
        'REDIS_CLUSTER_URL': config.get('REDIS_CLUSTER_URL'),
        'MONGODB_URL': config.get('MONGODB_URL'),
        'MONGODB_REPLICA_SET': config.get('MONGODB_REPLICA_SET'),
        'FAILOVER_TIMEOUT': int(config.get('FAILOVER_TIMEOUT', 30))
    }

    ha_manager = HighAvailabilityManager(ha_config)

    main(config=auth)
