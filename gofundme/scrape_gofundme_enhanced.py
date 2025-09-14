#!/usr/bin/env python3
"""
GoFundMe 前端专用资源爬取脚本 v4.0
前端深度加载模式：
- 只收集前端渲染资源（CSS, JS, 字体, 图片, SVG, 媒体, 文档）
- 完全排除API接口和后端数据请求
- 3分钟深度等待确保页面完全加载
- 桌面/移动端独立保存，专注前端内容
- 过滤跟踪脚本和分析工具
"""

import asyncio
import json
import requests
import socket
import re
import os
import sys
import time
import threading
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.async_api import async_playwright
import socks

# 目标URL
TARGET_URL = "https://www.gofundme.com/f/help-support-michelle-and-her-family-during-this-time"

class NetworkSecurity:
    """网络安全检查类"""
    
    def __init__(self):
        self.current_ip = None
        self.tor_ip = None
        self.is_monitoring = False
        self.monitor_thread = None
    
    def get_current_ip(self, use_proxy=False, proxy_url=None) -> Optional[str]:
        """获取当前IP地址 - 使用curl实现"""
        try:
            import subprocess
            
            # IP检查服务列表 - 优先IPv4服务
            services = [
                'https://ipv4.icanhazip.com',  # 强制IPv4
                'https://api.ipify.org', 
                'https://checkip.amazonaws.com',
                'https://icanhazip.com'  # 可能返回IPv6，放最后
            ]
            
            for i, service in enumerate(services):
                try:
                    if use_proxy and proxy_url:
                        # 使用curl + SOCKS代理
                        cmd = [
                            'curl', '--socks5-hostname', '127.0.0.1:9150',
                            service, '--connect-timeout', '15', '--max-time', '20',
                            '--silent'
                        ]
                        print(f"   🔍 尝试Tor服务 {i+1}/{len(services)}: {service}")
                    else:
                        # 直接使用curl
                        cmd = [
                            'curl', service, '--connect-timeout', '10', '--max-time', '15',
                            '--silent'
                        ]
                        print(f"   🔍 尝试直连服务 {i+1}/{len(services)}: {service}")
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
                    print(f"   📤 curl返回码: {result.returncode}")
                    if result.stderr:
                        print(f"   ⚠️ curl错误: {result.stderr[:100]}")
                    
                    if result.returncode == 0 and result.stdout.strip():
                        ip = result.stdout.strip()
                        print(f"   📥 获取到IP: {ip}")
                        # 检查是否是错误信息
                        if 'error' in ip.lower() or 'too many' in ip.lower() or '{' in ip or '}' in ip:
                            print(f"   ⚠️ 服务返回错误: {ip}")
                            continue
                        if len(ip) < 50 and ('.' in ip or ':' in ip):  # 基本IP验证
                            return ip
                except subprocess.TimeoutExpired:
                    print(f"   ⏰ 服务 {service} 超时")
                    continue
                except Exception as e:
                    print(f"   ❌ 服务 {service} 异常: {e}")
                    continue
            
            print(f"   ❌ 所有IP检查服务都失败了")
            return None
        except Exception as e:
            print(f"⚠️ 获取IP失败: {e}")
            return None
    
    def display_network_status(self) -> bool:
        """显示网络状态并让用户选择"""
        print("\n" + "="*70)
        print("🌐 网络安全状态检查")
        print("="*70)
        
        # 获取当前真实IP
        print("🔍 正在检查当前网络状态...")
        self.current_ip = self.get_current_ip(use_proxy=False)
        
        print(f"\n📍 当前真实IP地址: {self.current_ip or '无法获取'}")
        
        if not self.current_ip:
            print("❌ 无法获取当前IP地址，网络连接可能有问题")
            return False
        
        print("\n⚠️ 安全警告:")
        print("   使用真实IP访问GoFundMe可能暴露您的身份和位置")
        print("   强烈建议使用Tor网络进行匿名访问")
        
        # 用户选择
        print("\n📋 请选择操作:")
        print("   1. 继续检查Tor连接（推荐）")
        print("   2. 使用真实IP继续（不推荐）") 
        print("   3. 退出脚本")
        
        while True:
            choice = input("\n请输入选择 (1/2/3): ").strip()
            
            if choice == "1":
                return self.check_tor_network()
            elif choice == "2":
                print("\n⚠️ 严重警告：您选择使用真实IP继续")
                confirm = input("确定继续？这将暴露您的身份！(yes/NO): ").strip().lower()
                if confirm == "yes":
                    print("⚠️ 已确认使用真实IP模式")
                    return True
                else:
                    print("✅ 明智的选择，请使用Tor网络")
                    return False
            elif choice == "3":
                print("👋 用户选择退出")
                return False
            else:
                print("❌ 无效选择，请输入 1、2 或 3")
    
    def check_tor_network(self) -> bool:
        """检查Tor网络连接"""
        print("\n" + "="*70)
        print("🔐 Tor网络连接检查")
        print("="*70)
        
        # 检测Tor端口
        tor_ports = [9150, 9050]
        working_port = None
        
        print("🔍 扫描Tor SOCKS端口...")
        for port in tor_ports:
            if self._test_port(port):
                print(f"✅ 端口 {port} 可访问")
                working_port = port
                break
            else:
                print(f"❌ 端口 {port} 不可访问")
        
        if not working_port:
            print("\n❌ 未找到可用的Tor SOCKS端口")
            print("\n🔧 解决方案:")
            print("   1. 启动Tor Browser")
            print("   2. 或运行独立Tor服务: tor --SocksPort 9050")
            return False
        
        # 测试Tor连接并获取Tor IP
        proxy_url = f"socks5://127.0.0.1:{working_port}"
        print(f"\n🔐 测试Tor连接: {proxy_url}")
        print("   正在通过Tor获取IP地址...")
        
        self.tor_ip = self.get_current_ip(use_proxy=True, proxy_url=proxy_url)
        
        if not self.tor_ip:
            print("❌ Tor连接测试失败")
            return False
        
        print(f"   ✅ 成功获取Tor IP: {self.tor_ip}")
        
        # 验证是否真的通过Tor
        if self._ips_are_same(self.tor_ip, self.current_ip):
            print(f"❌ 检测到IP泄露！Tor IP与真实IP相同: {self.tor_ip}")
            print("   这表明Tor连接未生效，存在严重安全风险")
            return False
        
        # 显示IP对比
        print("\n🎯 IP地址对比:")
        print(f"   真实IP: {self.current_ip}")  
        print(f"   Tor IP:  {self.tor_ip}")
        print("   ✅ IP地址不同，Tor连接有效")
        
        # 最终确认
        print(f"\n🔒 Tor连接验证成功！")
        print("   您的网络流量将通过Tor网络进行匿名处理")
        
        confirm = input("\n是否使用此Tor连接继续？(Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            # 设置监控
            self.proxy_url = proxy_url
            self.start_ip_monitoring()
            return True
        else:
            print("👋 用户选择不使用Tor连接")
            return False
    
    def _test_port(self, port: int) -> bool:
        """测试端口连通性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _ips_are_same(self, ip1: str, ip2: str) -> bool:
        """智能IP比较 - 考虑IPv4/IPv6差异"""
        if not ip1 or not ip2:
            return False
        
        # 完全相同
        if ip1 == ip2:
            return True
        
        # 提取纯IP部分（去除端口等）
        def extract_ip(ip_str):
            if ',' in ip_str:  # httpbin.org有时返回多个IP
                ip_str = ip_str.split(',')[0].strip()
            if ':' in ip_str and not ip_str.startswith('['):
                # 可能是IPv4:port格式
                parts = ip_str.split(':')
                if len(parts) == 2 and parts[1].isdigit():
                    return parts[0]
            return ip_str.strip()
        
        clean_ip1 = extract_ip(ip1)
        clean_ip2 = extract_ip(ip2)
        
        # 如果清理后的IP相同，则认为是同一个
        if clean_ip1 == clean_ip2:
            return True
        
        # 如果一个是IPv4一个是IPv6，认为是不同的（Tor工作正常）
        ipv4_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        ipv6_pattern = r'^[0-9a-fA-F:]+$'
        
        is_ip1_v4 = re.match(ipv4_pattern, clean_ip1)
        is_ip1_v6 = re.match(ipv6_pattern, clean_ip1) and ':' in clean_ip1
        
        is_ip2_v4 = re.match(ipv4_pattern, clean_ip2)
        is_ip2_v6 = re.match(ipv6_pattern, clean_ip2) and ':' in clean_ip2
        
        # 如果版本不同，认为是不同IP（安全）
        if (is_ip1_v4 and is_ip2_v6) or (is_ip1_v6 and is_ip2_v4):
            return False
        
        return False
    
    def start_ip_monitoring(self):
        """启动IP监控"""
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_ip_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("🔒 已启动实时IP泄露监控")
    
    def stop_ip_monitoring(self):
        """停止IP监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 IP监控已停止")
    
    def _monitor_ip_loop(self):
        """IP监控循环"""
        check_interval = 30  # 30秒检查一次
        
        while self.is_monitoring:
            try:
                current_tor_ip = self.get_current_ip(use_proxy=True, proxy_url=self.proxy_url)
                
                if not current_tor_ip:
                    print("\n🚨 警告：无法获取Tor IP，可能连接中断")
                elif self._ips_are_same(current_tor_ip, self.current_ip):
                    print("\n🚨 严重警告：检测到IP泄露！Tor连接失效")
                    print("   正在终止所有网络活动...")
                    self.is_monitoring = False
                    os._exit(1)  # 立即终止程序
                elif not self._ips_are_same(current_tor_ip, self.tor_ip):
                    print(f"\n🔄 Tor出口节点已更换: {self.tor_ip} → {current_tor_ip}")
                    self.tor_ip = current_tor_ip
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"\n⚠️ IP监控异常: {e}")
                time.sleep(5)

class DownloadManager:
    """下载管理器"""
    
    def __init__(self, proxy_url: str = None, max_workers: int = 3, mode: str = "merged"):
        self.proxy_url = proxy_url
        self.max_workers = max_workers
        self.session = None
        # 使用新的保存目录，避免冲突
        self.progress_file = f"gofundme/scraped_resources_ultra/.download_progress_{mode}.json"
        self.downloaded_files = set()
        self.failed_files = []
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': time.time()
        }
        
    def setup_session(self):
        """设置下载会话"""
        # 🚨 安全检查：必须有Tor代理
        if not self.proxy_url:
            raise Exception("❌ 严重安全错误：下载管理器没有Tor代理配置，禁止下载！")
        
        self.session = requests.Session()
        
        # 强制设置Tor代理
        self.session.proxies = {
            'http': self.proxy_url,
            'https': self.proxy_url
        }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })
        
        print("🔒 下载器已配置强制Tor代理模式")
        
        # 加载断点续传进度
        self._load_progress()
    
    def _load_progress(self):
        """加载下载进度"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.downloaded_files = set(data.get('downloaded', []))
                    print(f"📄 加载断点续传数据: {len(self.downloaded_files)} 个文件已完成")
            except Exception as e:
                print(f"⚠️ 加载进度文件失败: {e}")
    
    def _save_progress(self):
        """保存下载进度"""
        try:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'downloaded': list(self.downloaded_files),
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ 保存进度失败: {e}")
    
    def check_disk_space(self, required_mb: int = 500):
        """检查磁盘空间"""
        try:
            total, used, free = shutil.disk_usage(".")
            free_mb = free // (1024*1024)
            
            if free_mb < required_mb:
                print(f"❌ 磁盘空间不足: 需要{required_mb}MB, 可用{free_mb}MB")
                return False
            
            print(f"✅ 磁盘空间充足: 可用 {free_mb}MB")
            return True
        except Exception as e:
            print(f"⚠️ 无法检查磁盘空间: {e}")
            return True
    
    def download_file(self, url: str, save_path: str, max_retries: int = 3) -> bool:
        """下载单个文件（支持断点续传）"""
        # 检查是否已下载
        if url in self.downloaded_files:
            self.stats['skipped'] += 1
            return True

        # 检查文件是否已存在且完整
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            self.downloaded_files.add(url)
            self.stats['completed'] += 1
            self._save_progress()
            return True
        
        if not self.session:
            self.setup_session()
        
        # 创建目录
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        for attempt in range(max_retries):
            try:
                print(f"⬇️ 下载: {os.path.basename(save_path)} (尝试 {attempt+1}/{max_retries})")
                
                response = self.session.get(url, timeout=30, stream=True)
                response.raise_for_status()
                
                # 下载文件
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证文件
                if os.path.getsize(save_path) > 0:
                    self.downloaded_files.add(url)
                    self.stats['completed'] += 1
                    self._save_progress()
                    print(f"✅ 完成: {os.path.basename(save_path)}")
                    return True
                else:
                    os.remove(save_path)
                    raise Exception("下载的文件为空")
                    
            except Exception as e:
                print(f"❌ 失败: {e}")
                if attempt == max_retries - 1:
                    self.failed_files.append({'url': url, 'path': save_path, 'error': str(e)})
                    self.stats['failed'] += 1
                    return False
                
                # 智能重试延迟
                delay = min(2 ** attempt, 10)
                time.sleep(delay)
        
        return False


    def batch_download(self, download_list: List[Dict[str, str]]):
        """批量下载"""
        if not self.check_disk_space():
            return False
        
        self.stats['total'] = len(download_list)
        print(f"\n🚀 开始批量下载 {self.stats['total']} 个文件...")
        print(f"   最大并发: {self.max_workers} 个线程")
        
        # 显示已有进度
        already_done = len([item for item in download_list if item['url'] in self.downloaded_files])
        if already_done > 0:
            print(f"   断点续传: {already_done} 个文件已完成")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {
                executor.submit(self.download_file, item['url'], item['path']): item
                for item in download_list
            }
            
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    future.result()
                    self._print_progress()
                except Exception as e:
                    print(f"❌ 下载任务异常: {e}")
        
        self._print_final_stats()
        return True
    
    def _print_progress(self):
        """打印进度"""
        completed = self.stats['completed'] + self.stats['skipped']
        progress = completed / self.stats['total'] * 100
        print(f"📊 进度: {completed}/{self.stats['total']} ({progress:.1f}%) - "
              f"✅{self.stats['completed']} ⏭️{self.stats['skipped']} ❌{self.stats['failed']}")
    
    def _print_final_stats(self):
        """打印最终统计"""
        elapsed = time.time() - self.stats['start_time']
        print(f"\n📈 下载完成统计:")
        print(f"   总耗时: {elapsed:.1f}秒")
        print(f"   成功: {self.stats['completed']} 个")
        print(f"   跳过: {self.stats['skipped']} 个") 
        print(f"   失败: {self.stats['failed']} 个")
        
        if self.failed_files:
            self._save_failed_report()
    
    def _save_failed_report(self):
        """保存失败报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"gofundme/scraped_resources_ultra/failed_downloads_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.failed_files, f, ensure_ascii=False, indent=2)
        
        print(f"📋 失败报告: {report_path}")

class ResourceCollector:
    """资源收集器 - 优化版"""
    
    def __init__(self, proxy_url: str = None):
        self.proxy_url = proxy_url
        self.resources = {'desktop': {}, 'mobile': {}}
    
    async def collect_all(self) -> Dict:
        """收集所有资源"""
        print("\n🔍 开始资源收集...")
        
        async with async_playwright() as playwright:
            # 桌面端收集
            print("\n💻 收集桌面端资源...")
            desktop_resources = await self._collect_single_mode(
                playwright, 'desktop', {'viewport': {'width': 1920, 'height': 1080}}
            )
            
            # 等待间隔并清理缓存
            print("\n⏱️ 等待5秒并清理缓存...")
            await asyncio.sleep(5)
            
            # 移动端收集  
            print("\n📱 收集移动端资源...")
            print("   🧹 注意：使用全新浏览器实例避免缓存干扰")
            mobile_resources = await self._collect_single_mode(
                playwright, 'mobile', playwright.devices['iPhone 13 Pro']
            )
            
            return {
                'desktop': desktop_resources,
                'mobile': mobile_resources
            }
    
    async def _collect_single_mode(self, playwright, mode: str, device_config: Dict) -> Dict:
        """收集单一模式的资源"""
        browser = None
        context = None
        
        try:
            # 🚨 安全警告：如果没有Tor代理，必须终止操作
            if not self.proxy_url:
                raise Exception("❌ 严重安全错误：没有Tor代理配置，禁止直接访问目标网站！")
            
            # 设置浏览器 - 强制使用Tor代理
            launch_options = {
                'headless': True,
                'proxy': {'server': self.proxy_url}
            }
            
            browser = await playwright.chromium.launch(**launch_options)
            
            # 设置上下文 - 完全模拟真实Tor Browser  
            if mode == 'mobile':
                user_agent = 'Mozilla/5.0 (Android 10; Mobile; rv:128.0) Gecko/128.0 Firefox/128.0'
            else:
                # 使用更真实的Tor Browser桌面端UA
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0'
            
            # 根据端类型设置不同的配置
            if mode == 'mobile':
                context_options = {
                    'user_agent': user_agent,
                    'ignore_https_errors': True,
                    'java_script_enabled': True,
                    'has_touch': True,
                    'is_mobile': True,
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York',
                    'extra_http_headers': {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0'
                    }
                }
            else:
                # 桌面端使用更简洁的头部，避免触发检测
                context_options = {
                    'user_agent': user_agent,
                    'ignore_https_errors': True,
                    'java_script_enabled': True,
                    'has_touch': False,
                    'is_mobile': False,
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York',
                    'extra_http_headers': {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                }
            context_options.update(device_config)
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            
            # 🔒 安全验证：确保页面通过Tor访问
            print(f"🔍 {mode}端 - 验证Tor连接...")
            try:
                # 先访问IP检查服务确认代理生效 - 使用多个服务
                ip_services = [
                    'https://ipv4.icanhazip.com',
                    'https://checkip.amazonaws.com', 
                    'https://api.ipify.org?format=json'
                ]
                
                current_ip = None
                for service in ip_services:
                    try:
                        await page.goto(service, timeout=15000)
                        ip_content = await page.content()
                        
                        if 'format=json' in service:
                            # JSON格式服务
                            if '"ip":"' in ip_content and 'error' not in ip_content.lower():
                                current_ip = ip_content.split('"ip":"')[1].split('"')[0]
                                break
                        else:
                            # 纯文本服务
                            # 提取页面中的IP（去掉HTML标签）
                            import re
                            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', ip_content)
                            if ip_match:
                                current_ip = ip_match.group(1)
                                break
                    except:
                        continue
                
                if current_ip:
                    print(f"   ✅ {mode}端IP验证: {current_ip}")
                    # 验证不是真实IP
                    if current_ip == '45.137.183.193':  # 更新你的真实IP
                        raise Exception(f"🚨 {mode}端IP泄露！检测到真实IP，立即终止！")
                else:
                    raise Exception(f"❌ {mode}端无法验证IP，可能代理失效")
            except Exception as ip_error:
                print(f"❌ {mode}端IP验证失败: {ip_error}")
                raise
            
            # 先不开始收集资源，等页面完全加载后再从DOM中提取
            resources = {'css': [], 'js': [], 'fonts': [], 'images': [], 'svg': [], 'media': [], 'html': ''}

            print("   🧠 前端专用模式：先让页面完全加载，再收集资源")

            # 🎭 真实浏览行为模拟
            print(f"   🎭 {mode}端 - 开始真实浏览行为模拟")
            
            # 步骤1：先访问主页建立会话
            print("   🏠 访问GoFundMe主页...")
            try:
                await page.goto('https://www.gofundme.com/', wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)  # 等待2秒
                print("   ✅ 主页访问成功")
            except Exception as e:
                print(f"   ⚠️ 主页访问失败: {e}")
            
            # 步骤2：模拟用户行为
            print("   🖱️ 模拟用户交互...")
            try:
                # 模拟鼠标移动和滚动
                await page.mouse.move(100, 100)
                await page.wait_for_timeout(500)
                await page.mouse.move(300, 200) 
                await page.evaluate('window.scrollBy(0, 300)')
                await page.wait_for_timeout(1000)
            except:
                pass
            
            # 步骤3：访问目标页面
            print(f"   🎯 访问目标页面: {TARGET_URL}")
            await page.goto(TARGET_URL, wait_until='networkidle', timeout=60000)
            
            # 步骤4：Ultra深度等待模式 - 等待3分钟让页面完全加载
            print("   🧠 Ultra深度等待模式：初始等待30秒让基础内容加载...")
            await page.wait_for_timeout(30000)  # 初始等待30秒

            # 获取页面初始状态
            initial_content_count = await page.evaluate(
                'document.querySelectorAll("*").length'
            )
            print(f"   📊 页面初始元素数量: {initial_content_count}")

            # 深度滚动触发所有懒加载内容 - 增加等待时间
            print("   🔄 Ultra深度滚动，慢速触发所有动态加载...")

            # 多轮滚动，每轮都彻底一些，总计约90秒
            for round_num in range(3):  # 3轮滚动，每轮约30秒
                print(f"   🔄 第{round_num+1}轮深度滚动（大约30秒）...")

                # 获取当前页面高度
                current_height = await page.evaluate('document.body.scrollHeight')
                viewport_height = await page.evaluate('window.innerHeight')

                # 细致滚动，增加步数让加载更充分
                scroll_steps = max(10, int(current_height / viewport_height) + 5)
                for i in range(scroll_steps):
                    scroll_position = int((i / scroll_steps) * current_height)
                    await page.evaluate(f'window.scrollTo(0, {scroll_position})')

                    # 每次滚动后都等待足够时间让内容加载（增加到8秒）
                    print(f"     📍 滚动步骤 {i+1}/{scroll_steps}，等待内容加载...")
                    await page.wait_for_timeout(8000)

                    # 检查是否有新内容
                    try:
                        await page.wait_for_function(
                            'document.readyState === "complete"',
                            timeout=5000
                        )
                    except:
                        pass

                # 滚动到底部并等待更长时间
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                print(f"     🏁 第{round_num+1}轮滚动完成，等待15秒...")
                await page.wait_for_timeout(15000)

            # 专门处理推荐区域和交互元素
            print("   🎯 Ultra思考：激活所有交互元素...")
            try:
                # 查找并激活各种可能触发内容加载的元素
                interactive_elements = [
                    'button[aria-expanded="false"]',  # 折叠的按钮
                    'button:has-text("Show more")',   # 显示更多按钮
                    'button:has-text("Load more")',   # 加载更多按钮
                    '.dropdown button',               # 下拉菜单
                    '[data-testid*="expand"]',        # 展开按钮
                    '[role="button"][aria-expanded="false"]', # ARIA按钮
                ]

                for selector in interactive_elements:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements[:5]:  # 限制点击数量
                            try:
                                await element.click()
                                await page.wait_for_timeout(8000)  # 增加到8秒等待新内容加载
                                print(f"   ✅ 激活了交互元素: {selector}")
                            except:
                                pass
                    except:
                        continue

            except Exception as e:
                print(f"   ⚠️ 交互元素处理异常: {e}")

            # 最终检查页面内容变化
            final_content_count = await page.evaluate(
                'document.querySelectorAll("*").length'
            )

            print(f"   📊 最终元素数量: {final_content_count} (增加了 {final_content_count - initial_content_count})")

            # 滚动回顶部让所有内容都在视野中
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(10000)

            # 🎯 专门处理用户圈出的三个关键区域
            print("   🎯 Ultra思考：专门处理关键动态内容区域...")

            # 区域1：照片展示区域 "Show your support for this GoFundMe"
            print("   📷 处理照片展示区域...")
            try:
                # 等待并检测照片展示区域
                await page.wait_for_function('''
                    () => {
                        const supportText = document.evaluate("//text()[contains(., 'Show your support')]/..",
                                          document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        return supportText !== null || document.body.innerHTML.includes('Show your support');
                    }
                ''', timeout=10000)

                # 滚动到照片展示区域并等待加载
                await page.evaluate('''
                    () => {
                        const supportText = document.evaluate("//text()[contains(., 'Show your support')]/..",
                                          document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                        if (supportText) {
                            supportText.scrollIntoView({behavior: 'smooth', block: 'center'});
                            return true;
                        }
                        return false;
                    }
                ''')

                await page.wait_for_timeout(8000)  # 等待8秒让照片加载
                print("   ✅ 照片展示区域处理完成")

            except Exception as e:
                print(f"   ⚠️ 照片展示区域处理异常: {e}")

            # 区域2：最近捐赠动态区域 "30 people just donated"
            print("   💰 处理最近捐赠动态区域...")
            try:
                # 等待并检测捐赠动态区域
                donation_found = False
                donation_keywords = [
                    'people just donated',
                    'just donated',
                    'recent donation',
                    'Recent donation',
                    'donation'
                ]

                for keyword in donation_keywords:
                    try:
                        await page.wait_for_function(f'''
                            () => {{
                                const donationText = document.evaluate("//text()[contains(., '{keyword}')]/..",
                                                      document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                return donationText !== null;
                            }}
                        ''', timeout=8000)
                        donation_found = True
                        print(f"   ✅ 发现捐赠动态关键词: {keyword}")
                        break
                    except:
                        continue

                if donation_found:
                    # 滚动到捐赠动态区域
                    await page.evaluate('''
                        () => {
                            const keywords = ['people just donated', 'just donated', 'Recent donation'];
                            for (const keyword of keywords) {
                                const donationElement = document.evaluate("//text()[contains(., '" + keyword + "')]/..",
                                                          document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                if (donationElement) {
                                    donationElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    return true;
                                }
                            }
                            return false;
                        }
                    ''')

                    await page.wait_for_timeout(6000)  # 等待6秒让捐赠动态加载

                    # 尝试展开更多捐赠记录（如果有的话）
                    print("   📋 尝试展开更多捐赠记录...")
                    try:
                        # 使用JavaScript查找捐赠相关按钮
                        donation_buttons_clicked = await page.evaluate('''
                            () => {
                                let clickCount = 0;
                                const donationKeywords = ['see all', 'view all', 'show more', 'see all donations', 'view all donations'];

                                // 1. 先用CSS选择器查找
                                const standardSelectors = [
                                    '[data-testid*="donation"] button',
                                    '[data-testid*="see-all"]'
                                ];

                                for (const selector of standardSelectors) {
                                    try {
                                        const elements = document.querySelectorAll(selector);
                                        for (let i = 0; i < Math.min(elements.length, 2); i++) {
                                            const element = elements[i];
                                            try {
                                                element.scrollIntoView({behavior: 'smooth', block: 'center'});
                                                setTimeout(() => element.click(), 1000 + i * 2000);
                                                clickCount++;
                                            } catch(e) {}
                                        }
                                    } catch(e) {}
                                }

                                // 2. 通过文本查找按钮
                                const allButtons = document.querySelectorAll('button, a');
                                for (const button of allButtons) {
                                    if (clickCount >= 3) break;

                                    const text = (button.textContent || button.innerText || '').toLowerCase();
                                    if (donationKeywords.some(keyword => text.includes(keyword))) {
                                        try {
                                            button.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            setTimeout(() => {
                                                button.click();
                                                console.log('Clicked donation button:', text.substring(0, 20));
                                            }, 3000 + clickCount * 2000);
                                            clickCount++;
                                        } catch(e) {}
                                    }
                                }

                                return clickCount;
                            }
                        ''')

                        if donation_buttons_clicked > 0:
                            print(f"   ✅ 激活了 {donation_buttons_clicked} 个捐赠记录按钮")
                            await page.wait_for_timeout(8000)  # 等待新内容加载
                        else:
                            print("   ⚠️ 未找到捐赠记录扩展按钮")

                    except Exception as e:
                        print(f"   ⚠️ 捐赠记录按钮处理异常: {e}")

                    print("   ✅ 最近捐赠动态区域处理完成")

                else:
                    print("   ⚠️ 未检测到明显的捐赠动态区域，但将在最终扫描中获取")

            except Exception as e:
                print(f"   ⚠️ 最近捐赠动态区域处理异常: {e}")

            # 区域3：底部推荐筹款活动区域 "More ways to make a difference"
            print("   🎯 处理底部推荐筹款活动区域...")
            try:
                # 缓慢滚动到页面最底部，确保触发懒加载
                current_height = await page.evaluate('document.body.scrollHeight')

                # 分步滚动到底部，每步都停留
                for step in range(5):
                    scroll_pos = current_height * (0.7 + step * 0.06)  # 从70%开始，每步增加6%
                    await page.evaluate(f'window.scrollTo(0, {scroll_pos})')
                    await page.wait_for_timeout(3000)  # 每步等待3秒

                # 最终滚动到底部
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(5000)  # 底部停留5秒

                # 专门等待推荐内容出现
                print("   🔍 等待'More ways to make a difference'内容...")
                try:
                    await page.wait_for_function('''
                        () => {
                            const moreText = document.evaluate("//text()[contains(., 'More ways to make a difference') or contains(., 'difference')]/..",
                                              document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            return moreText !== null;
                        }
                    ''', timeout=15000)
                    print("   ✅ 发现'More ways to make a difference'内容")
                except:
                    print("   ⚠️ 未检测到'More ways to make a difference'文本，但继续等待推荐内容...")

                # 查找并激活"Happening worldwide"下拉菜单
                print("   🌍 尝试激活'Happening worldwide'下拉菜单...")
                try:
                    # 使用JavaScript直接查找和点击
                    worldwide_clicked = await page.evaluate('''
                        () => {
                            let clickCount = 0;
                            const keywords = ['worldwide', 'Happening worldwide'];

                            // 查找所有可能的按钮和选择框
                            const allElements = document.querySelectorAll('button, select, [role="button"], [role="combobox"]');

                            for (const element of allElements) {
                                const text = element.textContent || element.innerText || '';
                                if (keywords.some(keyword => text.toLowerCase().includes(keyword.toLowerCase()))) {
                                    try {
                                        element.scrollIntoView({behavior: 'smooth', block: 'center'});
                                        setTimeout(() => element.click(), 500);
                                        clickCount++;
                                        if (clickCount >= 2) break; // 限制点击次数
                                    } catch(e) {
                                        console.log('Click failed for element:', element);
                                    }
                                }
                            }
                            return clickCount;
                        }
                    ''')

                    if worldwide_clicked > 0:
                        print(f"   ✅ 激活了 {worldwide_clicked} 个worldwide相关元素")
                        await page.wait_for_timeout(5000)  # 等待内容加载
                    else:
                        print("   ⚠️ 未找到worldwide相关元素，继续处理")
                except Exception as e:
                    print(f"   ⚠️ worldwide元素处理异常: {e}")

                # 额外等待推荐卡片内容加载
                print("   ⏳ 额外等待15秒让推荐卡片完全加载...")
                await page.wait_for_timeout(15000)

                print("   ✅ 底部推荐区域处理完成")

            except Exception as e:
                print(f"   ⚠️ 底部推荐区域处理异常: {e}")

            # 区域4：激活所有可能的交互元素和隐藏内容
            print("   🔄 Ultra激活：激活所有隐藏的交互内容...")
            try:
                # 使用JavaScript直接查找和激活各种交互元素
                activated_count = await page.evaluate('''
                    () => {
                        let activatedCount = 0;

                        // 定义要查找的文本关键词
                        const textKeywords = ['show more', 'load more', 'see more', 'see all', 'view all'];

                        // 1. 先处理标准CSS选择器可以找到的元素
                        const standardSelectors = [
                            'button[aria-expanded="false"]',
                            '.dropdown button',
                            '[role="button"][aria-expanded="false"]',
                            'button[data-testid*="expand"]',
                            'button[data-testid*="load"]',
                            'button[data-testid*="more"]',
                            'button[data-testid*="recommend"]',
                            'button[data-testid*="suggestion"]',
                            '[data-testid*="card"] button',
                        ];

                        for (const selector of standardSelectors) {
                            try {
                                const elements = document.querySelectorAll(selector);
                                for (let i = 0; i < Math.min(elements.length, 2); i++) {
                                    const element = elements[i];
                                    try {
                                        element.scrollIntoView({behavior: 'smooth', block: 'center'});
                                        setTimeout(() => {
                                            element.click();
                                            console.log('Activated element with selector:', selector);
                                        }, 1000 + i * 1000);
                                        activatedCount++;
                                    } catch(e) {
                                        console.log('Failed to activate element:', selector, e);
                                    }
                                }
                            } catch(e) {
                                continue;
                            }

                            if (activatedCount >= 8) break;
                        }

                        // 2. 通过文本内容查找按钮
                        const allButtons = document.querySelectorAll('button, a[role="button"], [role="button"]');
                        for (const button of allButtons) {
                            if (activatedCount >= 10) break;

                            const text = (button.textContent || button.innerText || '').toLowerCase();
                            if (textKeywords.some(keyword => text.includes(keyword))) {
                                try {
                                    button.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    setTimeout(() => {
                                        button.click();
                                        console.log('Activated text-based button:', text.substring(0, 30));
                                    }, 2000 + activatedCount * 1000);
                                    activatedCount++;
                                } catch(e) {
                                    console.log('Failed to activate text-based button:', e);
                                }
                            }
                        }

                        return activatedCount;
                    }
                ''')

                print(f"   🎯 总共激活了 {activated_count} 个交互元素")

                # 等待所有激活的元素加载新内容
                if activated_count > 0:
                    wait_time = min(activated_count * 3, 30)  # 最多等待30秒
                    print(f"   ⏳ 等待 {wait_time} 秒让激活的元素加载新内容...")
                    await page.wait_for_timeout(wait_time * 1000)

            except Exception as e:
                print(f"   ⚠️ 交互元素激活异常: {e}")

            # 最终深度等待确保所有异步内容都加载完成
            print("   ⏰ 最终深度等待30秒，确保所有新内容都已完全渲染...")
            await page.wait_for_timeout(30000)

            # 最后再次滚动到不同位置确保所有内容都在DOM中
            print("   📍 最终位置检查：滚动到关键位置确保内容在DOM中...")
            key_positions = [0, 0.3, 0.5, 0.7, 0.9, 1.0]  # 关键位置百分比
            page_height = await page.evaluate('document.body.scrollHeight')

            for pos in key_positions:
                scroll_y = int(page_height * pos)
                await page.evaluate(f'window.scrollTo(0, {scroll_y})')
                await page.wait_for_timeout(2000)  # 每个位置停留2秒

            print("   ✅ Ultra深度等待模式渲染完成！总等待时间约5分钟")

            # 🔍 关键内容验证环节
            print("   🔍 Ultra验证：检查关键区域是否成功加载到DOM中...")
            try:
                content_check_results = await page.evaluate('''
                    () => {
                        const results = {
                            photo_gallery: false,
                            recent_donations: false,
                            recommendations: false,
                            total_elements: 0,
                            key_texts_found: []
                        };

                        // 检查总元素数量
                        results.total_elements = document.querySelectorAll('*').length;

                        // 检查照片展示区域
                        const photoTexts = ['Show your support', 'support for this GoFundMe'];
                        for (const text of photoTexts) {
                            if (document.body.innerHTML.includes(text)) {
                                results.photo_gallery = true;
                                results.key_texts_found.push(text);
                                break;
                            }
                        }

                        // 检查最近捐赠区域
                        const donationTexts = ['people just donated', 'just donated', 'Recent donation'];
                        for (const text of donationTexts) {
                            if (document.body.innerHTML.includes(text)) {
                                results.recent_donations = true;
                                results.key_texts_found.push(text);
                                break;
                            }
                        }

                        // 检查底部推荐区域
                        const recommendTexts = ['More ways to make a difference', 'difference', 'Find fundraisers', 'Happening worldwide'];
                        for (const text of recommendTexts) {
                            if (document.body.innerHTML.includes(text)) {
                                results.recommendations = true;
                                results.key_texts_found.push(text);
                                break;
                            }
                        }

                        return results;
                    }
                ''')

                print(f"   📊 内容验证结果:")
                print(f"      📄 总DOM元素: {content_check_results['total_elements']} 个")
                print(f"      📷 照片展示区域: {'✅ 已加载' if content_check_results['photo_gallery'] else '❌ 未检测到'}")
                print(f"      💰 最近捐赠动态: {'✅ 已加载' if content_check_results['recent_donations'] else '❌ 未检测到'}")
                print(f"      🎯 底部推荐区域: {'✅ 已加载' if content_check_results['recommendations'] else '❌ 未检测到'}")

                if content_check_results['key_texts_found']:
                    print(f"      🔑 找到关键文本: {', '.join(content_check_results['key_texts_found'][:5])}")

                # 如果关键区域缺失，给出提示
                missing_areas = []
                if not content_check_results['photo_gallery']:
                    missing_areas.append("照片展示区域")
                if not content_check_results['recent_donations']:
                    missing_areas.append("最近捐赠动态")
                if not content_check_results['recommendations']:
                    missing_areas.append("底部推荐区域")

                if missing_areas:
                    print(f"   ⚠️ 注意：以下区域可能未完全加载：{', '.join(missing_areas)}")
                    print("      这些内容仍可能在HTML中，只是文本匹配未成功")
                else:
                    print("   🎉 所有关键区域都已检测到！HTML应该包含完整的动态内容")

            except Exception as e:
                print(f"   ⚠️ 内容验证过程异常: {e}")

            # 现在页面已完全加载，开始从DOM中提取所有已加载的资源
            print("   🔍 开始从完全加载的页面中提取前端资源...")

            # 使用JavaScript提取页面中所有已加载的资源链接
            page_resources = await page.evaluate('''
                () => {
                    const resources = {
                        css: [],
                        js: [],
                        fonts: [],
                        images: [],
                        svg: [],
                        media: []
                    };

                    // 提取CSS文件
                    document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"][as="style"]').forEach(link => {
                        if (link.href && !link.href.startsWith('data:')) {
                            resources.css.push(link.href);
                        }
                    });

                    // 提取JS文件
                    document.querySelectorAll('script[src]').forEach(script => {
                        if (script.src && !script.src.startsWith('data:')) {
                            // 过滤API和跟踪脚本
                            const skipKeywords = ['analytics', 'tracking', 'gtm', 'facebook', 'twitter', 'google-analytics', 'googletagmanager', 'api.js', 'sdk.js'];
                            if (!skipKeywords.some(keyword => script.src.toLowerCase().includes(keyword))) {
                                resources.js.push(script.src);
                            }
                        }
                    });

                    // 提取字体文件（从CSS和preload中）
                    document.querySelectorAll('link[rel="preload"][as="font"], link[href*=".woff"], link[href*=".ttf"], link[href*=".otf"]').forEach(link => {
                        if (link.href && !link.href.startsWith('data:')) {
                            resources.fonts.push(link.href);
                        }
                    });

                    // 提取图片资源
                    document.querySelectorAll('img, picture source, link[rel="icon"], link[rel="apple-touch-icon"]').forEach(img => {
                        const src = img.src || img.href || img.srcset;
                        if (src && !src.startsWith('data:')) {
                            // 过滤跟踪像素
                            const skipKeywords = ['track', 'pixel', 'beacon', '1x1', 'analytics', 'insight'];
                            if (!skipKeywords.some(keyword => src.toLowerCase().includes(keyword))) {
                                if (src.toLowerCase().includes('.svg') || src.toLowerCase().includes('svg')) {
                                    resources.svg.push(src);
                                } else {
                                    resources.images.push(src);
                                }
                            }
                        }
                    });

                    // 提取SVG文件和use元素引用的sprite
                    document.querySelectorAll('use[href], use[xlink\\\\:href]').forEach(use => {
                        const href = use.getAttribute('href') || use.getAttribute('xlink:href');
                        if (href && href.includes('.svg')) {
                            const spriteFile = href.split('#')[0];
                            if (spriteFile.startsWith('/_next') || spriteFile.startsWith('/')) {
                                resources.svg.push(window.location.origin + spriteFile);
                            } else if (spriteFile.startsWith('http')) {
                                resources.svg.push(spriteFile);
                            }
                        }
                    });

                    // 提取媒体文件
                    document.querySelectorAll('video[src], audio[src], source[src]').forEach(media => {
                        if (media.src && !media.src.startsWith('data:')) {
                            resources.media.push(media.src);
                        }
                    });

                    // 去重
                    Object.keys(resources).forEach(key => {
                        resources[key] = [...new Set(resources[key])];
                    });

                    return resources;
                }
            ''')

            # 将提取的资源赋值给resources对象
            for res_type, urls in page_resources.items():
                resources[res_type] = urls
                if urls:
                    print(f"   ✅ 提取{res_type.upper()}: {len(urls)} 个")

            # 🔧 关键修复：保存HTML前重置页面状态
            print("   🔧 保存HTML前重置页面状态以确保正常滚动...")

            try:
                # 1. 滚动回页面顶部
                await page.evaluate('window.scrollTo({top: 0, behavior: "instant"})')
                await page.wait_for_timeout(2000)

                # 2. 清除可能影响滚动的CSS状态
                await page.evaluate('''
                    () => {
                        // 移除可能阻止滚动的CSS样式
                        document.body.style.overflow = '';
                        document.documentElement.style.overflow = '';

                        // 移除fixed定位或transform可能造成的问题
                        const allElements = document.querySelectorAll('*');
                        allElements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.position === 'fixed' && !el.classList.contains('navbar')) {
                                // 保留导航栏等必要的固定元素
                                el.style.position = '';
                            }
                        });

                        // 确保body可滚动
                        document.body.style.height = '';
                        document.body.style.maxHeight = '';

                        console.log('页面状态已重置，确保正常滚动');
                    }
                ''')

                # 3. 等待页面稳定
                await page.wait_for_timeout(3000)

                # 4. 验证页面可滚动
                scroll_test = await page.evaluate('''
                    () => {
                        const initialY = window.scrollY;
                        window.scrollBy(0, 100);
                        const afterScrollY = window.scrollY;
                        window.scrollTo(0, initialY); // 恢复位置
                        return {
                            canScroll: afterScrollY > initialY,
                            bodyHeight: document.body.scrollHeight,
                            viewportHeight: window.innerHeight
                        };
                    }
                ''')

                if scroll_test['canScroll']:
                    print(f"   ✅ 页面滚动功能正常 (高度: {scroll_test['bodyHeight']}px)")
                else:
                    print("   ⚠️ 页面可能无法滚动，但仍将保存")

                print("   ✅ 页面状态重置完成")

            except Exception as reset_error:
                print(f"   ⚠️ 页面状态重置异常: {reset_error}")
                print("   继续保存HTML...")

            # 获取HTML（现在状态已重置）
            resources['html'] = await page.content()
            
            # 不去重！保持原始收集顺序和数量
            print(f"   🎯 保持原始资源收集，不进行去重处理")
            
            # 统计信息 - 前端专用版（从完全加载的页面中提取）
            total_resources = 0
            frontend_types = ['css', 'js', 'fonts', 'images', 'svg', 'media', 'documents']
            for res_type in frontend_types:
                if res_type in resources:
                    total_resources += len(resources[res_type])

            print(f"\n✅ {mode}端前端资源提取完成（等待3分钟后从DOM提取）:")
            print(f"   🎯 提取的前端资源总数: {total_resources} 个")
            print(f"   📄 CSS: {len(resources['css'])} 个")
            print(f"   📄 JS: {len(resources['js'])} 个")
            print(f"   📄 字体: {len(resources['fonts'])} 个")
            print(f"   📄 图片: {len(resources['images'])} 个")
            print(f"   📄 SVG: {len(resources.get('svg', []))} 个")
            print(f"   📄 媒体: {len(resources.get('media', []))} 个")
            print(f"   🧠 HTML包含完整前端内容: {len(resources['html'])} 字符")

            # 显示文档类型（如果存在）
            if 'documents' in resources and len(resources['documents']) > 0:
                print(f"   📄 文档: {len(resources['documents'])} 个")
            
            return resources
            
        except Exception as e:
            print(f"❌ {mode}端收集失败: {e}")
            return {'css': [], 'js': [], 'fonts': [], 'images': [], 'svg': [], 'media': [], 'html': ''}
        
        finally:
            if context:
                await context.close()
            if browser:
                await browser.close()
    
    def _is_important_image(self, url: str) -> bool:
        """判断是否为重要图片"""
        skip_keywords = ['track', 'pixel', 'beacon', '1x1', 'analytics']
        return not any(keyword in url.lower() for keyword in skip_keywords)
    
    def generate_download_list(self, resources: Dict) -> List[Dict[str, str]]:
        """生成下载列表 - 只包含前端资源，排除API相关文件"""
        download_list = []

        # 只处理前端相关的资源类型
        frontend_resource_types = ['css', 'js', 'fonts', 'images', 'svg', 'media', 'documents']

        # 桌面端前端资源
        print(f"\n📊 桌面端前端资源统计:")
        desktop_count = 0

        for res_type in frontend_resource_types:
            urls = resources['desktop'].get(res_type, [])
            count = len(urls)
            if count > 0:
                print(f"   📄 {res_type.upper()}: {count} 个")
                desktop_count += count

                for url in urls:
                    # 保持原始路径结构，特别是_next目录
                    if url.startswith('https://www.gofundme.com/'):
                        # 提取原始路径部分
                        original_path = url.replace('https://www.gofundme.com/', '')
                        # 去掉片段标识符(#)
                        if '#' in original_path:
                            original_path = original_path.split('#')[0]
                        save_path = os.path.join("gofundme/scraped_resources_ultra/desktop", original_path)
                    else:
                        filename = self._url_to_safe_filename(url, res_type)
                        save_path = os.path.join("gofundme/scraped_resources_ultra/desktop", res_type, filename)

                    download_list.append({
                        'url': url,
                        'path': save_path,
                        'type': f"desktop_{res_type}"
                    })

        print(f"   🎯 桌面端前端资源: {desktop_count} 个文件")

        # 移动端前端资源
        print(f"\n📊 移动端前端资源统计:")
        mobile_count = 0

        for res_type in frontend_resource_types:
            urls = resources['mobile'].get(res_type, [])
            count = len(urls)
            if count > 0:
                print(f"   📄 {res_type.upper()}: {count} 个")
                mobile_count += count

                for url in urls:
                    # 保持原始路径结构，特别是_next目录
                    if url.startswith('https://www.gofundme.com/'):
                        # 提取原始路径部分
                        original_path = url.replace('https://www.gofundme.com/', '')
                        # 去掉片段标识符(#)
                        if '#' in original_path:
                            original_path = original_path.split('#')[0]
                        save_path = os.path.join("gofundme/scraped_resources_ultra/mobile", original_path)
                    else:
                        filename = self._url_to_safe_filename(url, res_type)
                        save_path = os.path.join("gofundme/scraped_resources_ultra/mobile", res_type, filename)

                    download_list.append({
                        'url': url,
                        'path': save_path,
                        'type': f"mobile_{res_type}"
                    })
        print(f"   🎯 移动端前端资源: {mobile_count} 个文件")

        total_files = desktop_count + mobile_count
        print(f"\n🎯 总计将下载: {total_files} 个前端文件 (桌面{desktop_count} + 移动{mobile_count})")
        print("   ✅ 已排除所有API接口相关文件，只保留前端渲染资源")

        return download_list
    
    def _url_to_safe_filename(self, url: str, file_type: str) -> str:
        """生成安全的文件名"""
        # 获取原始文件名
        parts = url.split('/')
        original_name = parts[-1] if parts else 'unknown'
        
        # 移除查询参数
        if '?' in original_name:
            original_name = original_name.split('?')[0]
        
        # 如果文件名过长或无扩展名，生成hash名称
        if len(original_name) > 50 or '.' not in original_name:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            extensions = {
                'css': '.css',
                'js': '.js',
                'fonts': '.woff2',
                'images': '.png',
                'svg': '.svg',
                'media': '.mp4',
                'documents': '.html'
            }
            original_name = f"{file_type}_{url_hash}{extensions.get(file_type, '.dat')}"
        
        # 清理特殊字符
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', original_name)
        
        return safe_name
    
    def save_html_files(self, resources: Dict):
        """保存HTML文件 - Ultra思考版"""
        for mode in ['desktop', 'mobile']:
            html_content = resources[mode]['html']

            # 保存完整HTML
            html_path = f"gofundme/scraped_resources_ultra/{mode}/index.html"
            os.makedirs(os.path.dirname(html_path), exist_ok=True)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"📄 {mode}版完整HTML已保存: {html_path}")
            print(f"   🧠 HTML大小: {len(html_content):,} 字符 (包含所有动态内容)")

            # 额外：保存动态内容提取版本
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')

                # 提取可能包含动态内容的重要元素
                dynamic_content = {
                    'fundraiser_cards': [],
                    'recommendation_items': [],
                    'dynamic_sections': [],
                    'data_elements': []
                }

                # 查找筹款项目卡片
                cards = soup.find_all(['div', 'article'], class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['card', 'item', 'fundraiser', 'campaign']
                ))
                dynamic_content['fundraiser_cards'] = [str(card) for card in cards[:10]]

                # 查找推荐区域
                recommendations = soup.find_all(['section', 'div'], class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['recommend', 'suggest', 'related', 'more']
                ))
                dynamic_content['recommendation_items'] = [str(rec) for rec in recommendations[:5]]

                # 查找带有data属性的元素（通常是动态内容）
                data_elements = soup.find_all(attrs={'data-testid': True})
                dynamic_content['data_elements'] = [str(elem)[:500] for elem in data_elements[:20]]

                # 保存动态内容摘要
                dynamic_path = f"gofundme/scraped_resources_ultra/{mode}/dynamic_content.json"
                with open(dynamic_path, 'w', encoding='utf-8') as f:
                    json.dump(dynamic_content, f, ensure_ascii=False, indent=2)

                print(f"🧠 {mode}版动态内容摘要已保存: {dynamic_path}")

            except ImportError:
                print("   ⚠️ 需要 beautifulsoup4 来提取动态内容摘要")
            except Exception as e:
                print(f"   ⚠️ 动态内容摘要生成失败: {e}")

class SVGSpriteCollector:
    """SVG Sprite文件专项收集器"""

    def __init__(self, proxy_url: str = None):
        self.proxy_url = proxy_url
        self.target_url = TARGET_URL
        self.svg_sprites = []

    async def collect_svg_sprites(self):
        """专门收集SVG sprite文件"""
        print("🎯 开始SVG Sprite专项收集...")

        async with async_playwright() as playwright:
            # 使用简化的浏览器配置
            launch_options = {
                'headless': True,
                'proxy': {'server': self.proxy_url} if self.proxy_url else None
            }

            browser = await playwright.chromium.launch(**launch_options)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0'
            )

            try:
                page = await context.new_page()

                # 监控所有请求，专门寻找SVG文件
                svg_files = []
                def handle_request(request):
                    url = request.url
                    if url.endswith('.svg'):
                        svg_files.append(url)
                        print(f"🎯 发现SVG文件: {url}")

                page.on('request', handle_request)

                # 访问目标页面
                print(f"🌐 正在访问: {self.target_url}")
                await page.goto(self.target_url, wait_until='networkidle', timeout=60000)

                # 等待页面完全加载
                await page.wait_for_timeout(5000)

                # 从HTML中提取SVG sprite引用
                sprite_refs = await page.evaluate('''
                    () => {
                        const useElements = document.querySelectorAll('use[href]');
                        const spriteFiles = new Set();
                        useElements.forEach(use => {
                            const href = use.getAttribute('href');
                            if (href && href.includes('.svg#')) {
                                const spriteFile = href.split('#')[0];
                                // 转换相对路径为绝对路径
                                if (spriteFile.startsWith('/_next')) {
                                    spriteFiles.add('https://www.gofundme.com' + spriteFile);
                                } else if (!spriteFile.startsWith('http')) {
                                    spriteFiles.add(window.location.origin + spriteFile);
                                } else {
                                    spriteFiles.add(spriteFile);
                                }
                            }
                        });
                        return Array.from(spriteFiles);
                    }
                ''')

                # 合并发现的SVG文件
                all_svg_files = list(set(svg_files + sprite_refs))

                print(f"✅ SVG收集完成:")
                print(f"   📡 网络请求中的SVG: {len(svg_files)} 个")
                print(f"   🔗 HTML引用的Sprite: {len(sprite_refs)} 个")
                print(f"   🎯 总计SVG文件: {len(all_svg_files)} 个")

                for svg_url in all_svg_files:
                    print(f"   📄 {svg_url}")

                self.svg_sprites = all_svg_files
                return all_svg_files

            finally:
                await context.close()
                await browser.close()

    def download_svg_sprites(self):
        """下载SVG sprite文件"""
        if not self.svg_sprites:
            print("❌ 没有找到SVG文件")
            return False

        print(f"\n⬇️ 开始下载 {len(self.svg_sprites)} 个SVG文件...")

        # 使用现有的下载器
        downloader = DownloadManager(self.proxy_url, max_workers=2, mode="svg_sprites")
        downloader.setup_session()

        # 确保目录存在
        import os
        os.makedirs("gofundme/scraped_resources_ultra/desktop/svg", exist_ok=True)
        os.makedirs("gofundme/scraped_resources_ultra/mobile/svg", exist_ok=True)

        # 生成下载列表
        download_list = []
        for svg_url in self.svg_sprites:
            filename = self._url_to_filename(svg_url)
            download_list.append({
                'url': svg_url,
                'path': f"gofundme/scraped_resources_ultra/desktop/svg/{filename}"
            })
            # 同时为移动端下载
            download_list.append({
                'url': svg_url,
                'path': f"gofundme/scraped_resources_ultra/mobile/svg/{filename}"
            })

        success = downloader.batch_download(download_list)

        if success:
            print("✅ SVG Sprite文件下载完成！")
            print("📁 文件位置:")
            print("   - gofundme/scraped_resources_ultra/desktop/svg/")
            print("   - gofundme/scraped_resources_ultra/mobile/svg/")

        return success

    def _url_to_filename(self, url: str) -> str:
        """从URL生成文件名"""
        # 提取文件名
        filename = url.split('/')[-1]

        # 如果没有.svg扩展名，添加它
        if not filename.endswith('.svg'):
            # 使用URL的hash作为文件名
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"sprite_{url_hash}.svg"

        # 清理特殊字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        return filename

def main():
    """主函数 - 增强版"""
    # 检查是否为SVG专项模式
    import sys
    svg_mode = '--svg-only' in sys.argv or '--svg' in sys.argv

    if svg_mode:
        print("🎯 GoFundMe SVG Sprite专项爬取模式 [Ultra版本]")
        print("="*60)
    else:
        print("🎯 GoFundMe 前端专用资源爬取脚本 v4.0")
        print("🧠 前端深度加载 - 3分钟等待 - 排除API - 专注前端")
        print("="*60)
    
    # 第一步：网络安全检查
    security = NetworkSecurity()
    if not security.display_network_status():
        print("👋 脚本退出")
        return
    
    proxy_url = getattr(security, 'proxy_url', None)
    
    # 🚨 最终安全检查
    if not proxy_url:
        print("\n❌ 严重安全错误：没有有效的Tor代理配置！")
        print("   为了保护您的隐私，禁止在没有Tor保护的情况下访问目标网站")
        return
    
    print(f"🔒 确认使用Tor代理: {proxy_url}")

    try:
        if svg_mode:
            # SVG专项模式
            print("\n" + "="*60)
            print("🎯 SVG Sprite专项收集阶段")
            print("="*60)

            svg_collector = SVGSpriteCollector(proxy_url)
            svg_files = asyncio.run(svg_collector.collect_svg_sprites())

            if svg_files:
                print(f"\n🎯 找到 {len(svg_files)} 个SVG文件")
                for i, svg_url in enumerate(svg_files, 1):
                    print(f"   {i}. {svg_url}")

                confirm = input(f"\n是否下载这 {len(svg_files)} 个SVG文件？(Y/n): ").strip().lower()
                if confirm not in ['', 'y', 'yes']:
                    print("👋 用户取消下载")
                    return

                # 下载SVG文件
                success = svg_collector.download_svg_sprites()
                if success:
                    print("\n🎉 SVG Sprite文件补充完成！")
                    print("💡 提示：现在你的爬取结果应该能正常显示图标了")
                else:
                    print("\n⚠️ SVG文件下载遇到问题")
            else:
                print("❌ 未发现任何SVG文件，可能需要检查网络或目标页面")

            return

        # 常规完整模式
        print("\n" + "="*60)
        print("🔍 资源收集阶段")
        print("="*60)

        collector = ResourceCollector(proxy_url)
        resources = asyncio.run(collector.collect_all())
        
        # 保存HTML
        collector.save_html_files(resources)
        
        # 生成下载清单
        download_list = collector.generate_download_list(resources)
        print(f"\n📋 生成下载清单: {len(download_list)} 个文件")
        
        # 用户确认
        print(f"\n⚠️ 即将下载 {len(download_list)} 个文件到本地")
        confirm = input("是否继续下载？(Y/n): ").strip().lower()
        if confirm not in ['', 'y', 'yes']:
            print("👋 用户取消下载")
            return
        
        # 第三步：批量下载
        print("\n" + "="*60)
        print("⬇️ 批量下载阶段")
        print("="*60)
        
        downloader = DownloadManager(proxy_url, max_workers=3)
        success = downloader.batch_download(download_list)
        
        if success:
            print("\n🎉 GoFundMe资源爬取完成！")
            print("📁 资源位置: gofundme/scraped_resources_ultra/")
        else:
            print("\n⚠️ 下载过程中遇到问题，请查看错误报告")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
    finally:
        # 停止监控
        if hasattr(security, 'stop_ip_monitoring'):
            security.stop_ip_monitoring()

if __name__ == "__main__":
    # 检查帮助参数
    import sys
    if '--help' in sys.argv or '-h' in sys.argv:
        print("🎯 GoFundMe 前端专用资源爬取脚本 v4.0")
        print("🧠 前端深度加载 - 3分钟等待 - 排除API - 专注前端")
        print("="*60)
        print("📋 使用方法:")
        print("   python scrape_gofundme_enhanced.py           # 前端专用模式（只爬前端资源）")
        print("   python scrape_gofundme_enhanced.py --svg     # SVG专项模式（只爬取图标文件）")
        print("   python scrape_gofundme_enhanced.py --help    # 显示此帮助")
        print()
        print("🧠 前端专用模式特性:")
        print("   - 只收集前端渲染资源：CSS, JS, 字体, 图片, SVG, 媒体, 文档")
        print("   - 完全排除API接口请求和后端数据")
        print("   - 3分钟深度等待确保页面完全加载")
        print("   - 过滤跟踪脚本、分析工具和广告")
        print("   - 桌面端和移动端独立保存")
        print()
        print("🎯 SVG专项模式:")
        print("   专门用于补充缺失的图标文件，解决页面图标不显示的问题")
        print("   快速、精准，只下载必要的SVG Sprite文件")
        print()
        print("💡 前端专用建议:")
        print("   这个版本专门为前端页面还原设计，不爬取API数据")
        print("   适合需要完整前端展示但不涉及后端交互的场景")
        print("   等待时间较长（约3分钟），请耐心等待页面完全加载")
        exit(0)

    main()