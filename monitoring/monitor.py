import socket
import requests
import time
import yaml
import os
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger('monitoring')

class HostMonitor:
    def __init__(self, config_path: str = None):
        """
        Initialize the HostMonitor with configuration path.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path or 'config/hosts.yaml'
        self.hosts: List[Dict[str, Any]] = []
        self.host_status: Dict[str, Dict[str, Any]] = {}
        self.alert_messages: Dict[str, Dict[str, str]] = {}
        self.load_config()
    
    def load_config(self):
        """Load hosts configuration from YAML file"""
        try:
            logger.info(f"Attempting to load configuration from: {self.config_path}")
            
            # Try multiple possible locations for the config file
            possible_paths = [
                Path(self.config_path),  # Direct path
                Path(__file__).parent.parent / self.config_path,  # Relative to project root
                Path('/app') / self.config_path,  # Docker container path
                Path.cwd() / self.config_path,  # Current working directory
                Path.cwd() / 'config' / 'hosts.yaml',  # Common config location
                Path('/app/config/hosts.yaml'),  # Docker config location
            ]
            
            config_file = None
            for path in possible_paths:
                logger.debug(f"Checking path: {path}")
                if path.exists():
                    if path.is_file():
                        config_file = path
                        logger.info(f"Found config file at: {config_file}")
                        break
                    elif path.is_dir():
                        # If it's a directory, look for hosts.yaml inside it
                        potential_file = path / 'hosts.yaml'
                        if potential_file.exists() and potential_file.is_file():
                            config_file = potential_file
                            logger.info(f"Found config file at: {config_file}")
                            break
            
            if config_file is None:
                logger.error(f"Config file not found in any known location")
                logger.info("Using default configuration")
                self.load_default_config()
                return
            
            # Read and parse the config file
            with open(config_file, 'r') as file:
                config_content = file.read()
                
            if not config_content.strip():
                logger.error("Config file is empty")
                self.load_default_config()
                return
                
            config = yaml.safe_load(config_content)
            
            if not config:
                logger.error("Failed to parse YAML configuration")
                self.load_default_config()
                return
            
            # Validate required sections
            if 'hosts' not in config:
                logger.error("'hosts' section missing from config file")
                self.load_default_config()
                return
                
            self.hosts = config.get('hosts', [])
            
            # Validate each host configuration
            valid_hosts = []
            for i, host in enumerate(self.hosts):
                if not self.validate_host_config(host, i):
                    continue
                valid_hosts.append(host)
            
            self.hosts = valid_hosts
            
            # Load alert messages or use defaults
            self.alert_messages = config.get('alert_messages', {})
            if not self.alert_messages:
                self.alert_messages = self.get_default_alert_messages()
                logger.info("Using default alert messages")
            
            # Initialize status tracking for all valid hosts
            for host in self.hosts:
                key = self.get_host_key(host)
                self.host_status[key] = {
                    'current_status': 'unknown',
                    'last_status_change': None,
                    'downtime_start': None,
                    'last_check': None,
                    'check_count': 0
                }
                
            logger.info(f"Successfully loaded {len(self.hosts)} hosts from configuration")
            
            # Log loaded hosts for debugging
            for host in self.hosts:
                logger.debug(f"Configured host: {host['name']} ({host['ip_address']}:{host['port']})")
                
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {str(e)}")
            self.load_default_config()
        except FileNotFoundError as e:
            logger.error(f"Config file not found: {str(e)}")
            self.load_default_config()
        except PermissionError as e:
            logger.error(f"Permission denied accessing config file: {str(e)}")
            self.load_default_config()
        except Exception as e:
            logger.error(f"Unexpected error loading config: {str(e)}")
            self.load_default_config()
    
    def validate_host_config(self, host: Dict[str, Any], index: int) -> bool:
        """
        Validate a host configuration entry.
        
        Args:
            host: Host configuration dictionary
            index: Index of host in list for error reporting
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ['name', 'hostname', 'ip_address', 'port', 'check_type']
        
        # Check for required fields
        for field in required_fields:
            if field not in host:
                logger.error(f"Host at index {index} missing required field: '{field}'")
                return False
        
        # Validate check_type
        if host['check_type'] not in ['tcp', 'http', 'https']:
            logger.error(f"Host '{host['name']}' has invalid check_type: '{host['check_type']}'. Must be 'tcp', 'http', or 'https'")
            return False
        
        # Validate port
        try:
            port = int(host['port'])
            if not (1 <= port <= 65535):
                logger.error(f"Host '{host['name']}' has invalid port: {port}. Must be between 1-65535")
                return False
        except ValueError:
            logger.error(f"Host '{host['name']}' has invalid port: {host['port']}. Must be a number")
            return False
        
        # Validate IP address format (basic check)
        ip_parts = host['ip_address'].split('.')
        if len(ip_parts) != 4:
            logger.warning(f"Host '{host['name']}' has non-standard IP address: {host['ip_address']}")
            # Not returning False as it could be a hostname
        
        logger.debug(f"Host '{host['name']}' configuration validated successfully")
        return True
    
    def get_host_key(self, host: Dict[str, Any]) -> str:
        """Generate a unique key for a host"""
        return f"{host['hostname']}_{host['ip_address']}_{host['port']}"
    
    def get_default_alert_messages(self) -> Dict[str, Dict[str, str]]:
        """Get default alert messages"""
        return {
            'user': {
                'downtime': "We are aware of the downtime and we are working on it. It will be fixed within the next 15 minutes.",
                'resolved': "The downtime has been resolved. Thank you for your patience."
            },
            'admin': {
                'downtime': "Server {hostname} ({ip_address}) is down at {timestamp}",
                'resolved': "Host {hostname} ({ip_address}) is back online at {timestamp}"
            }
        }
    
    def load_default_config(self):
        """Load default configuration when config file is not found or invalid"""
        logger.info("Loading default configuration")
        
        self.hosts = [
            {
                'name': 'Google DNS',
                'hostname': 'dns.google',
                'ip_address': '8.8.8.8',
                'port': 53,
                'check_type': 'tcp'
            },
            {
                'name': 'Google HTTP',
                'hostname': 'google.com',
                'ip_address': '142.250.185.78',
                'port': 80,
                'check_type': 'http'
            },
            {
                'name': 'Localhost Test',
                'hostname': 'localhost',
                'ip_address': '127.0.0.1',
                'port': 8080,
                'check_type': 'http'
            }
        ]
        
        self.alert_messages = self.get_default_alert_messages()
        
        # Initialize status tracking for default hosts
        for host in self.hosts:
            key = self.get_host_key(host)
            self.host_status[key] = {
                'current_status': 'unknown',
                'last_status_change': None,
                'downtime_start': None,
                'last_check': None,
                'check_count': 0
            }
        
        logger.info(f"Loaded {len(self.hosts)} default hosts")
    
    def check_host(self, host: Dict[str, Any]) -> bool:
        """
        Check if a host is reachable.
        
        Args:
            host: Host configuration dictionary
            
        Returns:
            bool: True if host is reachable, False otherwise
        """
        host_key = self.get_host_key(host)
        current_time = datetime.now()
        
        try:
            is_up = False
            check_type = host['check_type']
            
            if check_type == 'tcp':
                is_up = self.check_tcp_port(host['ip_address'], host['port'])
            elif check_type in ['http', 'https']:
                is_up = self.check_http_service(host['ip_address'], host['port'], check_type == 'https')
            else:
                logger.error(f"Unknown check type for host {host['name']}: {check_type}")
                is_up = False
            
            # Update host status tracking
            self.host_status[host_key]['last_check'] = current_time
            self.host_status[host_key]['check_count'] = self.host_status[host_key].get('check_count', 0) + 1
            
            if is_up:
                logger.debug(f"Host {host['name']} ({host['ip_address']}:{host['port']}) is UP")
            else:
                logger.debug(f"Host {host['name']} ({host['ip_address']}:{host['port']}) is DOWN")
            
            return is_up
            
        except Exception as e:
            logger.error(f"Error checking host {host['name']} ({host['ip_address']}): {str(e)}")
            self.host_status[host_key]['last_check'] = current_time
            return False
    
    def check_tcp_port(self, ip: str, port: int, timeout: int = 10) -> bool:
        """
        Check if a TCP port is open.
        
        Args:
            ip: IP address or hostname
            port: Port number
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if port is open, False otherwise
        """
        try:
            logger.debug(f"Checking TCP port {ip}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                logger.debug(f"TCP check successful for {ip}:{port}")
                return True
            else:
                logger.debug(f"TCP check failed for {ip}:{port}, error code: {result}")
                return False
                
        except socket.timeout:
            logger.warning(f"TCP connection timeout for {ip}:{port}")
            return False
        except socket.gaierror as e:
            logger.error(f"Hostname resolution error for {ip}:{port}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"TCP socket error for {ip}:{port}: {str(e)}")
            return False
    
    def check_http_service(self, ip: str, port: int, use_https: bool = False, timeout: int = 10) -> bool:
        """
        Check if HTTP/HTTPS service is responding.
        
        Args:
            ip: IP address or hostname
            port: Port number
            use_https: Use HTTPS instead of HTTP
            timeout: Request timeout in seconds
            
        Returns:
            bool: True if service is responding, False otherwise
        """
        try:
            scheme = 'https' if use_https else 'http'
            url = f"{scheme}://{ip}:{port}"
            
            logger.debug(f"Checking HTTP service at {url}")
            
            # Add a simple path to avoid 404 on root if needed
            if port == 80 and not use_https:
                url = f"http://{ip}"
            elif port == 443 and use_https:
                url = f"https://{ip}"
            
            headers = {
                'User-Agent': 'Server-Monitoring-System/1.0'
            }
            
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                verify=False,  # Disable SSL verification for self-signed certs
                allow_redirects=True
            )
            
            # Consider any response < 500 as "up"
            is_up = response.status_code < 500
            
            if is_up:
                logger.debug(f"HTTP check successful for {url}, status: {response.status_code}")
            else:
                logger.warning(f"HTTP check failed for {url}, status: {response.status_code}")
            
            return is_up
            
        except requests.exceptions.Timeout:
            logger.warning(f"HTTP request timeout for {ip}:{port}")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning(f"HTTP connection error for {ip}:{port}")
            return False
        except requests.exceptions.SSLError:
            logger.warning(f"SSL error for {ip}:{port}, trying without verification")
            # Try again without SSL verification
            try:
                response = requests.get(
                    f"{scheme}://{ip}:{port}",
                    timeout=timeout,
                    verify=False,
                    allow_redirects=True
                )
                return response.status_code < 500
            except:
                return False
        except Exception as e:
            logger.error(f"HTTP check error for {ip}:{port}: {str(e)}")
            return False
    
    def monitor_all_hosts(self) -> List[Dict[str, Any]]:
        """
        Monitor all configured hosts and detect status changes.
        
        Returns:
            List of dictionaries containing status change information
        """
        status_changes = []
        current_time = datetime.now()
        
        if not self.hosts:
            logger.warning("No hosts configured to monitor")
            return status_changes
        
        logger.info(f"Starting monitoring cycle for {len(self.hosts)} hosts")
        
        for host in self.hosts:
            try:
                host_key = self.get_host_key(host)
                previous_status = self.host_status[host_key]['current_status']
                
                # Check host status
                is_up = self.check_host(host)
                new_status = 'up' if is_up else 'down'
                
                # Detect status change
                if previous_status != new_status:
                    self.host_status[host_key]['current_status'] = new_status
                    self.host_status[host_key]['last_status_change'] = current_time
                    
                    if new_status == 'down':
                        self.host_status[host_key]['downtime_start'] = current_time
                        logger.warning(f"STATUS CHANGE: {host['name']} ({host['ip_address']}) changed from {previous_status} to {new_status}")
                    else:
                        # If coming back up, calculate downtime duration
                        downtime_start = self.host_status[host_key]['downtime_start']
                        if downtime_start:
                            downtime_duration = (current_time - downtime_start).total_seconds()
                            logger.info(f"STATUS CHANGE: {host['name']} ({host['ip_address']}) changed from {previous_status} to {new_status} after {downtime_duration:.1f} seconds of downtime")
                        else:
                            logger.info(f"STATUS CHANGE: {host['name']} ({host['ip_address']}) changed from {previous_status} to {new_status}")
                        
                        self.host_status[host_key]['downtime_start'] = None
                    
                    # Record status change for notification
                    status_changes.append({
                        'host': host,
                        'previous_status': previous_status,
                        'new_status': new_status,
                        'timestamp': current_time,
                        'downtime_duration': self.get_downtime_duration(host_key) if new_status == 'up' else None
                    })
                else:
                    # Log periodic status for debugging (less verbose)
                    if self.host_status[host_key]['check_count'] % 10 == 0:  # Every 10th check
                        logger.debug(f"Status unchanged: {host['name']} ({host['ip_address']}) is {new_status}")
                        
            except Exception as e:
                logger.error(f"Error monitoring host {host.get('name', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"Monitoring cycle completed. Status changes detected: {len(status_changes)}")
        return status_changes
    
    def get_downtime_duration(self, host_key: str) -> Optional[float]:
        """
        Get downtime duration for a host.
        
        Args:
            host_key: Unique host identifier
            
        Returns:
            Downtime duration in seconds, or None if not currently down
        """
        if host_key not in self.host_status:
            return None
        
        downtime_start = self.host_status[host_key].get('downtime_start')
        if not downtime_start:
            return None
        
        return (datetime.now() - downtime_start).total_seconds()
    
    def get_host_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all hosts' status.
        
        Returns:
            Dictionary containing status summary
        """
        summary = {
            'total_hosts': len(self.hosts),
            'up_hosts': 0,
            'down_hosts': 0,
            'unknown_hosts': 0,
            'hosts': []
        }
        
        for host in self.hosts:
            host_key = self.get_host_key(host)
            status_info = self.host_status.get(host_key, {})
            current_status = status_info.get('current_status', 'unknown')
            
            # Count statuses
            if current_status == 'up':
                summary['up_hosts'] += 1
            elif current_status == 'down':
                summary['down_hosts'] += 1
            else:
                summary['unknown_hosts'] += 1
            
            # Add host details
            host_summary = {
                'name': host['name'],
                'hostname': host['hostname'],
                'ip_address': host['ip_address'],
                'port': host['port'],
                'check_type': host['check_type'],
                'current_status': current_status,
                'last_status_change': status_info.get('last_status_change'),
                'last_check': status_info.get('last_check'),
                'downtime_start': status_info.get('downtime_start'),
                'check_count': status_info.get('check_count', 0)
            }
            
            # Add downtime duration if currently down
            if current_status == 'down':
                downtime_duration = self.get_downtime_duration(host_key)
                if downtime_duration:
                    host_summary['downtime_duration_seconds'] = downtime_duration
            
            summary['hosts'].append(host_summary)
        
        return summary
    
    def get_host_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get host configuration by name.
        
        Args:
            name: Host name to find
            
        Returns:
            Host configuration dictionary or None if not found
        """
        for host in self.hosts:
            if host['name'] == name:
                return host
        return None
    
    def add_host(self, host_config: Dict[str, Any]) -> bool:
        """
        Add a new host to monitor.
        
        Args:
            host_config: Host configuration dictionary
            
        Returns:
            bool: True if host was added successfully, False otherwise
        """
        try:
            # Validate the new host configuration
            if not self.validate_host_config(host_config, len(self.hosts)):
                logger.error(f"Failed to validate new host configuration")
                return False
            
            # Check if host already exists
            for existing_host in self.hosts:
                if (existing_host['ip_address'] == host_config['ip_address'] and 
                    existing_host['port'] == host_config['port']):
                    logger.warning(f"Host with IP {host_config['ip_address']} and port {host_config['port']} already exists")
                    return False
            
            # Add host to list
            self.hosts.append(host_config)
            
            # Initialize status tracking
            host_key = self.get_host_key(host_config)
            self.host_status[host_key] = {
                'current_status': 'unknown',
                'last_status_change': None,
                'downtime_start': None,
                'last_check': None,
                'check_count': 0
            }
            
            logger.info(f"Added new host: {host_config['name']} ({host_config['ip_address']}:{host_config['port']})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding new host: {str(e)}")
            return False
    
    def remove_host(self, name: str) -> bool:
        """
        Remove a host from monitoring.
        
        Args:
            name: Name of the host to remove
            
        Returns:
            bool: True if host was removed successfully, False otherwise
        """
        for i, host in enumerate(self.hosts):
            if host['name'] == name:
                # Remove from hosts list
                removed_host = self.hosts.pop(i)
                
                # Remove from status tracking
                host_key = self.get_host_key(removed_host)
                if host_key in self.host_status:
                    del self.host_status[host_key]
                
                logger.info(f"Removed host: {name}")
                return True
        
        logger.warning(f"Host not found: {name}")
        return False