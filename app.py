from flask import Flask, jsonify, request, render_template
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import logging
import logging.config
from datetime import datetime
import time
import threading
import json
import os
import pytz
from config import settings
from monitoring.monitor import HostMonitor
from monitoring.notifier import Notifier

# Configure logging
logging.config.dictConfig(settings.LOGGING_CONFIG)
logger = logging.getLogger('monitoring')

app = Flask(__name__)

# Timezone helper functions
def get_local_timezone():
    """Get the configured local timezone"""
    timezone_str = os.getenv('TIMEZONE', 'UTC')
    try:
        return pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone: {timezone_str}, defaulting to UTC")
        return pytz.UTC

def format_datetime_for_api(dt):
    """Format datetime for API responses"""
    if dt is None:
        return None
    
    timezone = get_local_timezone()
    
    # If datetime is naive (no timezone), assume UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    # Convert to local timezone
    local_dt = dt.astimezone(timezone)
    return local_dt.isoformat()

def format_datetime_string_for_api(dt_str):
    """Format datetime string for API responses"""
    if not dt_str:
        return None
    
    try:
        # Try to parse the datetime string
        if 'T' in dt_str:
            # ISO format with T
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            # Try other common formats
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        
        return format_datetime_for_api(dt)
    except Exception as e:
        logger.error(f"Error parsing datetime {dt_str}: {str(e)}")
        return dt_str

# Initialize components with error handling
try:
    monitor = HostMonitor('config/hosts.yaml')
    notifier = Notifier()
    logger.info("Components initialized successfully")
    logger.info(f"Timezone configured: {os.getenv('TIMEZONE', 'UTC')}")
except Exception as e:
    logger.error(f"Failed to initialize components: {str(e)}")
    # Create minimal components for API to work
    monitor = None
    notifier = None

class MonitoringThread(threading.Thread):
    """Background thread for continuous monitoring"""
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
    
    def run(self):
        logger.info("Starting monitoring thread")
        while self.running:
            try:
                if monitor is None:
                    logger.error("Monitor not initialized, skipping check")
                    time.sleep(30)
                    continue
                
                status_changes = monitor.monitor_all_hosts()
                
                if notifier and status_changes:
                    for change in status_changes:
                        if change['new_status'] == 'down':
                            logger.warning(f"Host {change['host']['name']} is down")
                            notifier.send_downtime_alerts(change['host'], change['timestamp'])
                        elif change['new_status'] == 'up' and change['previous_status'] == 'down':
                            logger.info(f"Host {change['host']['name']} is back online")
                            notifier.send_resolved_alerts(change['host'], change['timestamp'])
                
                # Wait for next check
                time.sleep(settings.CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitoring thread: {str(e)}")
                time.sleep(30)
    
    def stop(self):
        self.running = False

# Start monitoring thread if components are initialized
if monitor and notifier:
    monitoring_thread = MonitoringThread()
    monitoring_thread.start()
    logger.info("Monitoring thread started")
else:
    monitoring_thread = None
    logger.warning("Monitoring thread not started due to initialization errors")

@app.route('/')
def index():
    """Root endpoint - returns service status"""
    current_time = format_datetime_for_api(datetime.now())
    return jsonify({
        'service': 'Server Monitoring System',
        'status': 'running',
        'monitored_hosts': len(monitor.hosts) if monitor else 0,
        'timezone': os.getenv('TIMEZONE', 'UTC'),
        'current_time': current_time,
        'api_endpoints': {
            'status': '/status',
            'health': '/health',
            'hosts': '/hosts',
            'manual_check': '/check/<host_index>',
            'test_alert': '/test-alert/<alert_type>',
            'dashboard': '/dashboard',
            'api_summary': '/api/summary',
            'time': '/time',
            'monitoring_start': '/monitoring/start (POST)',
            'monitoring_stop': '/monitoring/stop (POST)',
            'monitoring_status': '/monitoring/status',
            'monitoring_config': '/monitoring/config',
            'force_check': '/monitoring/force-check (POST)',
            'history': '/monitoring/history',
            'metrics': '/monitoring/metrics'
        }
    })

@app.route('/status')
def get_status():
    """Get current status of all monitored hosts"""
    if monitor is None:
        return jsonify({
            'error': 'Monitor not initialized',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 500
    
    # Use the monitor's method to get proper status
    summary = monitor.get_host_status_summary()
    
    # Format timestamps in response
    formatted_hosts = []
    for host in summary['hosts']:
        host_copy = host.copy()
        # Format datetime fields
        for field in ['last_check', 'last_status_change', 'downtime_start']:
            if host_copy.get(field):
                # Check if it's already a datetime object or a string
                if isinstance(host_copy[field], str):
                    host_copy[field] = format_datetime_string_for_api(host_copy[field])
                else:
                    host_copy[field] = format_datetime_for_api(host_copy[field])
        formatted_hosts.append(host_copy)
    
    return jsonify({
        'timestamp': format_datetime_for_api(datetime.now()),
        'timezone': os.getenv('TIMEZONE', 'UTC'),
        'summary': {
            'total_hosts': summary['total_hosts'],
            'up_hosts': summary['up_hosts'],
            'down_hosts': summary['down_hosts'],
            'unknown_hosts': summary['unknown_hosts']
        },
        'hosts': formatted_hosts
    })

@app.route('/health')
def health_check():
    """Health check endpoint for load balancers"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': format_datetime_for_api(datetime.now()),
        'timezone': os.getenv('TIMEZONE', 'UTC')
    })

@app.route('/hosts')
def list_hosts():
    """List all monitored hosts"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
    return jsonify(monitor.hosts)

@app.route('/check/<int:host_index>')
def manual_check(host_index):
    """Manually check a specific host"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
        
    if 0 <= host_index < len(monitor.hosts):
        host = monitor.hosts[host_index]
        is_up = monitor.check_host(host)
        return jsonify({
            'host': host['name'],
            'status': 'up' if is_up else 'down',
            'timestamp': format_datetime_for_api(datetime.now()),
            'timezone': os.getenv('TIMEZONE', 'UTC')
        })
    return jsonify({'error': 'Invalid host index'}), 404

@app.route('/test-alert/<alert_type>')
def test_alert(alert_type):
    """Test alert functionality (for testing only)"""
    if notifier is None:
        return jsonify({'error': 'Notifier not initialized'}), 500
        
    if alert_type == 'downtime':
        test_host = monitor.hosts[0] if monitor and monitor.hosts else {
            'name': 'Test Server',
            'hostname': 'test.example.com',
            'ip_address': '127.0.0.1'
        }
        current_time = datetime.now()
        logger.info(f"Testing downtime alert at {format_datetime_for_api(current_time)}")
        notifier.send_downtime_alerts(test_host, current_time)
        return jsonify({
            'message': 'Test downtime alert sent',
            'timestamp': format_datetime_for_api(current_time),
            'timezone': os.getenv('TIMEZONE', 'UTC')
        })
    
    elif alert_type == 'resolved':
        test_host = monitor.hosts[0] if monitor and monitor.hosts else {
            'name': 'Test Server',
            'hostname': 'test.example.com',
            'ip_address': '127.0.0.1'
        }
        current_time = datetime.now()
        logger.info(f"Testing resolved alert at {format_datetime_for_api(current_time)}")
        notifier.send_resolved_alerts(test_host, current_time)
        return jsonify({
            'message': 'Test resolved alert sent',
            'timestamp': format_datetime_for_api(current_time),
            'timezone': os.getenv('TIMEZONE', 'UTC')
        })
    
    return jsonify({'error': 'Invalid alert type'}), 400

@app.route('/dashboard')
def dashboard():
    """Serve the monitoring dashboard"""
    return render_template('dashboard.html')

@app.route('/api/summary')
def api_summary():
    """API endpoint for dashboard data"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    summary = monitor.get_host_status_summary()
    
    # Format timestamps for dashboard
    formatted_hosts = []
    for host in summary['hosts']:
        host_copy = host.copy()
        # Format datetime fields for dashboard
        for field in ['last_check', 'last_status_change', 'downtime_start']:
            if host_copy.get(field):
                if isinstance(host_copy[field], str):
                    host_copy[field] = format_datetime_string_for_api(host_copy[field])
                else:
                    host_copy[field] = format_datetime_for_api(host_copy[field])
        formatted_hosts.append(host_copy)
    
    return jsonify({
        'timestamp': format_datetime_for_api(datetime.now()),
        'timezone': os.getenv('TIMEZONE', 'UTC'),
        'summary': {
            'total': summary['total_hosts'],
            'up': summary['up_hosts'],
            'down': summary['down_hosts'],
            'unknown': summary['unknown_hosts']
        },
        'hosts': formatted_hosts
    })

@app.route('/time')
def get_time():
    """Endpoint to check current time in different timezones"""
    now = datetime.now(pytz.UTC)
    timezones = ['UTC', os.getenv('TIMEZONE', 'UTC'), 'Africa/Lagos', 'Europe/London', 'America/New_York']
    
    times = {}
    for tz in timezones:
        try:
            zone = pytz.timezone(tz)
            times[tz] = now.astimezone(zone).strftime('%Y-%m-%d %H:%M:%S %Z')
        except:
            times[tz] = "Invalid timezone"
    
    return jsonify({
        'server_time_utc': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'configured_timezone': os.getenv('TIMEZONE', 'UTC'),
        'times': times,
        'timestamp': format_datetime_for_api(datetime.now())
    })

@app.route('/monitoring/start', methods=['POST'])
def start_monitoring_endpoint():
    """Start the monitoring thread"""
    global monitoring_thread  # Needed because we assign a new value
    
    if monitoring_thread and monitoring_thread.is_alive():
        return jsonify({
            'message': 'Monitoring is already running',
            'status': 'running',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 200
    
    if monitor is None or notifier is None:
        return jsonify({
            'error': 'Monitor or notifier not initialized',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 500
    
    monitoring_thread = MonitoringThread()
    monitoring_thread.start()
    
    logger.info("Monitoring started via API")
    return jsonify({
        'message': 'Monitoring started',
        'status': 'started',
        'timestamp': format_datetime_for_api(datetime.now())
    }), 200

@app.route('/monitoring/stop', methods=['POST'])
def stop_monitoring_endpoint():
    """Stop the monitoring thread"""
    # No 'global' needed here - we're only reading, not assigning
    
    if monitoring_thread and monitoring_thread.is_alive():
        monitoring_thread.stop()
        monitoring_thread.join(timeout=5)
        
        logger.info("Monitoring stopped via API")
        return jsonify({
            'message': 'Monitoring stopped',
            'status': 'stopped',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 200
    
    return jsonify({
        'message': 'Monitoring is not running',
        'status': 'stopped',
        'timestamp': format_datetime_for_api(datetime.now())
    }), 200

@app.route('/monitoring/status')
def monitoring_status():
    """Get monitoring thread status"""
    thread_status = {
        'running': monitoring_thread.is_alive() if monitoring_thread else False,
        'thread_name': monitoring_thread.name if monitoring_thread else None,
        'daemon': monitoring_thread.daemon if monitoring_thread else None
    }
    
    return jsonify({
        'monitoring': thread_status,
        'check_interval': settings.CHECK_INTERVAL,
        'timestamp': format_datetime_for_api(datetime.now()),
        'components': {
            'monitor_initialized': monitor is not None,
            'notifier_initialized': notifier is not None,
            'hosts_loaded': len(monitor.hosts) if monitor else 0
        }
    })

@app.route('/monitoring/config', methods=['GET'])
def get_monitoring_config():
    """Get current monitoring configuration"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    config = {
        'check_interval': settings.CHECK_INTERVAL,
        'max_retries': settings.MAX_RETRIES,
        'retry_delay': settings.RETRY_DELAY,
        'timeout': settings.TIMEOUT,
        'config_file': monitor.config_file,
        'timestamp': format_datetime_for_api(datetime.now())
    }
    
    return jsonify(config)

@app.route('/monitoring/force-check', methods=['POST'])
def force_check_all():
    """Force immediate check of all hosts"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    try:
        # Get the request data to see if we should send alerts
        data = request.get_json() or {}
        send_alerts = data.get('send_alerts', True)
        
        logger.info(f"Force checking all hosts (send_alerts={send_alerts})")
        start_time = time.time()
        
        # Perform the check
        if send_alerts and notifier is not None:
            status_changes = monitor.monitor_all_hosts()
            
            # Send alerts for status changes
            if status_changes:
                for change in status_changes:
                    if change['new_status'] == 'down':
                        logger.warning(f"Host {change['host']['name']} is down")
                        notifier.send_downtime_alerts(change['host'], change['timestamp'])
                    elif change['new_status'] == 'up' and change['previous_status'] == 'down':
                        logger.info(f"Host {change['host']['name']} is back online")
                        notifier.send_resolved_alerts(change['host'], change['timestamp'])
        else:
            # Just check without sending alerts
            monitor.monitor_all_hosts()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Get updated status
        summary = monitor.get_host_status_summary()
        
        return jsonify({
            'message': 'Force check completed',
            'duration_seconds': round(duration, 2),
            'hosts_checked': summary['total_hosts'],
            'up_hosts': summary['up_hosts'],
            'down_hosts': summary['down_hosts'],
            'alerts_sent': send_alerts,
            'timestamp': format_datetime_for_api(datetime.now())
        })
        
    except Exception as e:
        logger.error(f"Error during force check: {str(e)}")
        return jsonify({
            'error': f'Force check failed: {str(e)}',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 500

@app.route('/monitoring/history')
def get_monitoring_history():
    """Get monitoring history (if implemented in monitor)"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    try:
        # Check if monitor has get_history method
        if hasattr(monitor, 'get_history'):
            history = monitor.get_history()
            return jsonify({
                'history': history,
                'timestamp': format_datetime_for_api(datetime.now())
            })
        else:
            return jsonify({
                'message': 'History tracking not implemented',
                'timestamp': format_datetime_for_api(datetime.now())
            })
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({
            'error': f'Failed to get history: {str(e)}',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 500

@app.route('/monitoring/metrics')
def get_monitoring_metrics():
    """Get monitoring performance metrics"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    try:
        metrics = {
            'total_checks': monitor.total_checks if hasattr(monitor, 'total_checks') else 0,
            'successful_checks': monitor.successful_checks if hasattr(monitor, 'successful_checks') else 0,
            'failed_checks': monitor.failed_checks if hasattr(monitor, 'failed_checks') else 0,
            'average_check_time': monitor.average_check_time if hasattr(monitor, 'average_check_time') else 0,
            'last_check_duration': monitor.last_check_duration if hasattr(monitor, 'last_check_duration') else 0,
            'uptime_percentage': monitor.uptime_percentage if hasattr(monitor, 'uptime_percentage') else 0,
            'timestamp': format_datetime_for_api(datetime.now())
        }
        
        # Add host-specific metrics if available
        host_metrics = []
        for host in monitor.hosts:
            host_info = {
                'name': host['name'],
                'total_checks': host.get('total_checks', 0),
                'uptime_percentage': host.get('uptime_percentage', 0),
                'downtime_count': host.get('downtime_count', 0),
                'last_downtime_duration': host.get('last_downtime_duration', 0)
            }
            host_metrics.append(host_info)
        
        if host_metrics:
            metrics['hosts'] = host_metrics
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({
            'error': f'Failed to get metrics: {str(e)}',
            'timestamp': format_datetime_for_api(datetime.now())
        }), 500

@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to avoid 404 errors"""
    return '', 204

def start_monitoring():
    """Start the monitoring thread"""
    if monitoring_thread:
        monitoring_thread.start()
        logger.info("Monitoring thread started")
    else:
        logger.warning("Monitoring thread not started")

if __name__ == '__main__':
    # Note: monitoring_thread is already started above
    app.run(host='0.0.0.0', port=8080, debug=False)