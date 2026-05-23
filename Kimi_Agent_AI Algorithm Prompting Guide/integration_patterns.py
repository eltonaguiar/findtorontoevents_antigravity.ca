#!/usr/bin/env python3
"""
Integration Patterns for Unified Signal Router
==============================================
Shows how to integrate the SignalRouter with existing trading systems.
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from pathlib import Path
import threading
import schedule

from unified_signal_router import (
    SignalRouter, DatabaseConsolidator, 
    SignalSource, ConflictResolver
)


# =============================================================================
# PATTERN 1: REAL-TIME WEBHOOK INTEGRATION
# =============================================================================

class WebhookSignalReceiver:
    """
    Receive signals via webhooks from external systems.
    Integrates with Alpha Engine, Battleground, etc.
    """
    
    def __init__(self, router: SignalRouter, port: int = 8080):
        self.router = router
        self.port = port
        self.received_count = 0
    
    def handle_signal(self, source: str, payload: Dict) -> Dict:
        """
        Handle incoming webhook signal.
        
        Example webhook payloads:
        
        Battleground:
        {
            "ticker": "BTCUSDT",
            "direction": "long",
            "strength": 0.92,
            "price": 45000,
            "sl": 43000,
            "tp": 50000,
            "tf": "1h"
        }
        
        Alpha Engine:
        {
            "pair": "ETHUSDT",
            "signal": "buy",
            "confidence": 0.78,
            "entry_price": 3200,
            "stop_loss": 3000,
            "take_profit": 3600
        }
        """
        signal = self.router.ingest_signal(payload, source)
        
        self.received_count += 1
        
        return {
            'status': 'accepted' if signal else 'rejected',
            'signal_id': signal.signal_id if signal else None,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def start_server(self):
        """Start webhook server (Flask/FastAPI example)"""
        # Flask example
        try:
            from flask import Flask, request, jsonify
            
            app = Flask(__name__)
            
            @app.route('/webhook/<source>', methods=['POST'])
            def webhook(source):
                payload = request.get_json()
                result = self.handle_signal(source, payload)
                return jsonify(result)
            
            @app.route('/health', methods=['GET'])
            def health():
                return jsonify({
                    'status': 'healthy',
                    'received_count': self.received_count
                })
            
            app.run(host='0.0.0.0', port=self.port)
            
        except ImportError:
            print("Flask not installed. Using mock server.")
            self._mock_server()
    
    def _mock_server(self):
        """Mock server for testing"""
        print(f"Mock webhook server running on port {self.port}")
        print("Endpoints:")
        print(f"  POST http://localhost:{self.port}/webhook/<source>")
        print(f"  GET  http://localhost:{self.port}/health")


# =============================================================================
# PATTERN 2: DATABASE POLLING INTEGRATION
# =============================================================================

class DatabasePoller:
    """
    Poll external SQLite databases for new signals.
    For systems that write to local databases.
    """
    
    def __init__(self, router: SignalRouter):
        self.router = router
        self.pollers: Dict[str, threading.Thread] = {}
        self.running = False
    
    def register_database(
        self,
        name: str,
        db_path: str,
        query: str,
        column_mapping: Dict[str, str],
        source: str,
        interval_seconds: int = 60
    ):
        """
        Register a database to poll.
        
        Args:
            name: Unique identifier for this poller
            db_path: Path to SQLite database
            query: SQL query to fetch new signals
            column_mapping: Map query columns to standard fields
            source: Source system name
            interval_seconds: Polling interval
        """
        def poll_loop():
            last_check = datetime.utcnow() - timedelta(hours=1)
            
            while self.running:
                try:
                    conn = sqlite3.connect(db_path)
                    
                    # Query with timestamp filter
                    query_with_filter = f"{query} AND created_at > ?"
                    cursor = conn.execute(query_with_filter, (last_check.isoformat(),))
                    
                    rows = cursor.fetchall()
                    for row in cursor.description:
                        print(f"Column: {row[0]}")
                    
                    for row in rows:
                        raw_signal = {}
                        for i, col in enumerate(cursor.description):
                            col_name = col[0]
                            if col_name in column_mapping:
                                raw_signal[column_mapping[col_name]] = row[i]
                            else:
                                raw_signal[col_name] = row[i]
                        
                        self.router.ingest_signal(raw_signal, source)
                    
                    last_check = datetime.utcnow()
                    conn.close()
                    
                except Exception as e:
                    print(f"Polling error for {name}: {e}")
                
                time.sleep(interval_seconds)
        
        self.pollers[name] = {
            'thread': None,
            'function': poll_loop,
            'interval': interval_seconds
        }
    
    def start(self):
        """Start all registered pollers"""
        self.running = True
        
        for name, config in self.pollers.items():
            thread = threading.Thread(target=config['function'], daemon=True)
            thread.start()
            config['thread'] = thread
            print(f"Started poller: {name}")
    
    def stop(self):
        """Stop all pollers"""
        self.running = False
        for name, config in self.pollers.items():
            if config['thread']:
                config['thread'].join(timeout=5)
        print("All pollers stopped")


# =============================================================================
# PATTERN 3: FILE WATCHER INTEGRATION
# =============================================================================

class FileWatcher:
    """
    Watch JSON files for new signals.
    For systems that output to files.
    """
    
    def __init__(self, router: SignalRouter):
        self.router = router
        self.watchers: Dict[str, threading.Thread] = {}
        self.running = False
        self.seen_files: set = set()
    
    def watch_directory(
        self,
        name: str,
        directory: str,
        pattern: str,
        source: str,
        interval_seconds: int = 30
    ):
        """
        Watch a directory for new JSON files.
        
        Args:
            name: Watcher identifier
            directory: Directory to watch
            pattern: File pattern (e.g., "*.json")
            source: Source system name
            interval_seconds: Check interval
        """
        def watch_loop():
            import glob
            
            while self.running:
                try:
                    files = glob.glob(f"{directory}/{pattern}")
                    
                    for filepath in files:
                        if filepath not in self.seen_files:
                            self.seen_files.add(filepath)
                            
                            with open(filepath, 'r') as f:
                                data = json.load(f)
                            
                            # Handle both single signals and arrays
                            signals = data if isinstance(data, list) else [data]
                            
                            for signal_data in signals:
                                self.router.ingest_signal(signal_data, source)
                            
                            print(f"Processed new file: {filepath}")
                    
                except Exception as e:
                    print(f"File watch error for {name}: {e}")
                
                time.sleep(interval_seconds)
        
        self.watchers[name] = {
            'thread': None,
            'function': watch_loop
        }
    
    def start(self):
        """Start all file watchers"""
        self.running = True
        
        for name, config in self.watchers.items():
            thread = threading.Thread(target=config['function'], daemon=True)
            thread.start()
            config['thread'] = thread
            print(f"Started file watcher: {name}")
    
    def stop(self):
        """Stop all watchers"""
        self.running = False
        for name, config in self.watchers.items():
            if config['thread']:
                config['thread'].join(timeout=5)
        print("All file watchers stopped")


# =============================================================================
# PATTERN 4: SCHEDULED AGGREGATION
# =============================================================================

class ScheduledAggregator:
    """
    Run aggregation on a schedule (replaces the 5-min cross-aggregator).
    """
    
    def __init__(self, router: SignalRouter):
        self.router = router
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def run_cycle(self):
        """Run a single aggregation cycle"""
        print(f"\n[{datetime.utcnow().isoformat()}] Running scheduled aggregation...")
        
        # Resolve conflicts
        resolved = self.router.resolve_conflicts()
        print(f"  Resolved {len(resolved)} conflicts")
        
        # Generate output
        output = self.router.output_consensus()
        print(f"  Generated {output['consensus_picks']} consensus picks")
        
        # Log summary
        stats = self.router.get_stats()
        print(f"  Total ingested: {stats['router_stats']['ingested']}")
        print(f"  Total output: {stats['router_stats']['output']}")
        
        return output
    
    def start(self, interval_minutes: int = 5):
        """
        Start scheduled aggregation.
        
        Args:
            interval_minutes: Aggregation interval (default 5 min to match existing)
        """
        self.running = True
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(self.run_cycle)
        
        def run_schedule():
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        self.thread = threading.Thread(target=run_schedule, daemon=True)
        self.thread.start()
        
        print(f"Scheduled aggregation started (every {interval_minutes} minutes)")
    
    def stop(self):
        """Stop scheduled aggregation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Scheduled aggregation stopped")


# =============================================================================
# PATTERN 5: MESSAGE QUEUE INTEGRATION
# =============================================================================

class MessageQueueConsumer:
    """
    Consume signals from message queues (Redis, RabbitMQ, Kafka).
    For high-throughput, distributed systems.
    """
    
    def __init__(self, router: SignalRouter):
        self.router = router
        self.consumers: Dict[str, threading.Thread] = {}
        self.running = False
    
    def consume_redis(
        self,
        name: str,
        redis_url: str,
        channel: str,
        source: str
    ):
        """
        Consume signals from Redis pub/sub.
        
        Args:
            name: Consumer identifier
            redis_url: Redis connection URL
            channel: Redis channel to subscribe
            source: Source system name
        """
        def consume_loop():
            try:
                import redis
                
                r = redis.from_url(redis_url)
                pubsub = r.pubsub()
                pubsub.subscribe(channel)
                
                print(f"Subscribed to Redis channel: {channel}")
                
                for message in pubsub.listen():
                    if not self.running:
                        break
                    
                    if message['type'] == 'message':
                        try:
                            payload = json.loads(message['data'])
                            self.router.ingest_signal(payload, source)
                        except json.JSONDecodeError:
                            print(f"Invalid JSON received: {message['data']}")
                            
            except ImportError:
                print("Redis not installed. Skipping Redis consumer.")
            except Exception as e:
                print(f"Redis consumer error: {e}")
        
        self.consumers[name] = {
            'thread': None,
            'function': consume_loop
        }
    
    def consume_rabbitmq(
        self,
        name: str,
        amqp_url: str,
        queue: str,
        source: str
    ):
        """
        Consume signals from RabbitMQ queue.
        
        Args:
            name: Consumer identifier
            amqp_url: RabbitMQ connection URL
            queue: Queue name
            source: Source system name
        """
        def consume_loop():
            try:
                import pika
                
                connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
                channel = connection.channel()
                channel.queue_declare(queue=queue, durable=True)
                
                def callback(ch, method, properties, body):
                    try:
                        payload = json.loads(body)
                        self.router.ingest_signal(payload, source)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        print(f"Message processing error: {e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag)
                
                channel.basic_consume(queue=queue, on_message_callback=callback)
                
                print(f"Consuming from RabbitMQ queue: {queue}")
                
                while self.running:
                    connection.process_data_events(time_limit=1)
                    
            except ImportError:
                print("Pika not installed. Skipping RabbitMQ consumer.")
            except Exception as e:
                print(f"RabbitMQ consumer error: {e}")
        
        self.consumers[name] = {
            'thread': None,
            'function': consume_loop
        }
    
    def start(self):
        """Start all consumers"""
        self.running = True
        
        for name, config in self.consumers.items():
            thread = threading.Thread(target=config['function'], daemon=True)
            thread.start()
            config['thread'] = thread
            print(f"Started consumer: {name}")
    
    def stop(self):
        """Stop all consumers"""
        self.running = False
        for name, config in self.consumers.items():
            if config['thread']:
                config['thread'].join(timeout=5)
        print("All consumers stopped")


# =============================================================================
# PATTERN 6: API CLIENT INTEGRATION
# =============================================================================

class APIClientIntegration:
    """
    Fetch signals from REST APIs.
    For systems that expose HTTP APIs.
    """
    
    def __init__(self, router: SignalRouter):
        self.router = router
        self.clients: Dict[str, threading.Thread] = {}
        self.running = False
    
    def poll_api(
        self,
        name: str,
        endpoint: str,
        source: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        interval_seconds: int = 60,
        response_parser: Optional[Callable] = None
    ):
        """
        Poll a REST API for signals.
        
        Args:
            name: Client identifier
            endpoint: API endpoint URL
            source: Source system name
            headers: HTTP headers
            params: Query parameters
            interval_seconds: Polling interval
            response_parser: Custom parser function
        """
        def poll_loop():
            import requests
            
            while self.running:
                try:
                    response = requests.get(
                        endpoint,
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Parse response
                    if response_parser:
                        signals = response_parser(data)
                    else:
                        signals = data if isinstance(data, list) else [data]
                    
                    for signal_data in signals:
                        self.router.ingest_signal(signal_data, source)
                    
                    print(f"Fetched {len(signals)} signals from {name}")
                    
                except Exception as e:
                    print(f"API poll error for {name}: {e}")
                
                time.sleep(interval_seconds)
        
        self.clients[name] = {
            'thread': None,
            'function': poll_loop
        }
    
    def start(self):
        """Start all API clients"""
        self.running = True
        
        for name, config in self.clients.items():
            thread = threading.Thread(target=config['function'], daemon=True)
            thread.start()
            config['thread'] = thread
            print(f"Started API client: {name}")
    
    def stop(self):
        """Stop all API clients"""
        self.running = False
        for name, config in self.clients.items():
            if config['thread']:
                config['thread'].join(timeout=5)
        print("All API clients stopped")


# =============================================================================
# COMPLETE INTEGRATION EXAMPLE
# =============================================================================

def create_integrated_system():
    """
    Create a fully integrated signal routing system.
    Demonstrates all integration patterns.
    """
    
    # Initialize router
    router = SignalRouter(
        db_path="unified_signals.db",
        conflict_window_minutes=30,
        min_confidence=0.4,
        consensus_threshold=0.5,
        output_path="live_picks.json"
    )
    
    # Configure priority order
    router.set_priority_order([
        SignalSource.BATTLEGROUND,
        SignalSource.ALPHA_ENGINE,
        SignalSource.MERCURY2,
        SignalSource.MULTI_ASSET,
        SignalSource.KIMI,
    ])
    
    # Set conflict resolver
    router.set_conflict_resolver(ConflictResolver.priority_based)
    
    # ======================================================================
    # SETUP INTEGRATION COMPONENTS
    # ======================================================================
    
    # 1. Webhook receiver (for real-time signals)
    webhook = WebhookSignalReceiver(router, port=8080)
    
    # 2. Database poller (for SQLite-based systems)
    db_poller = DatabasePoller(router)
    
    # Example: Poll Alpha Engine database
    db_poller.register_database(
        name="alpha_engine_db",
        db_path="/path/to/alpha_engine/signals.db",
        query="SELECT * FROM signals WHERE status = 'active'",
        column_mapping={
            'pair': 'symbol',
            'signal': 'direction',
            'confidence': 'confidence',
            'entry_price': 'suggested_price'
        },
        source="alpha_engine",
        interval_seconds=60
    )
    
    # 3. File watcher (for JSON file outputs)
    file_watcher = FileWatcher(router)
    
    file_watcher.watch_directory(
        name="battleground_files",
        directory="/path/to/battleground/output",
        pattern="picks_*.json",
        source="battleground",
        interval_seconds=30
    )
    
    # 4. Scheduled aggregator (replaces 5-min cross-aggregator)
    aggregator = ScheduledAggregator(router)
    
    # 5. Message queue consumer (for high-throughput)
    mq_consumer = MessageQueueConsumer(router)
    
    # Example: Redis consumer for Mercury2
    mq_consumer.consume_redis(
        name="mercury2_redis",
        redis_url="redis://localhost:6379",
        channel="mercury2:predictions",
        source="mercury2"
    )
    
    # 6. API client (for REST API sources)
    api_client = APIClientIntegration(router)
    
    # Example: Poll KIMI API
    api_client.poll_api(
        name="kimi_api",
        endpoint="https://api.kimi.example.com/v1/signals",
        source="kimi",
        headers={"Authorization": "Bearer YOUR_TOKEN"},
        interval_seconds=300
    )
    
    # ======================================================================
    # START ALL COMPONENTS
    # ======================================================================
    
    print("\n" + "=" * 60)
    print("STARTING INTEGRATED SIGNAL ROUTING SYSTEM")
    print("=" * 60)
    
    # Start webhook server in background
    # webhook_thread = threading.Thread(target=webhook.start_server, daemon=True)
    # webhook_thread.start()
    
    # Start database poller
    db_poller.start()
    
    # Start file watcher
    file_watcher.start()
    
    # Start message queue consumers
    mq_consumer.start()
    
    # Start API clients
    api_client.start()
    
    # Start scheduled aggregator (every 5 minutes)
    aggregator.start(interval_minutes=5)
    
    print("\nAll components started!")
    print("System is now routing signals from all sources...")
    print("\nPress Ctrl+C to stop")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        
        # Stop all components
        db_poller.stop()
        file_watcher.stop()
        mq_consumer.stop()
        api_client.stop()
        aggregator.stop()
        
        print("Shutdown complete!")


# =============================================================================
# CONFIGURATION TEMPLATES
# =============================================================================

INTEGRATION_CONFIG = {
    "router": {
        "db_path": "unified_signals.db",
        "conflict_window_minutes": 30,
        "min_confidence": 0.4,
        "consensus_threshold": 0.5,
        "output_path": "live_picks.json"
    },
    "priority_order": [
        "BATTLEGROUND",
        "ALPHA_ENGINE", 
        "MERCURY2",
        "MULTI_ASSET",
        "KIMI"
    ],
    "conflict_resolver": "priority_based",
    
    "sources": {
        "battleground": {
            "type": "file_watcher",
            "directory": "/data/battleground/output",
            "pattern": "*.json",
            "interval_seconds": 30
        },
        "alpha_engine": {
            "type": "database_poll",
            "db_path": "/data/alpha_engine/signals.db",
            "query": "SELECT * FROM signals WHERE status = 'active'",
            "column_mapping": {
                "pair": "symbol",
                "signal": "direction",
                "confidence": "confidence"
            },
            "interval_seconds": 60
        },
        "mercury2": {
            "type": "redis",
            "url": "redis://localhost:6379",
            "channel": "mercury2:predictions"
        },
        "multi_asset": {
            "type": "webhook",
            "port": 8080,
            "path": "/webhook/multi_asset"
        },
        "kimi": {
            "type": "api_poll",
            "endpoint": "https://api.kimi.example.com/v1/signals",
            "headers": {"Authorization": "Bearer TOKEN"},
            "interval_seconds": 300
        }
    },
    
    "aggregation": {
        "interval_minutes": 5,
        "output_formats": ["json", "database"]
    }
}


def load_config(config_path: str) -> Dict:
    """Load integration configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)


if __name__ == "__main__":
    # Run the integrated system example
    # create_integrated_system()
    
    # Or just print the configuration template
    print("Integration Configuration Template:")
    print(json.dumps(INTEGRATION_CONFIG, indent=2))
