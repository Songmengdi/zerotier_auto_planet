"""IP监控器测试"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from downloader import Downloader
from ip_monitor import IPMonitor


class TestIPMonitor:
    """IP监控器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.config = Config()
        self.downloader = Mock(spec=Downloader)
        self.ip_monitor = IPMonitor(self.config, self.downloader)
    
    def test_parse_ips_valid(self):
        """测试解析有效IP地址"""
        ip_content = "192.168.1.1,\n10.0.0.1\n172.16.0.1,"
        expected_ips = {"192.168.1.1", "10.0.0.1", "172.16.0.1"}
        
        result = self.ip_monitor.parse_ips(ip_content)
        assert result == expected_ips
    
    def test_parse_ips_invalid(self):
        """测试解析无效IP地址"""
        ip_content = "256.256.256.256, 192.168.1.1, invalid_ip"
        expected_ips = {"192.168.1.1"}
        
        result = self.ip_monitor.parse_ips(ip_content)
        assert result == expected_ips
    
    def test_parse_ips_empty(self):
        """测试解析空内容"""
        ip_content = ""
        expected_ips = set()
        
        result = self.ip_monitor.parse_ips(ip_content)
        assert result == expected_ips
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.read_text')
    def test_load_local_ips_exists(self, mock_read_text, mock_exists):
        """测试加载存在的本地IP文件"""
        mock_exists.return_value = True
        mock_read_text.return_value = "192.168.1.1,\n10.0.0.1"
        
        result = self.ip_monitor.load_local_ips()
        expected_ips = {"192.168.1.1", "10.0.0.1"}
        
        assert result == expected_ips
    
    @patch('pathlib.Path.exists')
    def test_load_local_ips_not_exists(self, mock_exists):
        """测试加载不存在的本地IP文件"""
        mock_exists.return_value = False
        
        result = self.ip_monitor.load_local_ips()
        assert result == set()
    
    def test_check_ip_changes_no_change(self):
        """测试IP无变动的情况"""
        # 模拟远程和本地IP相同
        self.downloader.download_text.return_value = "192.168.1.1,"
        
        with patch.object(self.ip_monitor, 'load_local_ips') as mock_load:
            mock_load.return_value = {"192.168.1.1"}
            
            has_changes, new_content = self.ip_monitor.check_ip_changes()
            
            assert has_changes is False
            assert new_content is None
    
    def test_check_ip_changes_has_change(self):
        """测试IP有变动的情况"""
        # 模拟远程和本地IP不同
        remote_content = "192.168.1.1,\n10.0.0.1"
        self.downloader.download_text.return_value = remote_content
        
        with patch.object(self.ip_monitor, 'load_local_ips') as mock_load:
            mock_load.return_value = {"192.168.1.1"}
            
            has_changes, new_content = self.ip_monitor.check_ip_changes()
            
            assert has_changes is True
            assert new_content == remote_content


if __name__ == '__main__':
    pytest.main([__file__])
