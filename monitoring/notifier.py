import os
import pytz
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from twilio.rest import Client
import requests
import json
import logging
from config import settings

logger = logging.getLogger('monitoring')


class WhatsAppBatchSender:
    """Handles batch sending of WhatsApp messages with rate limiting"""
    
    def __init__(self, twilio_client: Client, from_number: str):
        self.twilio_client = twilio_client
        self.from_number = from_number
        self.daily_message_count = 0
        self.last_reset_time = datetime.now()
        self.rate_limit_hit = False
        self.last_send_time = datetime.now() - timedelta(seconds=2)  # Start ready
        
        # Rate limiting configuration
        self.MIN_DELAY_BETWEEN_MESSAGES = 0.5  # seconds
        self.MAX_MESSAGES_PER_MINUTE = 30
        self.MAX_MESSAGES_PER_DAY = 50  # Twilio free tier
        self.messages_this_minute = 0
        self.minute_start_time = datetime.now()
    
    def _check_rate_limits(self) -> bool:
        """Check if we can send more messages"""
        now = datetime.now()
        
        # Reset daily counter if new day
        if now.date() > self.last_reset_time.date():
            self.daily_message_count = 0
            self.rate_limit_hit = False
            self.last_reset_time = now
            logger.info("📅 Daily message counter reset")
        
        # Check daily limit
        if self.daily_message_count >= self.MAX_MESSAGES_PER_DAY:
            if not self.rate_limit_hit:
                logger.critical(f"🚨 DAILY LIMIT REACHED: {self.daily_message_count}/{self.MAX_MESSAGES_PER_DAY}")
                self.rate_limit_hit = True
            return False
        
        # Check minute limit (reset counter every minute)
        if (now - self.minute_start_time).seconds >= 60:
            self.messages_this_minute = 0
            self.minute_start_time = now
        
        if self.messages_this_minute >= self.MAX_MESSAGES_PER_MINUTE:
            logger.warning(f"⏱️  Minute limit reached: {self.messages_this_minute}/{self.MAX_MESSAGES_PER_MINUTE}")
            # Wait for next minute
            time_to_wait = 60 - (now - self.minute_start_time).seconds
            if time_to_wait > 0:
                logger.info(f"⏳ Waiting {time_to_wait} seconds for minute reset...")
                time.sleep(time_to_wait)
                self.messages_this_minute = 0
                self.minute_start_time = datetime.now()
        
        # Enforce minimum delay between messages
        time_since_last = (now - self.last_send_time).total_seconds()
        if time_since_last < self.MIN_DELAY_BETWEEN_MESSAGES:
            time.sleep(self.MIN_DELAY_BETWEEN_MESSAGES - time_since_last)
        
        return True
    
    def send_single_message(self, to_number: str, message: str) -> Dict:
        """Send a single WhatsApp message with rate limiting"""
        if not self._check_rate_limits():
            return {
                'success': False,
                'error': 'Rate limited',
                'number': to_number
            }
        
        try:
            message_obj = self.twilio_client.messages.create(
                from_=f"whatsapp:{self.from_number}",
                body=message,
                to=to_number
            )
            
            # Update counters
            self.daily_message_count += 1
            self.messages_this_minute += 1
            self.last_send_time = datetime.now()
            
            return {
                'success': True,
                'message_id': message_obj.sid,
                'number': to_number,
                'daily_count': self.daily_message_count
            }
            
        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "exceeded" in error_msg.lower():
                self.rate_limit_hit = True
                error_type = "RATE_LIMIT"
            elif "21608" in error_msg:  # Twilio: Number not authorized
                error_type = "UNAUTHORIZED_NUMBER"
            else:
                error_type = "SEND_ERROR"
            
            return {
                'success': False,
                'error': error_msg,
                'error_type': error_type,
                'number': to_number
            }
    
    def get_stats(self) -> Dict:
        """Get current sending statistics"""
        now = datetime.now()
        return {
            'daily_messages': self.daily_message_count,
            'daily_limit': self.MAX_MESSAGES_PER_DAY,
            'messages_this_minute': self.messages_this_minute,
            'minute_limit': self.MAX_MESSAGES_PER_MINUTE,
            'rate_limit_hit': self.rate_limit_hit,
            'minutes_until_reset': 60 - (now - self.minute_start_time).seconds if (now - self.minute_start_time).seconds < 60 else 0,
            'last_send_time': self.last_send_time.isoformat()
        }


class Notifier:
    """Advanced notifier for handling many WhatsApp numbers"""
    
    def __init__(self):
        self.twilio_client = None
        self.batch_sender = None
        
        # Timezone configuration
        timezone_str = os.getenv('TIMEZONE', 'UTC')
        try:
            self.timezone = pytz.timezone(timezone_str)
            logger.info(f"Using timezone: {timezone_str}")
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone_str}, defaulting to UTC")
            self.timezone = pytz.UTC
        
        # Load number priorities
        self.critical_numbers = self._load_critical_numbers()
        self.setup_twilio()
        
        # Message queue for handling many recipients
        self.message_queue = []
        self.queue_processor_running = False
        self.start_queue_processor()
    
    def _load_critical_numbers(self) -> List[str]:
        """Load critical numbers from environment or use first N as critical"""
        # Get from environment or use first 3 as critical
        critical_env = os.getenv('CRITICAL_WHATSAPP_NUMBERS', '')
        if critical_env:
            critical_numbers = [n.strip() for n in critical_env.split(',') if n.strip()]
        else:
            # Default: First 3 numbers from user and admin lists are critical
            user_numbers = settings.WHATSAPP_CONFIG.get('user_numbers', [])
            admin_numbers = settings.WHATSAPP_CONFIG.get('admin_numbers', [])
            all_numbers = user_numbers + admin_numbers
            critical_numbers = [n.strip() for n in all_numbers[:3] if n and n.strip()]
        
        logger.info(f"Loaded {len(critical_numbers)} critical WhatsApp numbers")
        return critical_numbers
    
    def format_timestamp(self, dt: datetime) -> str:
        """Format timestamp in local timezone"""
        try:
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            
            local_dt = dt.astimezone(self.timezone)
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            logger.error(f"Error formatting timestamp: {str(e)}")
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    def setup_twilio(self):
        """Initialize Twilio client for WhatsApp"""
        if settings.WHATSAPP_CONFIG['account_sid'] and settings.WHATSAPP_CONFIG['auth_token']:
            try:
                self.twilio_client = Client(
                    settings.WHATSAPP_CONFIG['account_sid'],
                    settings.WHATSAPP_CONFIG['auth_token']
                )
                self.batch_sender = WhatsAppBatchSender(
                    self.twilio_client,
                    settings.WHATSAPP_CONFIG['from_number']
                )
                logger.info("✅ Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
        else:
            logger.warning("Twilio credentials not configured")
    
    def _prepare_whatsapp_numbers(self, numbers_list: List[str]) -> List[str]:
        """Clean and format WhatsApp numbers"""
        prepared = []
        for number in numbers_list:
            if not number or not number.strip():
                continue
            
            cleaned = number.strip()
            if not cleaned.startswith('whatsapp:'):
                cleaned = f'whatsapp:{cleaned}'
            prepared.append(cleaned)
        
        return prepared
    
    def send_whatsapp_message(self, to_numbers: List[str], message: str, 
                            alert_type: str = "notification", 
                            priority: str = "normal") -> Dict:
        """
        Send WhatsApp message to many recipients with intelligent handling
        
        Args:
            to_numbers: List of phone numbers
            message: Message content
            alert_type: Type of alert for logging
            priority: "high", "normal", or "low"
        
        Returns:
            Dict with sending results
        """
        if not self.batch_sender:
            logger.warning("Twilio client not configured. WhatsApp messages disabled.")
            return {'success': False, 'error': 'Twilio not configured', 'sent_to': []}
        
        # Prepare numbers
        prepared_numbers = self._prepare_whatsapp_numbers(to_numbers)
        
        if not prepared_numbers:
            logger.warning(f"No valid numbers to send {alert_type} to")
            return {'success': False, 'error': 'No valid numbers', 'sent_to': []}
        
        # Separate numbers by priority
        critical_numbers = []
        normal_numbers = []
        
        for number in prepared_numbers:
            # Extract just the phone number part for comparison
            phone_part = number.replace('whatsapp:', '')
            if phone_part in self.critical_numbers:
                critical_numbers.append(number)
            else:
                normal_numbers.append(number)
        
        logger.info(f"📱 Sending {alert_type}: {len(critical_numbers)} critical, "
                   f"{len(normal_numbers)} normal recipients")
        
        results = {
            'successful': [],
            'failed': [],
            'rate_limited': [],
            'critical_sent': 0,
            'normal_sent': 0,
            'daily_count': self.batch_sender.daily_message_count
        }
        
        # Function to send to a group of numbers
        def send_number_group(numbers: List[str], group_name: str, is_critical: bool):
            for number in numbers:
                result = self.batch_sender.send_single_message(number, message)
                
                if result['success']:
                    logger.info(f"✅ {'CRITICAL ' if is_critical else ''}{alert_type} sent to {number}")
                    results['successful'].append(number)
                    if is_critical:
                        results['critical_sent'] += 1
                    else:
                        results['normal_sent'] += 1
                else:
                    error_type = result.get('error_type', 'UNKNOWN')
                    
                    if error_type == 'RATE_LIMIT':
                        logger.error(f"⚠️ Rate limit hit while sending to {number}")
                        results['rate_limited'].append(number)
                        
                        # If rate limited and this is critical, queue for retry
                        if is_critical:
                            self._queue_for_retry(number, message, alert_type)
                    else:
                        logger.error(f"❌ Failed to send to {number}: {result.get('error', 'Unknown error')}")
                        results['failed'].append({
                            'number': number,
                            'error': result.get('error', 'Unknown'),
                            'type': error_type
                        })
        
        # Send critical numbers FIRST (always try these)
        if critical_numbers:
            logger.info(f"🔄 Sending to {len(critical_numbers)} critical numbers...")
            send_number_group(critical_numbers, "critical", is_critical=True)
        
        # Check if we can send to normal numbers
        stats = self.batch_sender.get_stats()
        
        if normal_numbers and not stats['rate_limit_hit']:
            # Estimate if we have capacity for normal numbers
            daily_remaining = stats['daily_limit'] - stats['daily_messages']
            minute_remaining = stats['minute_limit'] - stats['messages_this_minute']
            
            capacity = min(daily_remaining, minute_remaining)
            
            if capacity >= len(normal_numbers):
                logger.info(f"🔄 Sending to {len(normal_numbers)} normal numbers...")
                send_number_group(normal_numbers, "normal", is_critical=False)
            elif capacity > 0:
                # Send to as many as we have capacity for
                logger.info(f"🔄 Partial send: {capacity}/{len(normal_numbers)} normal numbers (limited by capacity)")
                send_number_group(normal_numbers[:capacity], "normal_partial", is_critical=False)
                
                # Queue the rest
                remaining = normal_numbers[capacity:]
                for number in remaining:
                    self._queue_for_retry(number, message, alert_type)
                logger.info(f"📨 Queued {len(remaining)} numbers for later delivery")
            else:
                logger.warning(f"⏸️  No capacity for normal numbers, queueing all {len(normal_numbers)}")
                for number in normal_numbers:
                    self._queue_for_retry(number, message, alert_type)
        elif normal_numbers:
            logger.warning(f"⏸️  Rate limit hit, queueing {len(normal_numbers)} normal numbers")
            for number in normal_numbers:
                self._queue_for_retry(number, message, alert_type)
        
        # Log summary
        total_attempted = len(prepared_numbers)
        successful_count = len(results['successful'])
        
        if successful_count == total_attempted:
            logger.info(f"🎉 {alert_type}: All {successful_count} messages sent successfully")
        elif successful_count > 0:
            logger.info(f"📊 {alert_type}: {successful_count}/{total_attempted} messages sent "
                       f"({results['critical_sent']} critical, {results['normal_sent']} normal)")
            
            if results['rate_limited']:
                logger.warning(f"⚠️  {len(results['rate_limited'])} numbers rate limited")
            if results['failed']:
                logger.error(f"❌ {len(results['failed'])} numbers failed")
        else:
            logger.error(f"🚨 {alert_type}: All {total_attempted} messages failed")
        
        return {
            'success': successful_count > 0,
            'results': results,
            'stats': stats,
            'queued_count': len(self.message_queue)
        }
    
    def _queue_for_retry(self, number: str, message: str, alert_type: str):
        """Queue a message for retry later"""
        queue_item = {
            'number': number,
            'message': message,
            'alert_type': alert_type,
            'added_at': datetime.now(),
            'retry_count': 0,
            'next_retry': datetime.now() + timedelta(minutes=5)
        }
        
        self.message_queue.append(queue_item)
        logger.debug(f"📨 Queued message for {number} (retry in 5 minutes)")
    
    def start_queue_processor(self):
        """Start background thread to process queued messages"""
        def process_queue():
            self.queue_processor_running = True
            logger.info("🔄 Starting message queue processor")
            
            while self.queue_processor_running:
                try:
                    now = datetime.now()
                    items_to_retry = []
                    
                    # Find items ready for retry
                    for item in self.message_queue[:]:  # Copy for iteration
                        if now >= item['next_retry']:
                            items_to_retry.append(item)
                    
                    # Process retries
                    for item in items_to_retry:
                        result = self.batch_sender.send_single_message(
                            item['number'], 
                            item['message']
                        )
                        
                        if result['success']:
                            logger.info(f"✅ Retry successful for {item['number']}")
                            self.message_queue.remove(item)
                        else:
                            item['retry_count'] += 1
                            
                            if item['retry_count'] >= 3:  # Max 3 retries
                                logger.error(f"❌ Max retries reached for {item['number']}, removing from queue")
                                self.message_queue.remove(item)
                            else:
                                # Exponential backoff: 5, 15, 45 minutes
                                backoff_minutes = 5 * (3 ** item['retry_count'])
                                item['next_retry'] = now + timedelta(minutes=backoff_minutes)
                                logger.info(f"🔄 Scheduled retry {item['retry_count']} for {item['number']} "
                                          f"in {backoff_minutes} minutes")
                    
                    # Clean old items (older than 24 hours)
                    cutoff_time = now - timedelta(hours=24)
                    initial_count = len(self.message_queue)
                    self.message_queue = [
                        item for item in self.message_queue 
                        if item['added_at'] > cutoff_time
                    ]
                    
                    if len(self.message_queue) < initial_count:
                        logger.debug(f"🧹 Cleaned {initial_count - len(self.message_queue)} old queue items")
                    
                    # Sleep before next check
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in queue processor: {str(e)}")
                    time.sleep(60)  # Wait longer on error
        
        # Start the processor thread
        if not self.queue_processor_running:
            processor_thread = threading.Thread(target=process_queue, daemon=True)
            processor_thread.start()
    
    def send_teams_message(self, webhook_url: str, message: str, 
                          title: str = "Server Monitoring Alert") -> Dict:
        """Send message to Microsoft Teams channel"""
        if not webhook_url:
            logger.debug("Teams webhook URL not configured")
            return {'success': False, 'error': 'Webhook not configured'}
        
        try:
            teams_message = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": title,
                "sections": [{
                    "activityTitle": title,
                    "activitySubtitle": self.format_timestamp(datetime.now()),
                    "text": message,
                    "markdown": True
                }]
            }
            
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                json=teams_message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Teams message sent: {title}")
                return {'success': True, 'status_code': response.status_code}
            else:
                logger.error(f"❌ Teams message failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'details': response.text[:100]
                }
                
        except Exception as e:
            logger.error(f"❌ Error sending Teams message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_downtime_alerts(self, host: dict, timestamp: datetime):
        """Send downtime alerts to users and admins - EXACT FORMAT AS REQUIRED"""
        # Format timestamp in local timezone
        local_timestamp = self.format_timestamp(timestamp)
        
        # EXACT MESSAGES AS REQUIRED:
        # User message: "We are aware of the downtime and we are working on it as it will be fixed within the next 15mins"
        user_message = "We are aware of the downtime and we are working on it as it will be fixed within the next 15mins"
        
        # Admin message: "Server (hostname/ip-address) is down with time stamp"
        admin_message = f"Server {host['hostname']}/{host['ip_address']} is down at {local_timestamp}"
        
        # Send WhatsApp to users
        user_whatsapp_result = self.send_whatsapp_message(
            settings.WHATSAPP_CONFIG['user_numbers'],
            user_message,
            alert_type="downtime_user",
            priority="high"
        )
        
        # Send WhatsApp to admins
        admin_whatsapp_result = self.send_whatsapp_message(
            settings.WHATSAPP_CONFIG['admin_numbers'],
            admin_message,
            alert_type="downtime_admin",
            priority="high"
        )
        
        # Send Teams messages with the same exact messages
        user_teams_result = self.send_teams_message(
            settings.TEAMS_CONFIG['user_webhook'], 
            user_message, 
            "Service Downtime Notification"
        )
        
        admin_teams_result = self.send_teams_message(
            settings.TEAMS_CONFIG['admin_webhook'], 
            admin_message, 
            f"Server Down: {host['name']}"
        )
        
        return {
            'user_whatsapp': user_whatsapp_result,
            'admin_whatsapp': admin_whatsapp_result,
            'user_teams': user_teams_result,
            'admin_teams': admin_teams_result,
            'timestamp': local_timestamp,
            'host': host['name']
        }
    
    def send_resolved_alerts(self, host: dict, timestamp: datetime):
        """Send resolution alerts to users and admins - EXACT FORMAT AS REQUIRED"""
        # Format timestamp in local timezone
        local_timestamp = self.format_timestamp(timestamp)
        
        # EXACT MESSAGES AS REQUIRED:
        # User message: "The downtime has been resolved. Thank you for your patience"
        user_message = "The downtime has been resolved. Thank you for your patience"
        
        # Admin message: "Host (state the hostname/ip address) is back online"
        admin_message = f"Host {host['hostname']}/{host['ip_address']} is back online at {local_timestamp}"
        
        # Send WhatsApp to users
        user_whatsapp_result = self.send_whatsapp_message(
            settings.WHATSAPP_CONFIG['user_numbers'],
            user_message,
            alert_type="resolved_user",
            priority="normal"
        )
        
        # Send WhatsApp to admins
        admin_whatsapp_result = self.send_whatsapp_message(
            settings.WHATSAPP_CONFIG['admin_numbers'],
            admin_message,
            alert_type="resolved_admin",
            priority="normal"
        )
        
        # Send Teams messages with the same exact messages
        user_teams_result = self.send_teams_message(
            settings.TEAMS_CONFIG['user_webhook'], 
            user_message, 
            "Service Restored"
        )
        
        admin_teams_result = self.send_teams_message(
            settings.TEAMS_CONFIG['admin_webhook'], 
            admin_message, 
            f"Server Restored: {host['name']}"
        )
        
        return {
            'user_whatsapp': user_whatsapp_result,
            'admin_whatsapp': admin_whatsapp_result,
            'user_teams': user_teams_result,
            'admin_teams': admin_teams_result,
            'timestamp': local_timestamp,
            'host': host['name']
        }
    
    def get_notification_stats(self) -> Dict:
        """Get notification system statistics"""
        if self.batch_sender:
            sender_stats = self.batch_sender.get_stats()
        else:
            sender_stats = {}
        
        return {
            'whatsapp': {
                'configured': bool(self.twilio_client),
                'critical_numbers': len(self.critical_numbers),
                'queue_size': len(self.message_queue),
                **sender_stats
            },
            'teams': {
                'user_webhook_configured': bool(settings.TEAMS_CONFIG.get('user_webhook')),
                'admin_webhook_configured': bool(settings.TEAMS_CONFIG.get('admin_webhook'))
            },
            'timezone': str(self.timezone)
        }
    
    def test_many_numbers(self, test_numbers: List[str] = None) -> Dict:
        """Test the system with many numbers"""
        if not test_numbers:
            # Generate test numbers if none provided
            test_numbers = [
                f"+23481{str(i).zfill(8)}" for i in range(1000, 1020)  # 20 test numbers
            ]
        
        test_host = {
            'name': 'Test Server',
            'hostname': 'test.example.com',
            'ip_address': '127.0.0.1'
        }
        test_time = datetime.now()
        
        logger.info(f"🧪 Testing with {len(test_numbers)} numbers...")
        
        # Test message
        test_message = f"Test message at {self.format_timestamp(test_time)}"
        
        # Send test
        result = self.send_whatsapp_message(
            test_numbers,
            test_message,
            alert_type="mass_test",
            priority="low"
        )
        
        # Queue stats
        queue_info = [
            {
                'number': item['number'],
                'alert_type': item['alert_type'],
                'retry_count': item['retry_count'],
                'next_retry': item['next_retry'].isoformat() if 'next_retry' in item else 'N/A'
            }
            for item in self.message_queue[:10]  # First 10 items
        ]
        
        return {
            'test_numbers_count': len(test_numbers),
            'whatsapp_result': result,
            'queue_summary': {
                'total_queued': len(self.message_queue),
                'sample_items': queue_info
            },
            'timestamp': test_time.isoformat()
        }