import pytest
import tempfile
import yaml
from monitoring.monitor import HostMonitor
from datetime import datetime

def test_host_monitor_initialization():
    """Test that the host monitor initializes correctly"""
    monitor = HostMonitor()
    assert monitor is not None
    assert hasattr(monitor, 'hosts')
    assert hasattr(monitor, 'host_status')

def test_load_config():
    """Test loading configuration from YAML"""
    # Create a temporary config file
    config_data = {
        'hosts': [
            {
                'name': 'Test Host',
                'hostname': 'test.example.com',
                'ip_address': '127.0.0.1',
                'port': 80,
                'check_type': 'http'
            }
        ],
        'alert_messages': {
            'user': {
                'downtime': 'Test downtime',
                'resolved': 'Test resolved'
            },
            'admin': {
                'downtime': 'Test admin downtime',
                'resolved': 'Test admin resolved'
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_config = f.name
    
    try:
        monitor = HostMonitor(temp_config)
        assert len(monitor.hosts) == 1
        assert monitor.hosts[0]['name'] == 'Test Host'
    finally:
        import os
        os.unlink(temp_config)

def test_host_key_generation():
    """Test generating unique host keys"""
    monitor = HostMonitor()
    test_host = {
        'hostname': 'test.com',
        'ip_address': '192.168.1.1',
        'port': 443
    }
    
    key = monitor.get_host_key(test_host)
    expected_key = 'test.com_192.168.1.1_443'
    assert key == expected_key

def test_status_summary():
    """Test getting status summary"""
    monitor = HostMonitor()
    summary = monitor.get_host_status_summary()
    
    assert 'total_hosts' in summary
    assert 'up_hosts' in summary
    assert 'down_hosts' in summary
    assert 'unknown_hosts' in summary
    assert 'hosts' in summary

def test_validate_host_config():
    """Test host configuration validation"""
    monitor = HostMonitor()
    
    # Valid configuration
    valid_host = {
        'name': 'Test',
        'hostname': 'test.com',
        'ip_address': '127.0.0.1',
        'port': 80,
        'check_type': 'http'
    }
    
    assert monitor.validate_host_config(valid_host, 0) == True
    
    # Invalid configurations
    missing_name = valid_host.copy()
    del missing_name['name']
    assert monitor.validate_host_config(missing_name, 0) == False
    
    invalid_port = valid_host.copy()
    invalid_port['port'] = 'not-a-number'
    assert monitor.validate_host_config(invalid_port, 0) == False
    
    invalid_check_type = valid_host.copy()
    invalid_check_type['check_type'] = 'invalid'
    assert monitor.validate_host_config(invalid_check_type, 0) == False