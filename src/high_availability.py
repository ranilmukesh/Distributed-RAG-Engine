from typing import Dict, List, Optional
import logging
from redis.sentinel import Sentinel
from redis.cluster import RedisCluster
from motor.motor_asyncio import AsyncIOMotorClient
from prometheus_client import Counter, Gauge
import asyncio
from datetime import datetime
import socket

# HA metrics
failover_events = Counter('failover_events_total', 'Total failover events')
node_status = Gauge('node_status', 'Node status', ['node_type', 'node_id'])
replication_lag = Gauge('replication_lag_seconds', 'Replication lag in seconds')

class HighAvailabilityManager:
    def __init__(self, config: Dict):
        """Initialize HA manager"""
        self.config = config
        self.active_node = None
        self.standby_nodes = []
        
        # Initialize Redis Sentinel
        sentinel_hosts = [(host, port) for host, port in config.get('SENTINEL_HOSTS', [])]
        self.sentinel = Sentinel(sentinel_hosts, socket_timeout=0.1)
        
        # Initialize Redis Cluster
        self.redis_cluster = RedisCluster.from_url(config.get('REDIS_CLUSTER_URL'))
        
        # Initialize MongoDB replica set
        self.mongo = AsyncIOMotorClient(
            config.get('MONGODB_URL'),
            replicaSet=config.get('MONGODB_REPLICA_SET')
        )
        
        # Start health check loop
        asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self):
        """Continuous health check of all nodes"""
        while True:
            try:
                await self._check_node_health()
                await self._check_replication_status()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logging.error(f"Health check error: {str(e)}")

    async def _check_node_health(self):
        """Check health of all nodes"""
        for node_type in ['primary', 'secondary']:
            try:
                # Check MongoDB nodes
                mongo_status = await self.mongo.admin.command('replSetGetStatus')
                for member in mongo_status['members']:
                    node_status.labels(
                        node_type='mongodb',
                        node_id=member['name']
                    ).set(1 if member['health'] == 1 else 0)

                # Check Redis nodes
                redis_master = self.sentinel.discover_master('mymaster')
                redis_slaves = self.sentinel.discover_slaves('mymaster')
                
                node_status.labels(
                    node_type='redis',
                    node_id=f"{redis_master[0]}:{redis_master[1]}"
                ).set(1)
                
                for slave in redis_slaves:
                    node_status.labels(
                        node_type='redis',
                        node_id=f"{slave[0]}:{slave[1]}"
                    ).set(1)

            except Exception as e:
                logging.error(f"Node health check error: {str(e)}")
                node_status.labels(node_type=node_type, node_id='unknown').set(0)

    async def handle_failover(self, failed_node: str):
        """Handle node failover"""
        try:
            failover_events.inc()
            logging.warning(f"Initiating failover for node: {failed_node}")
            
            if failed_node.startswith('redis'):
                # Redis failover
                self.sentinel.failover('mymaster')
            
            # Update metrics and notify monitoring
            await self._notify_failover(failed_node)
            
        except Exception as e:
            logging.error(f"Failover error: {str(e)}")

    async def get_active_node(self) -> Dict:
        """Get current active node information"""
        try:
            mongo_status = await self.mongo.admin.command('replSetGetStatus')
            redis_master = self.sentinel.discover_master('mymaster')
            
            return {
                'mongodb_primary': next(
                    m['name'] for m in mongo_status['members'] 
                    if m['stateStr'] == 'PRIMARY'
                ),
                'redis_master': f"{redis_master[0]}:{redis_master[1]}"
            }
            
        except Exception as e:
            logging.error(f"Error getting active node: {str(e)}")
            return {}

    async def _check_replication_status(self):
        """Check replication status and lag"""
        try:
            # Check MongoDB replication lag
            mongo_status = await self.mongo.admin.command('replSetGetStatus')
            for member in mongo_status['members']:
                if member['stateStr'] == 'SECONDARY':
                    lag = member.get('optimeDate', 0)
                    replication_lag.labels(
                        node_type='mongodb',
                        node_id=member['name']
                    ).set(lag)

            # Check Redis replication lag
            redis_info = self.redis_cluster.info()
            for node_id, info in redis_info.items():
                if info.get('role') == 'slave':
                    lag = info.get('master_last_io_seconds_ago', 0)
                    replication_lag.labels(
                        node_type='redis',
                        node_id=node_id
                    ).set(lag)

        except Exception as e:
            logging.error(f"Replication check error: {str(e)}") 