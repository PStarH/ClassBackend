"""
安全监控和日志系统
包含入侵检测、异常行为分析、实时告警等功能
基于建议的最佳实践实现
"""
import time
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import models
from decouple import config

logger = logging.getLogger('security')

# 配置常量
MONITOR_ENABLED = config('SECURITY_MONITOR_ENABLED', default=True, cast=bool)
ALERT_THRESHOLD = config('SECURITY_ALERT_THRESHOLD', default=10, cast=int)
TIME_WINDOW = config('SECURITY_TIME_WINDOW', default=300, cast=int)  # 5分钟
MAX_FAILED_ATTEMPTS = config('MAX_FAILED_LOGIN_ATTEMPTS', default=5, cast=int)
BLACKLIST_DURATION = config('IP_BLACKLIST_DURATION', default=3600, cast=int)  # 1小时


@dataclass
class SecurityEvent:
    """安全事件数据类"""
    event_type: str
    severity: str  # low, medium, high, critical
    source_ip: str
    user_agent: str
    path: str
    method: str
    timestamp: datetime
    user_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    attack_signature: Optional[str] = None


class SecurityEventModel(models.Model):
    """安全事件模型 - 数据库存储"""
    event_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    source_ip = models.GenericIPAddressField()
    user_agent = models.TextField()
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    user_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict)
    attack_signature = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'core'
        db_table = 'security_events'
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['source_ip', 'created_at']),
            models.Index(fields=['severity', 'resolved']),
        ]


class ThreatIntelligence:
    """威胁情报系统"""
    
    def __init__(self):
        self.malicious_ips = set()
        self.suspicious_user_agents = set()
        self.attack_patterns = {}
        self.load_threat_data()
    
    def load_threat_data(self):
        """加载威胁数据"""
        # 从缓存加载已知恶意IP
        cached_ips = cache.get('malicious_ips', set())
        self.malicious_ips.update(cached_ips)
        
        # 加载可疑User-Agent
        self.suspicious_user_agents.update([
            'sqlmap', 'nikto', 'dirb', 'nmap', 'masscan',
            'sqlninja', 'havij', 'pangolin', 'bbscan'
        ])
        
        # 加载攻击模式
        self.attack_patterns = {
            'sql_injection': [
                r'union\s+select', r'drop\s+table', r'exec\s*\(',
                r'script\s+alert', r'javascript:'
            ],
            'xss': [
                r'<script', r'javascript:', r'onload=',
                r'onerror=', r'onclick='
            ],
            'lfi': [
                r'\.\./', r'etc/passwd', r'proc/self',
                r'windows/system32'
            ]
        }
    
    def is_malicious_ip(self, ip: str) -> bool:
        """检查IP是否为恶意IP"""
        return ip in self.malicious_ips
    
    def is_suspicious_user_agent(self, user_agent: str) -> bool:
        """检查User-Agent是否可疑"""
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in self.suspicious_user_agents)
    
    def add_malicious_ip(self, ip: str):
        """添加恶意IP到黑名单"""
        self.malicious_ips.add(ip)
        # 同步到缓存
        cache.set('malicious_ips', self.malicious_ips, 86400)  # 24小时
        logger.warning(f"Added malicious IP to blacklist: {ip}")
    
    def remove_malicious_ip(self, ip: str):
        """从黑名单移除IP"""
        self.malicious_ips.discard(ip)
        cache.set('malicious_ips', self.malicious_ips, 86400)
        logger.info(f"Removed IP from blacklist: {ip}")


class BehaviorAnalyzer:
    """行为分析器"""
    
    def __init__(self):
        self.request_patterns = defaultdict(lambda: deque(maxlen=1000))
        self.failed_logins = defaultdict(int)
        self.blocked_ips = defaultdict(int)
        self.anomaly_threshold = config('ANOMALY_THRESHOLD', default=50, cast=int)
    
    def analyze_request_pattern(self, event: SecurityEvent) -> Dict[str, Any]:
        """分析请求模式"""
        ip = event.source_ip
        current_time = time.time()
        
        # 记录请求时间
        self.request_patterns[ip].append(current_time)
        
        # 计算请求频率
        recent_requests = [
            req_time for req_time in self.request_patterns[ip]
            if current_time - req_time <= TIME_WINDOW
        ]
        
        request_rate = len(recent_requests) / (TIME_WINDOW / 60)  # 每分钟请求数
        
        # 检测异常
        anomalies = []
        
        # 高频请求检测
        if request_rate > self.anomaly_threshold:
            anomalies.append({
                'type': 'high_frequency_requests',
                'value': request_rate,
                'threshold': self.anomaly_threshold
            })
        
        # 爆破攻击检测
        if event.event_type == 'failed_login':
            self.failed_logins[ip] += 1
            if self.failed_logins[ip] > MAX_FAILED_ATTEMPTS:
                anomalies.append({
                    'type': 'brute_force_attack',
                    'value': self.failed_logins[ip],
                    'threshold': MAX_FAILED_ATTEMPTS
                })
        
        # 扫描行为检测
        unique_paths = set()
        for req_time in recent_requests:
            # 这里简化处理，实际应该记录每个请求的路径
            unique_paths.add(event.path)
        
        if len(unique_paths) > 20:  # 访问过多不同路径
            anomalies.append({
                'type': 'scanning_behavior',
                'value': len(unique_paths),
                'threshold': 20
            })
        
        return {
            'request_rate': request_rate,
            'failed_logins': self.failed_logins[ip],
            'unique_paths': len(unique_paths),
            'anomalies': anomalies
        }
    
    def should_block_ip(self, ip: str) -> bool:
        """判断是否应该阻止IP"""
        return (
            self.failed_logins[ip] > MAX_FAILED_ATTEMPTS or
            self.blocked_ips[ip] > 0
        )
    
    def block_ip(self, ip: str, duration: int = BLACKLIST_DURATION):
        """阻止IP访问"""
        self.blocked_ips[ip] = int(time.time()) + duration
        cache.set(f'blocked_ip:{ip}', True, duration)
        logger.warning(f"Blocked IP {ip} for {duration} seconds")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被阻止"""
        return cache.get(f'blocked_ip:{ip}', False)


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_channels = []
        self.alert_rules = self.load_alert_rules()
        self.alert_history = deque(maxlen=1000)
        
    def load_alert_rules(self) -> List[Dict[str, Any]]:
        """加载告警规则"""
        return [
            {
                'name': 'Critical Security Event',
                'condition': lambda event: event.severity == 'critical',
                'channels': ['email', 'slack'],
                'cooldown': 300  # 5分钟冷却
            },
            {
                'name': 'High Frequency Attacks',
                'condition': lambda event: event.event_type == 'injection_attack',
                'channels': ['email'],
                'cooldown': 600  # 10分钟冷却
            },
            {
                'name': 'Brute Force Attack',
                'condition': lambda event: event.event_type == 'brute_force',
                'channels': ['slack'],
                'cooldown': 900  # 15分钟冷却
            }
        ]
    
    def should_send_alert(self, rule: Dict[str, Any], event: SecurityEvent) -> bool:
        """判断是否应该发送告警"""
        # 检查规则条件
        if not rule['condition'](event):
            return False
        
        # 检查冷却时间
        cooldown_key = f"alert_cooldown:{rule['name']}:{event.source_ip}"
        if cache.get(cooldown_key):
            return False
        
        return True
    
    def send_alert(self, event: SecurityEvent, analysis: Dict[str, Any]):
        """发送告警"""
        for rule in self.alert_rules:
            if self.should_send_alert(rule, event):
                # 设置冷却时间
                cooldown_key = f"alert_cooldown:{rule['name']}:{event.source_ip}"
                cache.set(cooldown_key, True, rule['cooldown'])
                
                # 发送告警
                alert_data = self.create_alert_message(event, analysis, rule)
                
                for channel in rule['channels']:
                    self.send_to_channel(channel, alert_data)
                
                # 记录告警历史
                self.alert_history.append({
                    'rule': rule['name'],
                    'event': event,
                    'timestamp': timezone.now(),
                    'channels': rule['channels']
                })
    
    def create_alert_message(self, event: SecurityEvent, analysis: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """创建告警消息"""
        return {
            'title': f"🚨 Security Alert: {rule['name']}",
            'severity': event.severity.upper(),
            'timestamp': event.timestamp.isoformat(),
            'source_ip': event.source_ip,
            'event_type': event.event_type,
            'path': event.path,
            'method': event.method,
            'user_agent': event.user_agent,
            'analysis': analysis,
            'details': event.details or {}
        }
    
    def send_to_channel(self, channel: str, alert_data: Dict[str, Any]):
        """发送到指定渠道"""
        try:
            if channel == 'email':
                self.send_email_alert(alert_data)
            elif channel == 'slack':
                self.send_slack_alert(alert_data)
            elif channel == 'webhook':
                self.send_webhook_alert(alert_data)
            
            logger.info(f"Alert sent to {channel}: {alert_data['title']}")
            
        except Exception as e:
            logger.error(f"Failed to send alert to {channel}: {e}")
    
    def send_email_alert(self, alert_data: Dict[str, Any]):
        """发送邮件告警"""
        from django.core.mail import send_mail
        
        subject = alert_data['title']
        message = self.format_email_message(alert_data)
        
        recipient_list = getattr(settings, 'SECURITY_ALERT_EMAILS', [])
        if recipient_list:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL'),
                recipient_list=recipient_list,
                fail_silently=False
            )
    
    def send_slack_alert(self, alert_data: Dict[str, Any]):
        """发送Slack告警"""
        import requests
        
        webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        if not webhook_url:
            return
        
        payload = {
            'text': alert_data['title'],
            'attachments': [{
                'color': self.get_color_by_severity(alert_data['severity']),
                'fields': [
                    {'title': 'Severity', 'value': alert_data['severity'], 'short': True},
                    {'title': 'Source IP', 'value': alert_data['source_ip'], 'short': True},
                    {'title': 'Event Type', 'value': alert_data['event_type'], 'short': True},
                    {'title': 'Path', 'value': alert_data['path'], 'short': True},
                ],
                'timestamp': alert_data['timestamp']
            }]
        }
        
        requests.post(webhook_url, json=payload, timeout=10)
    
    def send_webhook_alert(self, alert_data: Dict[str, Any]):
        """发送Webhook告警"""
        import requests
        
        webhook_url = getattr(settings, 'SECURITY_WEBHOOK_URL', None)
        if not webhook_url:
            return
        
        requests.post(webhook_url, json=alert_data, timeout=10)
    
    def format_email_message(self, alert_data: Dict[str, Any]) -> str:
        """格式化邮件消息"""
        return f"""
Security Alert: {alert_data['title']}

Severity: {alert_data['severity']}
Timestamp: {alert_data['timestamp']}
Source IP: {alert_data['source_ip']}
Event Type: {alert_data['event_type']}
Path: {alert_data['path']}
Method: {alert_data['method']}
User Agent: {alert_data['user_agent']}

Analysis:
{json.dumps(alert_data['analysis'], indent=2)}

Details:
{json.dumps(alert_data['details'], indent=2)}

Please investigate immediately.
        """.strip()
    
    def get_color_by_severity(self, severity: str) -> str:
        """根据严重程度获取颜色"""
        colors = {
            'LOW': 'good',
            'MEDIUM': 'warning', 
            'HIGH': 'danger',
            'CRITICAL': '#ff0000'
        }
        return colors.get(severity, 'good')


class SecurityMonitor:
    """安全监控主类"""
    
    def __init__(self):
        self.enabled = MONITOR_ENABLED
        self.threat_intel = ThreatIntelligence()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.alert_manager = AlertManager()
        
        # 统计信息
        self.stats = {
            'total_events': 0,
            'blocked_attempts': 0,
            'alerts_sent': 0,
            'start_time': timezone.now()
        }
    
    def process_security_event(self, event: SecurityEvent) -> Dict[str, Any]:
        """处理安全事件"""
        if not self.enabled:
            return {}
        
        try:
            # 更新统计
            self.stats['total_events'] += 1
            
            # 威胁情报检查
            if self.threat_intel.is_malicious_ip(event.source_ip):
                event.severity = 'critical'
                event.details = event.details or {}
                event.details['threat_intel'] = 'Known malicious IP'
            
            if self.threat_intel.is_suspicious_user_agent(event.user_agent):
                event.severity = max(event.severity, 'high', key=lambda x: ['low', 'medium', 'high', 'critical'].index(x))
                event.details = event.details or {}
                event.details['threat_intel'] = 'Suspicious user agent'
            
            # 行为分析
            analysis = self.behavior_analyzer.analyze_request_pattern(event)
            
            # 检查是否需要阻止IP
            if self.behavior_analyzer.should_block_ip(event.source_ip):
                self.behavior_analyzer.block_ip(event.source_ip)
                self.stats['blocked_attempts'] += 1
                
                # 升级事件严重程度
                event.severity = 'high'
                event.details = event.details or {}
                event.details['action'] = 'IP blocked'
            
            # 记录事件到数据库
            if getattr(settings, 'SECURITY_LOG_TO_DB', False):
                self.save_event_to_db(event)
            
            # 发送告警
            if analysis.get('anomalies'):
                self.alert_manager.send_alert(event, analysis)
                self.stats['alerts_sent'] += 1
            
            # 记录到日志
            self.log_security_event(event, analysis)
            
            return {
                'event_processed': True,
                'severity': event.severity,
                'analysis': analysis,
                'blocked': self.behavior_analyzer.is_ip_blocked(event.source_ip)
            }
            
        except Exception as e:
            logger.error(f"Error processing security event: {e}")
            return {'event_processed': False, 'error': str(e)}
    
    def save_event_to_db(self, event: SecurityEvent):
        """保存事件到数据库"""
        try:
            SecurityEventModel.objects.create(
                event_type=event.event_type,
                severity=event.severity,
                source_ip=event.source_ip,
                user_agent=event.user_agent,
                path=event.path,
                method=event.method,
                user_id=event.user_id,
                details=event.details or {},
                attack_signature=event.attack_signature
            )
        except Exception as e:
            logger.error(f"Failed to save security event to database: {e}")
    
    def log_security_event(self, event: SecurityEvent, analysis: Dict[str, Any]):
        """记录安全事件到日志"""
        log_level = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }.get(event.severity, logging.INFO)
        
        logger.log(
            log_level,
            f"Security Event | Type: {event.event_type} | "
            f"Severity: {event.severity} | IP: {event.source_ip} | "
            f"Path: {event.path} | Analysis: {analysis}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        uptime = timezone.now() - self.stats['start_time']
        
        return {
            **self.stats,
            'uptime_seconds': uptime.total_seconds(),
            'events_per_hour': self.stats['total_events'] / max(uptime.total_seconds() / 3600, 1),
            'blocked_ips_count': len(self.behavior_analyzer.blocked_ips),
            'malicious_ips_count': len(self.threat_intel.malicious_ips),
            'alert_rules_count': len(self.alert_manager.alert_rules)
        }
    
    def is_request_allowed(self, ip: str, user_agent: str) -> bool:
        """检查请求是否被允许"""
        if not self.enabled:
            return True
        
        # 检查IP黑名单
        if self.behavior_analyzer.is_ip_blocked(ip):
            return False
        
        # 检查威胁情报
        if self.threat_intel.is_malicious_ip(ip):
            return False
        
        return True


# 全局监控实例
security_monitor = SecurityMonitor()


# 便捷函数
def create_security_event(event_type: str, request, severity: str = 'medium', **kwargs) -> SecurityEvent:
    """创建安全事件"""
    return SecurityEvent(
        event_type=event_type,
        severity=severity,
        source_ip=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
        path=request.path,
        method=request.method,
        timestamp=timezone.now(),
        user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
        **kwargs
    )


def get_client_ip(request) -> str:
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'Unknown')
    return ip


def log_security_event(event_type: str, request, severity: str = 'medium', **kwargs):
    """记录安全事件的便捷函数"""
    event = create_security_event(event_type, request, severity, **kwargs)
    return security_monitor.process_security_event(event)


# 导出主要组件
__all__ = [
    'SecurityMonitor',
    'SecurityEvent',
    'SecurityEventModel', 
    'ThreatIntelligence',
    'BehaviorAnalyzer',
    'AlertManager',
    'security_monitor',
    'create_security_event',
    'log_security_event',
]