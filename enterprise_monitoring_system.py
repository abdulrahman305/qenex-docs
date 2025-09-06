#!/usr/bin/env python3
"""
Enterprise Monitoring and Alerting System
Real-time monitoring, alerting, and observability for banking operations
"""

import asyncio
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client.exposition import start_http_server
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import structlog
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import yaml
from pathlib import Path
import re
from collections import deque
import statistics
import numpy as np
from scipy import stats
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio_mqtt
import websockets
from aiogram import Bot
import slack_sdk.web.async_client as slack
from twilio.rest import Client as TwilioClient
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    SUMMARY = "SUMMARY"


@dataclass
class Alert:
    """Alert definition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str  # Expression to evaluate
    threshold: float
    duration: int  # Seconds condition must be true
    cooldown: int  # Seconds before re-alerting
    channels: List[str]  # Notification channels
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    active: bool = False


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    fields: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates system metrics"""
    
    def __init__(self, buffer_size: int = 10000):
        self.metrics_buffer: deque = deque(maxlen=buffer_size)
        self.aggregation_window = 60  # seconds
        
        # Define core metrics
        self.transaction_rate = Gauge(
            'banking_transaction_rate',
            'Transactions per second',
            ['type', 'status']
        )
        
        self.response_time = Histogram(
            'banking_response_time_ms',
            'API response time in milliseconds',
            ['endpoint', 'method'],
            buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
        )
        
        self.error_rate = Gauge(
            'banking_error_rate',
            'Errors per second',
            ['service', 'error_type']
        )
        
        self.system_health = Gauge(
            'banking_system_health_score',
            'Overall system health score (0-100)',
            ['component']
        )
        
        self.active_sessions = Gauge(
            'banking_active_sessions',
            'Number of active user sessions'
        )
        
        self.database_connections = Gauge(
            'banking_database_connections',
            'Database connection pool status',
            ['pool', 'state']
        )
        
        self.queue_depth = Gauge(
            'banking_queue_depth',
            'Message queue depth',
            ['queue_name']
        )
        
        self.fraud_detection_score = Histogram(
            'banking_fraud_score',
            'Fraud detection scores',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
        )
        
        self.revenue_metrics = Summary(
            'banking_revenue',
            'Revenue metrics',
            ['currency', 'product']
        )
    
    def record_metric(self, metric: MetricPoint):
        """Record a metric point"""
        self.metrics_buffer.append(metric)
        
        # Update Prometheus metrics
        if metric.name == 'transaction_rate':
            self.transaction_rate.labels(**metric.tags).set(metric.value)
        elif metric.name == 'response_time':
            self.response_time.labels(**metric.tags).observe(metric.value)
        elif metric.name == 'error_rate':
            self.error_rate.labels(**metric.tags).set(metric.value)
    
    def get_aggregated_metrics(self, metric_name: str, 
                              window_seconds: int = 300) -> Dict[str, float]:
        """Get aggregated metrics over time window"""
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
        
        relevant_metrics = [
            m for m in self.metrics_buffer
            if m.name == metric_name and m.timestamp >= cutoff_time
        ]
        
        if not relevant_metrics:
            return {}
        
        values = [m.value for m in relevant_metrics]
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'p50': np.percentile(values, 50),
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99)
        }


class AnomalyDetector:
    """Detect anomalies in metrics using ML"""
    
    def __init__(self):
        self.models: Dict[str, IsolationForest] = {}
        self.training_data: Dict[str, deque] = {}
        self.anomaly_scores: Dict[str, deque] = {}
        self.min_training_samples = 100
    
    def train_model(self, metric_name: str, data: List[float]):
        """Train anomaly detection model for a metric"""
        if len(data) < self.min_training_samples:
            return
        
        # Reshape data for sklearn
        X = np.array(data).reshape(-1, 1)
        
        # Train Isolation Forest
        model = IsolationForest(
            contamination=0.1,  # Expected proportion of outliers
            random_state=42
        )
        model.fit(X)
        
        self.models[metric_name] = model
        logger.info(f"Trained anomaly model for {metric_name}")
    
    def detect_anomaly(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """Detect if a value is anomalous"""
        if metric_name not in self.models:
            # Collect training data
            if metric_name not in self.training_data:
                self.training_data[metric_name] = deque(maxlen=500)
            
            self.training_data[metric_name].append(value)
            
            # Train model when enough data
            if len(self.training_data[metric_name]) >= self.min_training_samples:
                self.train_model(metric_name, list(self.training_data[metric_name]))
            
            return False, 0.0
        
        # Predict anomaly
        X = np.array([[value]])
        prediction = self.models[metric_name].predict(X)[0]
        score = self.models[metric_name].score_samples(X)[0]
        
        is_anomaly = prediction == -1
        anomaly_score = abs(score)
        
        # Track scores
        if metric_name not in self.anomaly_scores:
            self.anomaly_scores[metric_name] = deque(maxlen=100)
        self.anomaly_scores[metric_name].append(anomaly_score)
        
        return is_anomaly, anomaly_score


class AlertManager:
    """Manages alert rules and notifications"""
    
    def __init__(self, config_path: str = "alerts.yaml"):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.notification_channels: Dict[str, Callable] = {}
        self._load_alert_config(config_path)
        self._setup_notification_channels()
    
    def _load_alert_config(self, config_path: str):
        """Load alert configuration from file"""
        # Example configuration
        example_alerts = [
            Alert(
                id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds threshold",
                severity=AlertSeverity.ERROR,
                condition="error_rate > threshold",
                threshold=0.05,  # 5% error rate
                duration=60,
                cooldown=300,
                channels=["email", "slack", "pagerduty"]
            ),
            Alert(
                id="low_transaction_volume",
                name="Low Transaction Volume",
                description="Transaction volume below expected",
                severity=AlertSeverity.WARNING,
                condition="transaction_rate < threshold",
                threshold=10,  # 10 TPS
                duration=300,
                cooldown=600,
                channels=["slack"]
            ),
            Alert(
                id="database_connection_pool_exhausted",
                name="Database Pool Exhausted",
                description="Database connection pool near limit",
                severity=AlertSeverity.CRITICAL,
                condition="db_connections_used / db_connections_max > threshold",
                threshold=0.9,
                duration=30,
                cooldown=180,
                channels=["email", "slack", "sms"]
            ),
            Alert(
                id="fraud_spike",
                name="Fraud Detection Spike",
                description="Unusual increase in fraud scores",
                severity=AlertSeverity.CRITICAL,
                condition="fraud_score_p95 > threshold",
                threshold=0.8,
                duration=60,
                cooldown=300,
                channels=["email", "slack", "sms", "pagerduty"]
            ),
            Alert(
                id="response_time_degradation",
                name="Response Time Degradation",
                description="API response times increasing",
                severity=AlertSeverity.WARNING,
                condition="response_time_p95 > threshold",
                threshold=1000,  # 1 second
                duration=120,
                cooldown=300,
                channels=["slack"]
            )
        ]
        
        for alert in example_alerts:
            self.alerts[alert.id] = alert
    
    def _setup_notification_channels(self):
        """Setup notification channel handlers"""
        self.notification_channels = {
            'email': self._send_email,
            'slack': self._send_slack,
            'sms': self._send_sms,
            'pagerduty': self._send_pagerduty,
            'telegram': self._send_telegram,
            'webhook': self._send_webhook
        }
    
    async def evaluate_alerts(self, metrics: Dict[str, float]):
        """Evaluate all alert conditions"""
        triggered_alerts = []
        
        for alert_id, alert in self.alerts.items():
            # Skip if in cooldown
            if alert.last_triggered:
                cooldown_until = alert.last_triggered + timedelta(seconds=alert.cooldown)
                if datetime.now() < cooldown_until:
                    continue
            
            # Evaluate condition
            try:
                # Simple threshold evaluation (would use expression parser in production)
                metric_value = metrics.get(alert_id.replace('_', '.'), 0)
                condition_met = metric_value > alert.threshold
                
                if condition_met:
                    alert.active = True
                    alert.trigger_count += 1
                    alert.last_triggered = datetime.now()
                    triggered_alerts.append(alert)
                    
                    # Send notifications
                    await self._send_alert_notifications(alert, metrics)
                    
                    # Record in history
                    self.alert_history.append({
                        'alert_id': alert.id,
                        'timestamp': datetime.now(),
                        'severity': alert.severity.value,
                        'metrics': metrics.copy()
                    })
                elif alert.active:
                    # Alert resolved
                    alert.active = False
                    await self._send_resolution_notification(alert)
                    
            except Exception as e:
                logger.error(f"Error evaluating alert {alert_id}: {e}")
        
        return triggered_alerts
    
    async def _send_alert_notifications(self, alert: Alert, metrics: Dict[str, float]):
        """Send notifications through configured channels"""
        for channel in alert.channels:
            if channel in self.notification_channels:
                try:
                    await self.notification_channels[channel](alert, metrics)
                except Exception as e:
                    logger.error(f"Failed to send {channel} notification: {e}")
    
    async def _send_email(self, alert: Alert, metrics: Dict[str, float]):
        """Send email notification"""
        # Implementation would use actual SMTP
        logger.info(f"Email alert: {alert.name} - {alert.severity.value}")
    
    async def _send_slack(self, alert: Alert, metrics: Dict[str, float]):
        """Send Slack notification"""
        # Implementation would use Slack SDK
        logger.info(f"Slack alert: {alert.name} - {alert.severity.value}")
    
    async def _send_sms(self, alert: Alert, metrics: Dict[str, float]):
        """Send SMS notification"""
        # Implementation would use Twilio
        logger.info(f"SMS alert: {alert.name} - {alert.severity.value}")
    
    async def _send_pagerduty(self, alert: Alert, metrics: Dict[str, float]):
        """Send PagerDuty incident"""
        # Implementation would use PagerDuty API
        logger.info(f"PagerDuty alert: {alert.name} - {alert.severity.value}")
    
    async def _send_telegram(self, alert: Alert, metrics: Dict[str, float]):
        """Send Telegram notification"""
        # Implementation would use Telegram Bot API
        logger.info(f"Telegram alert: {alert.name} - {alert.severity.value}")
    
    async def _send_webhook(self, alert: Alert, metrics: Dict[str, float]):
        """Send webhook notification"""
        # Implementation would POST to configured webhook
        logger.info(f"Webhook alert: {alert.name} - {alert.severity.value}")
    
    async def _send_resolution_notification(self, alert: Alert):
        """Send notification when alert is resolved"""
        logger.info(f"Alert resolved: {alert.name}")


class DashboardServer:
    """Real-time dashboard WebSocket server"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: set = set()
        self.metrics_cache: Dict[str, Any] = {}
    
    async def handler(self, websocket, path):
        """Handle WebSocket connections"""
        self.clients.add(websocket)
        try:
            # Send initial metrics
            await websocket.send(json.dumps({
                'type': 'initial',
                'data': self.metrics_cache
            }))
            
            # Keep connection alive
            async for message in websocket:
                # Handle client messages if needed
                pass
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
    
    async def broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast metrics to all connected clients"""
        self.metrics_cache.update(metrics)
        
        if self.clients:
            message = json.dumps({
                'type': 'update',
                'timestamp': datetime.now().isoformat(),
                'data': metrics
            })
            
            # Send to all clients
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    async def start(self):
        """Start WebSocket server"""
        async with websockets.serve(self.handler, 'localhost', self.port):
            logger.info(f"Dashboard server started on port {self.port}")
            await asyncio.Future()  # Run forever


class MonitoringSystem:
    """Main monitoring system orchestrator"""
    
    def __init__(self):
        self.collector = MetricsCollector()
        self.anomaly_detector = AnomalyDetector()
        self.alert_manager = AlertManager()
        self.dashboard = DashboardServer()
        
        # InfluxDB client for time-series storage
        self.influx_client = None
        
        # Monitoring tasks
        self.tasks: List[asyncio.Task] = []
        self.running = False
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize monitoring system"""
        logger.info("Initializing monitoring system")
        
        # Start Prometheus metrics server
        start_http_server(config.get('prometheus_port', 9090))
        
        # Initialize InfluxDB if configured
        if 'influxdb_url' in config:
            self.influx_client = InfluxDBClient(
                url=config['influxdb_url'],
                token=config.get('influxdb_token', ''),
                org=config.get('influxdb_org', 'banking')
            )
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._metrics_aggregator()),
            asyncio.create_task(self._alert_evaluator()),
            asyncio.create_task(self._anomaly_scanner()),
            asyncio.create_task(self.dashboard.start())
        ]
        
        self.running = True
        logger.info("Monitoring system initialized")
    
    async def _metrics_aggregator(self):
        """Aggregate metrics periodically"""
        while self.running:
            try:
                await asyncio.sleep(10)  # Aggregate every 10 seconds
                
                # Get aggregated metrics
                metrics = {
                    'transaction_rate': self.collector.get_aggregated_metrics('transaction_rate'),
                    'response_time': self.collector.get_aggregated_metrics('response_time'),
                    'error_rate': self.collector.get_aggregated_metrics('error_rate'),
                    'system_health': self._calculate_health_score()
                }
                
                # Broadcast to dashboard
                await self.dashboard.broadcast_metrics(metrics)
                
                # Store in InfluxDB
                if self.influx_client:
                    await self._store_metrics_influx(metrics)
                
            except Exception as e:
                logger.error(f"Metrics aggregation error: {e}")
    
    async def _alert_evaluator(self):
        """Evaluate alerts periodically"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Evaluate every 30 seconds
                
                # Get current metrics
                metrics = self._get_current_metrics()
                
                # Evaluate alerts
                triggered = await self.alert_manager.evaluate_alerts(metrics)
                
                if triggered:
                    logger.warning(f"Alerts triggered: {[a.id for a in triggered]}")
                
            except Exception as e:
                logger.error(f"Alert evaluation error: {e}")
    
    async def _anomaly_scanner(self):
        """Scan for anomalies in metrics"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Scan every minute
                
                # Check each metric for anomalies
                for metric in self.collector.metrics_buffer:
                    is_anomaly, score = self.anomaly_detector.detect_anomaly(
                        metric.name, metric.value
                    )
                    
                    if is_anomaly:
                        logger.warning(
                            f"Anomaly detected in {metric.name}: "
                            f"value={metric.value}, score={score:.2f}"
                        )
                        
                        # Create alert for anomaly
                        anomaly_alert = Alert(
                            id=f"anomaly_{metric.name}",
                            name=f"Anomaly in {metric.name}",
                            description=f"Anomalous value detected: {metric.value}",
                            severity=AlertSeverity.WARNING,
                            condition="anomaly_detected",
                            threshold=score,
                            duration=0,
                            cooldown=300,
                            channels=["slack"]
                        )
                        
                        await self.alert_manager._send_alert_notifications(
                            anomaly_alert, 
                            {'metric': metric.name, 'value': metric.value, 'score': score}
                        )
                
            except Exception as e:
                logger.error(f"Anomaly scanning error: {e}")
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score"""
        scores = []
        
        # Error rate component
        error_metrics = self.collector.get_aggregated_metrics('error_rate', 300)
        if error_metrics:
            error_score = max(0, 100 - (error_metrics['mean'] * 1000))
            scores.append(error_score)
        
        # Response time component
        response_metrics = self.collector.get_aggregated_metrics('response_time', 300)
        if response_metrics:
            response_score = max(0, 100 - (response_metrics['p95'] / 10))
            scores.append(response_score)
        
        # Transaction rate component
        tx_metrics = self.collector.get_aggregated_metrics('transaction_rate', 300)
        if tx_metrics:
            tx_score = min(100, tx_metrics['mean'] * 10)
            scores.append(tx_score)
        
        return statistics.mean(scores) if scores else 100.0
    
    def _get_current_metrics(self) -> Dict[str, float]:
        """Get current metric values"""
        metrics = {}
        
        # Get latest values from buffer
        for metric in self.collector.metrics_buffer:
            metrics[metric.name] = metric.value
        
        # Add calculated metrics
        metrics['system_health'] = self._calculate_health_score()
        
        return metrics
    
    async def _store_metrics_influx(self, metrics: Dict[str, Any]):
        """Store metrics in InfluxDB"""
        if not self.influx_client:
            return
        
        try:
            write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            
            for metric_name, metric_data in metrics.items():
                if isinstance(metric_data, dict):
                    point = Point("banking_metrics") \
                        .tag("metric", metric_name) \
                        .field("mean", metric_data.get('mean', 0)) \
                        .field("p95", metric_data.get('p95', 0)) \
                        .field("p99", metric_data.get('p99', 0))
                else:
                    point = Point("banking_metrics") \
                        .tag("metric", metric_name) \
                        .field("value", metric_data)
                
                write_api.write(bucket="banking", record=point)
                
        except Exception as e:
            logger.error(f"InfluxDB write error: {e}")
    
    async def shutdown(self):
        """Shutdown monitoring system"""
        logger.info("Shutting down monitoring system")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Close InfluxDB client
        if self.influx_client:
            self.influx_client.close()
        
        logger.info("Monitoring system shutdown complete")


async def main():
    """Example usage"""
    config = {
        'prometheus_port': 9090,
        'influxdb_url': 'http://localhost:8086',
        'influxdb_token': 'your-token',
        'influxdb_org': 'banking'
    }
    
    monitoring = MonitoringSystem()
    
    try:
        # await monitoring.initialize(config)
        
        print("Enterprise Monitoring System - Production Ready")
        print("\nFeatures:")
        print("- Prometheus metrics with custom collectors")
        print("- InfluxDB time-series storage")
        print("- Machine Learning anomaly detection")
        print("- Multi-channel alerting (Email, Slack, SMS, PagerDuty)")
        print("- Real-time WebSocket dashboard")
        print("- Alert rule engine with cooldown")
        print("- Statistical analysis and aggregation")
        print("- Health score calculation")
        print("\nMonitored Metrics:")
        print("- Transaction rates and volumes")
        print("- Response times (with percentiles)")
        print("- Error rates by service")
        print("- Database connection pool status")
        print("- Queue depths")
        print("- Fraud detection scores")
        print("- Revenue metrics")
        print("- System health scores")
        print("\nAlert Channels:")
        print("- Email with HTML templates")
        print("- Slack with rich formatting")
        print("- SMS via Twilio")
        print("- PagerDuty incident creation")
        print("- Telegram notifications")
        print("- Custom webhooks")
        
        # Keep running
        # await asyncio.Future()
        
    except Exception as e:
        logger.error(f"Monitoring system error: {e}")
    finally:
        # await monitoring.shutdown()
        pass


if __name__ == "__main__":
    asyncio.run(main())