from typing import Dict, Optional
import logging
from datetime import datetime
import psutil
import os
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import threading
from redis import Redis
import json

# System Metrics
cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('system_memory_usage_bytes', 'Memory usage in bytes')
disk_usage = Gauge('system_disk_usage_percent', 'Disk usage percentage')

# Application Metrics
api_requests = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
error_count = Counter('error_count_total', 'Total errors', ['type'])
request_duration = Histogram('request_duration_seconds', 'Request duration in seconds')

class EnterpriseMonitor:
    def __init__(self, config: Dict):
        """Initialize monitoring system"""
        self.redis = Redis.from_url(config.get('REDIS_URL', 'redis://localhost:6379'))
        self.log_path = config.get('LOG_PATH', 'logs')
        self.metrics_port = config.get('METRICS_PORT', 9090)
        self.alert_threshold = config.get('ALERT_THRESHOLD', 90)
        
        # Setup logging
        self.setup_logging()
        
        # Start metrics server
        start_http_server(self.metrics_port)
        
        # Start monitoring thread
        self.start_monitoring()

    def setup_logging(self):
        """Configure logging handlers"""
        # Application logger
        self.app_logger = logging.getLogger('app')
        self.app_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger('error')
        self.error_logger.setLevel(logging.ERROR)
        
        # Performance logger
        self.perf_logger = logging.getLogger('performance')
        self.perf_logger.setLevel(logging.INFO)
        
        # Setup handlers
        self._setup_log_handlers()

    def _setup_log_handlers(self):
        """Setup individual log handlers"""
        handlers = {
            'app': logging.FileHandler(f"{self.log_path}/app.log"),
            'error': logging.FileHandler(f"{self.log_path}/error.log"),
            'performance': logging.FileHandler(f"{self.log_path}/performance.log")
        }
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        for handler in handlers.values():
            handler.setFormatter(formatter)
            
        self.app_logger.addHandler(handlers['app'])
        self.error_logger.addHandler(handlers['error'])
        self.perf_logger.addHandler(handlers['performance'])

    def start_monitoring(self):
        """Start system monitoring thread"""
        def monitor_system():
            while True:
                try:
                    # Update system metrics
                    cpu_usage.set(psutil.cpu_percent())
                    memory = psutil.virtual_memory()
                    memory_usage.set(memory.used)
                    disk = psutil.disk_usage('/')
                    disk_usage.set(disk.percent)
                    
                    # Check thresholds and alert if necessary
                    self._check_alerts({
                        'cpu': psutil.cpu_percent(),
                        'memory': memory.percent,
                        'disk': disk.percent
                    })
                    
                    # Store metrics in Redis
                    self._store_metrics()
                    
                except Exception as e:
                    self.error_logger.error(f"Monitoring error: {str(e)}")
                
                time.sleep(60)  # Update every minute
        
        threading.Thread(target=monitor_system, daemon=True).start()

    def _check_alerts(self, metrics: Dict):
        """Check metrics against thresholds"""
        for metric, value in metrics.items():
            if value > self.alert_threshold:
                self.error_logger.warning(
                    f"Alert: {metric} usage above threshold: {value}%"
                )
                self._send_alert(metric, value)

    def _store_metrics(self):
        """Store current metrics in Redis"""
        current_metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'active_threads': threading.active_count()
        }
        
        self.redis.lpush('system_metrics', json.dumps(current_metrics))
        # Keep only last 24 hours of metrics
        self.redis.ltrim('system_metrics', 0, 1440)

    def log_request(self, endpoint: str, method: str, duration: float):
        """Log API request"""
        api_requests.labels(endpoint=endpoint, method=method).inc()
        request_duration.observe(duration)
        
        self.perf_logger.info(
            f"Request: {method} {endpoint} - Duration: {duration:.2f}s"
        )

    def log_error(self, error_type: str, error_message: str):
        """Log error with details"""
        error_count.labels(type=error_type).inc()
        self.error_logger.error(f"Error ({error_type}): {error_message}")

    def get_system_health(self) -> Dict:
        """Get current system health metrics"""
        return {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'active_threads': threading.active_count(),
            'timestamp': datetime.utcnow().isoformat()
        }