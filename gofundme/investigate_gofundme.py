import asyncio
import json
import requests
import socket
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from playwright.async_api import async_playwright
import socks

def check_local_ip():
    """检查本地IP地址"""
    print("检查本地IP地址...")
    try:
        # 通过连接到外部服务检查公网IP
        response = requests.get('https://httpbin.org/ip', timeout=10)
        if response.status_code == 200:
            ip_info = response.json()
            print(f"当前公网IP: {ip_info.get('origin', 'Unknown')}")
            return ip_info.get('origin', 'Unknown')
        else:
            print("无法获取公网IP")
            return None
    except Exception as e:
        print(f"获取IP地址失败: {e}")
        return None

def check_tor_connection(allow_skip=False):
    """
    简化的Tor连接检查函数
    返回: 成功时返回代理字符串 (如 "socks5://127.0.0.1:9150")，失败时返回 None
    """
    print("=" * 60)
    print("🔐 执行Tor连接检查...")
    print("=" * 60)
    
    # 测试端口连通性
    def test_port(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    # 测试常见的Tor端口
    tor_ports = [9150, 9050]  # 9150是Tor Browser默认端口，9050是Tor服务端口
    
    print("🔍 检查Tor SOCKS代理端口...")
    for port in tor_ports:
        if not test_port(port):
            print(f"❌ 端口 {port} 不可访问")
            continue
            
        print(f"✅ 端口 {port} 可访问，测试Tor连接...")
        
        try:
            # 使用requests.Session测试Tor连接
            session = requests.Session()
            session.proxies = {
                'http': f'socks5h://127.0.0.1:{port}',
                'https': f'socks5h://127.0.0.1:{port}'
            }
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0'
            })
            
            response = session.get('https://check.torproject.org/api/ip', timeout=30)
            
            if response.status_code == 200:
                tor_info = response.json()
                is_tor = tor_info.get('IsTor', False)
                ip = tor_info.get('IP', 'Unknown')
                
                print(f"🌐 检测到的IP地址: {ip}")
                print(f"🔒 Tor状态: {'✅ 已连接' if is_tor else '❌ 未连接'}")
                
                if is_tor:
                    print("✅ Tor连接验证成功！")
                    return f"socks5://127.0.0.1:{port}"
                else:
                    print(f"⚠️ 端口 {port} 可访问但未通过Tor路由")
            else:
                print(f"⚠️ 端口 {port} 连接测试失败 (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"⚠️ 端口 {port} 连接测试异常: {e}")
    
    # 所有端口都失败
    print("❌ 未找到可用的Tor连接")
    print("\n🔧 Tor配置解决方案:")
    print("方案1: 配置Tor Browser允许外部连接")
    print("   1. 打开Tor Browser")
    print("   2. 在地址栏输入: about:config")
    print("   3. 搜索并设置: network.proxy.socks_remote_dns = true")
    print("\n方案2: 使用独立的Tor服务")
    print("   1. 下载Tor Expert Bundle")
    print("   2. 运行: tor.exe --SocksPort 9050")
    
    if allow_skip:
        print("\n⚠️ 测试模式：允许跳过Tor检查")
        user_input = input("是否跳过Tor检查继续执行？(y/N): ").strip().lower()
        if user_input in ['y', 'yes']:
            print("⚠️ 警告：跳过Tor检查，直接连接")
            return "skip"  # 返回特殊值表示跳过
    
    return None

# 硬编码目标URL
TARGET_URL = "https://www.gofundme.com/f/axmft-help-ahmad-and-his-family"

class ReconnaissanceData:
    """侦察数据存储类"""
    def __init__(self, mode: str):
        self.mode = mode  # 'desktop' 或 'mobile'
        self.timestamp = datetime.now().isoformat()
        self.resources = {
            'css_files': [],
            'js_files': [],
            'font_files': [],
            'image_files': []
        }
        self.network_requests = []
        self.api_endpoints = []
        self.html_content = ""
        self.interactive_elements = []
        self.css_animations = {
            'animation_count': 0,
            'transition_count': 0,
            'keyframes_count': 0,
            'details': []
        }
        self.third_party_scripts = []
        self.screenshot_path = ""
        self.extracted_data = {}

class PlaywrightRecon:
    """Playwright侦察主类"""
    
    def __init__(self, proxy_url=None):
        self.desktop_data = None
        self.mobile_data = None
        self.proxy_url = proxy_url

    async def setup_browser_with_tor(self, playwright, device_config=None, mode="desktop"):
        """设置带Tor代理的浏览器"""
        launch_options = {
            'headless': True,
            'args': [
                "--disable-web-security",
                "--no-sandbox", 
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--no-first-run",
                "--no-default-browser-check"
            ]
        }
        
        # 使用Playwright官方推荐的proxy参数
        if self.proxy_url and self.proxy_url != "skip":
            launch_options['proxy'] = {'server': self.proxy_url}
            print(f"🔐 使用Tor代理: {self.proxy_url}")
        else:
            print("⚠️ 警告：未使用Tor代理，直接连接")
        
        browser = await playwright.chromium.launch(**launch_options)
        
        # 根据模式设置不同的User-Agent
        if mode == "mobile":
            user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        else:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # 创建上下文
        context_options = {
            'ignore_https_errors': True,
            'user_agent': user_agent,
            'java_script_enabled': True,
            'bypass_csp': True,
            'extra_http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        if device_config:
            context_options.update(device_config)
            
        context = await browser.new_context(**context_options)
        
        # 注入反检测脚本
        await context.add_init_script("""
            // 移除webdriver标识
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 设置语言偏好
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'zh-CN'],
            });
            
            // 伪造插件数量
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' },
                    { name: 'Chromium PDF Plugin' },
                    { name: 'Microsoft Edge PDF Plugin' }
                ],
            });
            
            // 覆盖window.chrome
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 覆盖permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 伪造deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
            });
            
            // 伪造hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4,
            });
            
            // 移除selenium相关属性
            delete window.document.$cdc_asdjflasutopfhvcZLmcfl_;
            delete window.$chrome_asyncScriptInfo;
            
            // 伪造Connection API
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    downlink: 10,
                    effectiveType: '4g',
                    onchange: null,
                    rtt: 100,
                    saveData: false
                }),
            });
            
            // 伪造Battery API
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1.0
                });
            }
        """)
        
        return browser, context
    
    async def monitor_network_requests(self, page, recon_data: ReconnaissanceData):
        """监控网络请求"""
        def handle_request(request):
            url = request.url
            resource_type = request.resource_type
            
            recon_data.network_requests.append({
                'url': url,
                'resource_type': resource_type,
                'method': request.method
            })
            
            # 分类资源文件
            if resource_type == 'stylesheet':
                recon_data.resources['css_files'].append(url)
            elif resource_type == 'script':
                recon_data.resources['js_files'].append(url)
                # 检查是否为第三方脚本
                if any(domain in url for domain in ['google', 'facebook', 'stripe', 'paypal', 'analytics']):
                    recon_data.third_party_scripts.append(url)
            elif resource_type == 'font':
                recon_data.resources['font_files'].append(url)
            elif resource_type == 'image':
                recon_data.resources['image_files'].append(url)
                
            # 检查API端点
            if '/api/' in url or url.endswith('.json') or 'graphql' in url:
                recon_data.api_endpoints.append(url)
        
        page.on('request', handle_request)
    
    async def analyze_interactive_elements(self, page, recon_data: ReconnaissanceData):
        """分析交互元素"""
        interactive_selectors = [
            'button',
            'a[href]',
            'input',
            '[onclick]',
            '[role="button"]',
            '.btn, .button',
            '[data-testid*="button"]',
            '[data-testid*="donate"]',
            '[class*="share"]',
            '[class*="expand"]'
        ]
        
        for selector in interactive_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.inner_text() if element else ""
                    if text and len(text.strip()) > 0:
                        recon_data.interactive_elements.append({
                            'selector': selector,
                            'text': text.strip()[:100],  # 限制长度
                            'tag': await element.evaluate('el => el.tagName.toLowerCase()') if element else ""
                        })
            except Exception as e:
                print(f"⚠️ 分析交互元素时出错 {selector}: {e}")
    
    async def analyze_css_animations(self, page, recon_data: ReconnaissanceData):
        """分析CSS动画"""
        try:
            # 获取所有样式表内容
            css_content = await page.evaluate('''
                () => {
                    let allCSS = '';
                    for (let sheet of document.styleSheets) {
                        try {
                            for (let rule of sheet.cssRules) {
                                allCSS += rule.cssText + '\\n';
                            }
                        } catch (e) {
                            // 跨域样式表无法访问
                        }
                    }
                    return allCSS;
                }
            ''')
            
            # 使用正则表达式分析动画相关CSS
            animation_patterns = {
                'animation': r'animation\s*:',
                'transition': r'transition\s*:',
                'keyframes': r'@keyframes\s+[\w-]+'
            }
            
            for pattern_name, pattern in animation_patterns.items():
                matches = re.findall(pattern, css_content, re.IGNORECASE)
                count = len(matches)
                recon_data.css_animations[f'{pattern_name}_count'] = count
                
                if count > 0:
                    recon_data.css_animations['details'].append({
                        'type': pattern_name,
                        'count': count,
                        'examples': matches[:5]  # 只保存前5个示例
                    })
                    
        except Exception as e:
            print(f"⚠️ 分析CSS动画时出错: {e}")

    async def extract_gofundme_data_playwright(self, page, user_agent_type="desktop"):
        """使用Playwright提取GoFundMe页面数据"""
        
        # 定义关键字段选择器
        selectors = {
            'campaign_title': "h1, [data-testid='campaign-title'], .campaign-title, .hrt-title-text",
            'campaign_description': "[data-testid='campaign-description'], .campaign-description, .hrt-text-body, .co-story__content",
            'fundraiser_name': "[data-testid='fundraiser-name'], .fundraiser-name, .hrt-avatar-name",
            'goal_amount': "[data-testid='goal-amount'], .goal-amount, .hrt-progress-bar__goal-text",
            'raised_amount': "[data-testid='raised-amount'], .raised-amount, .hrt-progress-bar__current-text",
            'donors_count': "[data-testid='donors-count'], .donors-count, .hrt-progress-bar__contributors",
            'campaign_updates': "[data-testid='updates'] .update, .campaign-updates .update",
            'recent_donations': "[data-testid='recent-donations'] .donation, .recent-donations .donation",
            'share_buttons': "[data-testid='share-buttons'] a, .share-buttons a"
        }
        
        extracted_data = {}
        
        # 提取各个字段的数据
        for field_name, selector in selectors.items():
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    texts = []
                    for element in elements:
                        text = await element.inner_text()
                        if text and text.strip():
                            texts.append(text.strip())
                    
                    if texts:
                        extracted_data[field_name] = texts if len(texts) > 1 else texts[0]
                    else:
                        extracted_data[field_name] = "未找到"
                else:
                    extracted_data[field_name] = "未找到"
            except Exception as e:
                print(f"⚠️ 提取字段 {field_name} 时出错: {e}")
                extracted_data[field_name] = "提取失败"
        
        return extracted_data

    async def reconnaissance_mode(self, playwright, mode: str, max_retries=3):
        """执行单一模式的侦察"""
        print(f"\n🔍 开始{mode}模式侦察...")
        
        recon_data = ReconnaissanceData(mode)
        
        # 设置设备配置
        if mode == 'mobile':
            device_config = playwright.devices['iPhone 13 Pro']
        else:
            device_config = {'viewport': {'width': 1920, 'height': 1080}}
        
        for attempt in range(max_retries):
            try:
                print(f"🚀 尝试第 {attempt + 1}/{max_retries} 次连接...")
                
                browser, context = await self.setup_browser_with_tor(playwright, device_config, mode)
                
                try:
                    page = await context.new_page()
                    
                    # 设置网络监控
                    await self.monitor_network_requests(page, recon_data)
                    
                    # 添加随机延迟 (1-3秒)
                    import random
                    delay = random.uniform(1, 3)
                    print(f"⏱️ 等待 {delay:.1f}s 后访问...")
                    await page.wait_for_timeout(int(delay * 1000))
                    
                    print(f"📱 正在访问目标URL ({mode}模式)...")
                    
                    # 使用更宽松的等待条件
                    response = await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=60000)
                    
                    # 检查响应状态
                    if response and response.status == 403:
                        print(f"⚠️ 收到403错误，尝试第 {attempt + 1} 次")
                        if attempt < max_retries - 1:
                            await context.close()
                            await browser.close()
                            # 增加等待时间后重试
                            retry_delay = (attempt + 1) * 5  # 5s, 10s, 15s
                            print(f"⏱️ 等待 {retry_delay}s 后重试...")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise Exception(f"多次尝试后仍收到403错误")
                    
                    print(f"✅ 页面加载成功 (状态码: {response.status if response else 'Unknown'})")
                    
                    # 等待页面完全加载
                    await page.wait_for_timeout(5000)
                    
                    # 等待关键元素出现 (如果有)
                    try:
                        await page.wait_for_selector('body', timeout=10000)
                        print("✅ 页面内容已完全加载")
                    except Exception:
                        print("⚠️ 等待页面内容加载超时，继续执行...")
                    
                    print(f"📊 收集{mode}模式数据...")
                    
                    # 获取HTML内容
                    recon_data.html_content = await page.content()
                    
                    # 提取结构化数据
                    recon_data.extracted_data = await self.extract_gofundme_data_playwright(page, mode)
                    
                    # 分析交互元素
                    await self.analyze_interactive_elements(page, recon_data)
                    
                    # 分析CSS动画
                    await self.analyze_css_animations(page, recon_data)
                    
                    # 截屏
                    screenshot_filename = f"gofundme/{mode}_view.png"
                    await page.screenshot(path=screenshot_filename, full_page=True)
                    recon_data.screenshot_path = screenshot_filename
                    print(f"📸 截屏已保存: {screenshot_filename}")
                    
                    print(f"✅ {mode}模式侦察完成")
                    
                    # 成功则跳出重试循环
                    break
                    
                finally:
                    await context.close()
                    await browser.close()
                    
            except Exception as e:
                print(f"❌ 第 {attempt + 1} 次尝试失败: {e}")
                if attempt < max_retries - 1:
                    retry_delay = (attempt + 1) * 5  # 5s, 10s, 15s
                    print(f"⏱️ 等待 {retry_delay}s 后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    print(f"❌ {mode}模式侦察失败，已达最大重试次数")
                    raise
                    
        return recon_data

    def generate_comparison_report(self):
        """生成对比分析报告"""
        print("\n📝 生成对比分析报告...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 计算克隆难度
        def calculate_clone_difficulty():
            desktop_js = len(self.desktop_data.resources['js_files'])
            total_animations = (self.desktop_data.css_animations['animation_count'] + 
                              self.desktop_data.css_animations['transition_count'])
            
            if desktop_js > 20 or total_animations > 10:
                return "高"
            elif desktop_js > 10 or total_animations > 5:
                return "中"
            else:
                return "低"
        
        # 分析移动端适配方案
        def analyze_mobile_adaptation():
            html_diff = len(set(self.desktop_data.html_content) - set(self.mobile_data.html_content))
            css_diff = len(set(self.desktop_data.resources['css_files']) - set(self.mobile_data.resources['css_files']))
            
            if html_diff < 1000 and css_diff < 2:
                return "主要通过CSS媒体查询实现，HTML结构基本一致"
            else:
                return "使用动态渲染，桌面和移动版有不同的HTML结构"
        
        report = {
            "侦察报告": {
                "生成时间": timestamp,
                "目标URL": TARGET_URL,
                "侦察模式": ["桌面 (1920x1080)", "移动 (iPhone 13 Pro)"]
            },
            "总体评估": {
                "克隆难度": calculate_clone_difficulty(),
                "移动端适配方案": analyze_mobile_adaptation(),
                "核心技术栈": "待进一步分析"
            },
            "桌面vs移动对比分析": {
                "CSS文件数量": {
                    "桌面": len(self.desktop_data.resources['css_files']),
                    "移动": len(self.mobile_data.resources['css_files']),
                    "差异": list(set(self.desktop_data.resources['css_files']) - set(self.mobile_data.resources['css_files']))
                },
                "JS文件数量": {
                    "桌面": len(self.desktop_data.resources['js_files']),
                    "移动": len(self.mobile_data.resources['js_files']),
                    "差异": list(set(self.desktop_data.resources['js_files']) - set(self.mobile_data.resources['js_files']))
                },
                "总网络请求数": {
                    "桌面": len(self.desktop_data.network_requests),
                    "移动": len(self.mobile_data.network_requests)
                },
                "API端点": {
                    "桌面": self.desktop_data.api_endpoints,
                    "移动": self.mobile_data.api_endpoints,
                    "共同端点": list(set(self.desktop_data.api_endpoints) & set(self.mobile_data.api_endpoints))
                }
            },
            "交互与动画分析": {
                "桌面交互元素数量": len(self.desktop_data.interactive_elements),
                "移动交互元素数量": len(self.mobile_data.interactive_elements),
                "关键交互元素": self.desktop_data.interactive_elements[:10],  # 前10个
                "动画复杂度": {
                    "桌面": {
                        "动画数量": self.desktop_data.css_animations['animation_count'],
                        "过渡数量": self.desktop_data.css_animations['transition_count'],
                        "关键帧数量": self.desktop_data.css_animations['keyframes_count']
                    },
                    "移动": {
                        "动画数量": self.mobile_data.css_animations['animation_count'],
                        "过渡数量": self.mobile_data.css_animations['transition_count'],
                        "关键帧数量": self.mobile_data.css_animations['keyframes_count']
                    }
                }
            },
            "资源清单与待办事项": {
                "字体文件": list(set(self.desktop_data.resources['font_files'] + self.mobile_data.resources['font_files'])),
                "关键JS文件": self.desktop_data.resources['js_files'][:5],
                "第三方脚本": list(set(self.desktop_data.third_party_scripts + self.mobile_data.third_party_scripts)),
                "核心API端点": list(set(self.desktop_data.api_endpoints + self.mobile_data.api_endpoints))
            },
            "视觉确认": {
                "桌面截图": self.desktop_data.screenshot_path,
                "移动截图": self.mobile_data.screenshot_path,
                "提示": "请查看生成的截图文件进行视觉对比"
            }
        }
        
        # 保存报告
        report_filename = f"gofundme/reconnaissance_report_{timestamp}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📋 报告已保存: {report_filename}")
        
        # 打印关键信息
        self.print_summary_report(report)
        
        return report
    
    def print_summary_report(self, report):
        """打印摘要报告"""
        print("\n" + "="*80)
        print("🎯 GoFundMe侦察报告摘要")
        print("="*80)
        
        print(f"\n📊 总体评估:")
        print(f"   克隆难度: {report['总体评估']['克隆难度']}")
        print(f"   移动端适配: {report['总体评估']['移动端适配方案']}")
        
        print(f"\n📱 对比分析:")
        comparison = report['桌面vs移动对比分析']
        print(f"   CSS文件 - 桌面: {comparison['CSS文件数量']['桌面']}, 移动: {comparison['CSS文件数量']['移动']}")
        print(f"   JS文件 - 桌面: {comparison['JS文件数量']['桌面']}, 移动: {comparison['JS文件数量']['移动']}")
        print(f"   网络请求 - 桌面: {comparison['总网络请求数']['桌面']}, 移动: {comparison['总网络请求数']['移动']}")
        
        print(f"\n🎬 动画分析:")
        animation = report['交互与动画分析']['动画复杂度']
        print(f"   桌面动画: {animation['桌面']['动画数量']}个, 过渡: {animation['桌面']['过渡数量']}个")
        print(f"   移动动画: {animation['移动']['动画数量']}个, 过渡: {animation['移动']['过渡数量']}个")
        
        print(f"\n📁 资源统计:")
        resources = report['资源清单与待办事项']
        print(f"   字体文件: {len(resources['字体文件'])}个")
        print(f"   第三方脚本: {len(resources['第三方脚本'])}个")
        print(f"   API端点: {len(resources['核心API端点'])}个")
        
        print(f"\n🖼️ 视觉确认:")
        visual = report['视觉确认']
        print(f"   桌面截图: {visual['桌面截图']}")
        print(f"   移动截图: {visual['移动截图']}")
        print(f"   {visual['提示']}")
        
        print("\n" + "="*80)
    
    async def run_full_reconnaissance(self):
        """运行完整的双重模式侦察"""
        print("🚀 启动双重设备侦察模式...")
        
        async with async_playwright() as playwright:
            # 桌面模式侦察
            self.desktop_data = await self.reconnaissance_mode(playwright, 'desktop')
            
            # 桌面和移动模式之间增加更长的等待时间
            print("⏱️ 桌面侦察完成，等待10秒后进行移动侦察...")
            await asyncio.sleep(10)
            
            # 移动模式侦察
            self.mobile_data = await self.reconnaissance_mode(playwright, 'mobile')
            
            # 生成对比报告
            report = self.generate_comparison_report()
            
            print("🎉 双重设备侦察任务完成！")
            return report

async def main():
    """主函数 - GoFundMe深度侦察"""
    print("🎯 GoFundMe深度侦察脚本启动")
    print(f"🔗 目标URL: {TARGET_URL}")
    
    # 显示当前IP地址
    current_ip = check_local_ip()
    
    # 检查是否有命令行参数允许跳过Tor检查
    import sys
    allow_skip = '--skip-tor' in sys.argv or '--test' in sys.argv
    
    if allow_skip:
        print("⚠️ 检测到跳过Tor检查的参数")
    
    # Tor连接检查
    proxy_url = check_tor_connection(allow_skip=allow_skip)
    
    if proxy_url is None:
        print("\n❌ Tor连接检查失败！出于安全考虑，脚本终止执行。")
        print("请确保Tor正确配置并运行后重试。")
        print("\n💡 或者使用以下参数进行测试（不推荐）：")
        print("   python investigate_gofundme.py --skip-tor")
        print("   python investigate_gofundme.py --test")
        return
    
    if proxy_url == "skip":
        print("\n⚠️ 跳过Tor检查，使用直接连接...")
    else:
        print(f"\n✅ Tor连接验证通过: {proxy_url}")
    
    print("开始侦察任务...")
    
    # 创建输出目录
    Path("gofundme").mkdir(exist_ok=True)
    
    # 执行侦察，传入代理URL
    recon = PlaywrightRecon(proxy_url=proxy_url if proxy_url != "skip" else None)
    await recon.run_full_reconnaissance()

if __name__ == "__main__":
    asyncio.run(main())