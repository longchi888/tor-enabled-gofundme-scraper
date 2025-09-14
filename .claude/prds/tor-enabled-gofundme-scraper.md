---
name: tor-enabled-gofundme-scraper
description: 基于Crawl4AI的安全匿名GoFundMe页面爬取系统，使用Tor网络保护隐私
status: backlog
created: 2025-09-14T22:09:20Z
---

# PRD: tor-enabled-gofundme-scraper

## Executive Summary

使用Crawl4AI框架重新开发现有的GoFundMe爬取脚本，实现与`scrape_gofundme_enhanced.py`完全相同的功能，同时保持Tor网络连接以确保最高级别的安全性和匿名性。该系统将利用Crawl4AI的先进爬取能力，同时保留现有脚本的所有安全特性。

## Problem Statement

**现状问题**：
- 现有的`scrape_gofundme_enhanced.py`脚本使用Playwright直接实现爬取逻辑
- 缺乏Crawl4AI框架的先进特性，如智能内容提取、自适应爬取等
- 代码复杂度高，维护困难

**为什么现在重要**：
- Crawl4AI提供更强大的LLM集成和内容提取能力
- 需要利用Crawl4AI的自适应爬取和智能分析功能
- 保持现有的安全性要求（Tor网络）的同时提升爬取效率

## User Stories

### 主要用户角色
- **安全研究人员**：需要匿名分析GoFundMe页面内容
- **数据分析师**：需要安全地收集筹款平台数据
- **开发者**：需要可靠的爬取工具进行研究

### 详细用户旅程

**研究人员使用场景**：
1. 启动脚本时自动检查网络安全状态
2. 系统强制要求使用Tor网络连接
3. 自动爬取桌面和移动端页面内容
4. 获得结构化的数据输出和完整的前端资源

**痛点解决**：
- 自动化的安全检查流程
- 完整的前端资源保存
- 动态内容的深度提取

## Requirements

### Functional Requirements

#### 核心爬取功能
1. **双端爬取模式**
   - 桌面端爬取（1920x1080分辨率）
   - 移动端爬取（iPhone 13 Pro模拟）
   - 平台间内容对比分析

2. **深度内容提取**
   - 等待动态内容完全加载（3分钟深度等待）
   - 激活交互元素触发懒加载内容
   - 专项处理三个关键区域：
     * 照片展示区域（"Show your support"）
     * 最近捐赠动态（"people just donated"）
     * 底部推荐筹款（"More ways to make a difference"）

3. **前端资源收集**
   - CSS文件提取和下载
   - JavaScript文件收集（过滤跟踪脚本）
   - 字体文件下载
   - 图片资源保存
   - SVG文件和Sprite收集
   - 媒体文件下载

4. **数据结构化输出**
   - 完整HTML保存（桌面/移动版本）
   - 动态内容摘要提取
   - JSON格式的元数据
   - 资源文件组织存储

#### Crawl4AI集成功能
1. **智能内容提取**
   - 使用Crawl4AI的LLM策略提取关键信息
   - 自动识别筹款项目的结构化数据
   - 智能文本内容清理和格式化

2. **自适应爬取策略**
   - 根据页面类型调整爬取参数
   - 智能重试机制
   - 内容变化检测

### Non-Functional Requirements

#### 安全性要求（最高优先级）
1. **强制Tor网络使用**
   - 脚本启动时检测Tor连接可用性
   - 自动发现Tor SOCKS端口（9150/9050）
   - 禁止在没有Tor保护的情况下运行

2. **网络安全监控**
   - 实时IP泄露检测
   - 真实IP与Tor IP对比验证
   - 检测到IP泄露时立即终止操作

3. **匿名性保护**
   - 随机User-Agent轮换
   - 反检测浏览器配置
   - 网络指纹伪装

#### 性能要求
- 支持断点续传下载
- 并发下载（最多3个线程）
- 磁盘空间检查（最少500MB）
- 智能重试机制（指数退避）

#### 可靠性要求
- 网络中断时自动恢复
- 下载进度持久化保存
- 详细的错误日志记录
- 失败任务报告生成

## Success Criteria

### 功能成功指标
- [ ] 100%保持现有脚本的所有功能
- [ ] 成功集成Crawl4AI框架
- [ ] Tor网络连接成功率 > 95%
- [ ] 动态内容提取完整性 > 90%

### 性能指标
- [ ] 页面加载时间 < 5分钟（包含深度等待）
- [ ] 资源下载成功率 > 85%
- [ ] 断点续传功能正常工作
- [ ] 内存使用量 < 2GB

### 安全指标
- [ ] 零IP泄露事件
- [ ] 所有网络请求通过Tor
- [ ] 实时监控功能正常运行

## Constraints & Assumptions

### 技术限制
- 必须基于现有的Crawl4AI框架
- 保持与`scrape_gofundme_enhanced.py`的功能一致性
- Windows平台兼容性要求

### 时间约束
- 必须保持现有的3分钟深度等待机制
- 不能显著增加总体爬取时间

### 资源限制
- 依赖Tor网络的可用性
- 需要足够的磁盘空间存储资源
- 网络带宽要求适中

### 假设条件
- 用户已安装Tor Browser或独立Tor服务
- 目标GoFundMe页面结构保持相对稳定
- Crawl4AI框架功能可靠

## Out of Scope

### 明确不包含的功能
- 不修改现有脚本的目标URL
- 不添加多站点爬取功能
- 不实现实时监控功能
- 不添加GUI界面
- 不支持代理轮换（仅Tor）

### 未来版本考虑
- 多个GoFundMe页面的批量处理
- 数据库存储集成
- Web界面开发
- API接口提供

## Dependencies

### 外部依赖
- **Crawl4AI框架**：核心爬取引擎
- **Tor网络服务**：端口9150或9050可用
- **Playwright**：浏览器自动化（Crawl4AI内置）

### 内部依赖
- 现有的目录结构：`gofundme/scraped_resources_ultra/`
- 配置文件：遵循CLAUDE.md中的项目规范
- 日志系统：与现有脚本兼容

### Python包依赖
```python
crawl4ai>=0.3.0
asyncio
json
pathlib
hashlib
aiofiles
```

### 系统依赖
- Windows/Linux/macOS兼容性
- Python 3.8+
- 最少2GB RAM
- 500MB可用磁盘空间

## Implementation Plan

### 开发阶段
1. **需求分析阶段**（1-2天）
   - 深入分析现有脚本功能
   - 制定Crawl4AI集成策略
   - 确定接口设计

2. **核心开发阶段**（3-5天）
   - 实现Tor网络集成
   - 开发双端爬取功能
   - 集成Crawl4AI提取策略

3. **测试验证阶段**（2-3天）
   - 功能对比测试
   - 安全性验证
   - 性能基准测试

### 验收标准
- 所有现有功能正常工作
- Tor网络安全检查通过
- 输出格式与现有脚本一致
- 代码质量符合项目标准