---
name: tor-enabled-gofundme-scraper
status: backlog
created: 2025-09-14T22:12:11Z
progress: 0%
prd: .claude/prds/tor-enabled-gofundme-scraper.md
github: [Will be updated when synced to GitHub]
---

# Epic: tor-enabled-gofundme-scraper

## Overview

重构现有的GoFundMe爬取脚本，从基于Playwright的实现迁移到Crawl4AI框架，同时保持所有现有的安全特性和功能。重点是利用Crawl4AI的先进功能简化代码复杂度，同时确保Tor网络强制连接和完整的匿名性保护。

## Architecture Decisions

### 核心架构选择
- **Crawl4AI AsyncWebCrawler**: 替换直接的Playwright实现，利用其内置的浏览器管理和智能提取功能
- **策略模式集成**: 使用Crawl4AI的ContentStrategy和ExtractionStrategy实现智能内容处理
- **安全层保持**: 将现有的NetworkSecurity类重构为Crawl4AI的代理配置层
- **配置驱动**: 使用BrowserConfig、CrawlerRunConfig和LLMConfig统一管理所有配置

### 技术决策理由
1. **保留安全检查逻辑**: 现有的Tor检测和IP监控逻辑已经非常完善，直接迁移到新架构
2. **简化资源收集**: 利用Crawl4AI的内置资源提取能力，大幅简化当前的手动DOM操作
3. **智能内容提取**: 使用LLM策略自动识别和提取GoFundMe的关键信息结构

## Technical Approach

### 核心组件重构
#### 1. 安全网络层 (`TorSecurityManager`)
- 继承现有NetworkSecurity的所有功能
- 与Crawl4AI的BrowserConfig集成，确保所有请求通过Tor代理
- 提供实时监控和自动终止机制

#### 2. Crawl4AI配置层 (`GoFundMeScraperConfig`)
```python
# 核心配置类整合
- BrowserConfig: Tor代理 + 反检测设置
- CrawlerRunConfig: 双端模式 + 深度等待策略
- LLMConfig: 智能内容提取配置
```

#### 3. 双端爬取引擎 (`DualModeCollector`)
- 使用AsyncWebCrawler的设备模拟功能
- 桌面/移动端配置自动切换
- 保持现有的3分钟深度等待和交互激活逻辑

#### 4. 智能内容提取 (`GoFundMeExtractor`)
- 基于Crawl4AI的ExtractionStrategy
- 自动识别三个关键区域的内容
- LLM辅助的结构化数据提取

### 数据流设计
```
URL → TorSecurityManager → Crawl4AI AsyncWebCrawler →
智能提取策略 → 结构化输出 → 资源下载管理
```

### 文件结构保持
- 完全兼容现有的`gofundme/scraped_resources_ultra/`目录结构
- 保持桌面/移动端分离的输出格式
- 维持JSON元数据和HTML保存的一致性

## Implementation Strategy

### 开发阶段
1. **配置层迁移** (1天)
   - 将现有配置映射到Crawl4AI配置类
   - 测试Tor代理集成的兼容性

2. **核心功能重写** (2-3天)
   - 实现双端爬取引擎
   - 集成智能内容提取策略
   - 保持深度等待和交互激活逻辑

3. **验证和优化** (1-2天)
   - 功能对比测试确保一致性
   - 性能调优和错误处理完善

### 风险缓解
- **功能降级风险**: 逐步迁移，保持现有脚本作为备份参考
- **安全性风险**: 优先实现和测试Tor集成，确保无IP泄露
- **性能风险**: 基准测试确保不降低爬取效率

## Task Breakdown Preview

高级任务分类（共8个核心任务）:
- [ ] **安全层集成**: 将NetworkSecurity迁移到Crawl4AI代理配置
- [ ] **配置系统重构**: 实现GoFundMeScraperConfig统一配置管理
- [ ] **双端爬取引擎**: 基于AsyncWebCrawler的桌面/移动模式实现
- [ ] **深度内容提取**: 保持3分钟等待和交互激活的Crawl4AI策略版本
- [ ] **智能数据提取**: LLM策略实现关键区域的结构化提取
- [ ] **资源收集重构**: 利用Crawl4AI内置功能简化资源下载逻辑
- [ ] **输出格式兼容**: 确保JSON/HTML输出与现有脚本完全一致
- [ ] **集成测试验证**: 全功能对比测试和安全性验证

## Dependencies

### 外部依赖
- **Crawl4AI框架**: 版本>=0.3.0，核心爬取引擎
- **Tor网络服务**: 端口9150/9050，必须可用
- **现有脚本**: `scrape_gofundme_enhanced.py`作为功能参考基准

### 内部依赖
- **目录结构**: 必须兼容`gofundme/scraped_resources_ultra/`
- **配置系统**: 遵循CLAUDE.md项目规范
- **安全检查**: 复用现有IP监控和验证逻辑

### 技术栈整合
```python
crawl4ai>=0.3.0          # 核心框架
asyncio                  # 异步支持
aiofiles                 # 异步文件操作
pathlib                  # 路径管理
hashlib                  # 文件命名
```

## Success Criteria (Technical)

### 功能对等性
- [ ] 100%功能对等: 所有现有脚本功能在新实现中正常工作
- [ ] 输出一致性: JSON元数据和HTML文件格式完全匹配
- [ ] 安全等级维持: Tor强制连接和IP监控功能无降级

### 性能基准
- [ ] 爬取时间: ≤ 5分钟 (包含3分钟深度等待)
- [ ] 内存使用: ≤ 2GB 峰值内存占用
- [ ] 成功率: ≥ 95% Tor连接成功率, ≥ 85% 资源下载成功率

### 代码质量
- [ ] 复杂度降低: 相比现有脚本减少30%以上代码量
- [ ] 维护性提升: 清晰的模块分离和配置管理
- [ ] 错误处理: 完善的异常捕获和恢复机制

## Estimated Effort

### 时间线评估
- **总开发时间**: 4-6天
- **关键路径**: 安全层集成 → 双端爬取 → 内容提取 → 验证测试
- **并行任务**: 配置重构可与核心功能开发同步进行

### 资源需求
- **开发人员**: 1名熟悉Crawl4AI和网络安全的开发者
- **测试环境**: 需要Tor网络环境用于安全性验证
- **参考资料**: 现有脚本作为功能基准和回归测试标准

### 风险缓冲
- **技术风险**: 预留1-2天处理Crawl4AI集成的未预期问题
- **兼容性风险**: 预留1天进行输出格式的精确匹配调试

## Tasks Created
- [ ] 001.md - 安全层集成 - 将NetworkSecurity迁移到Crawl4AI代理配置 (parallel: true)
- [ ] 002.md - 配置系统重构 - 实现GoFundMeScraperConfig统一配置管理 (parallel: true)
- [ ] 003.md - 双端爬取引擎 - 基于AsyncWebCrawler的桌面/移动模式实现 (parallel: false)
- [ ] 004.md - 深度内容提取 - 保持3分钟等待和交互激活的Crawl4AI策略版本 (parallel: false)
- [ ] 005.md - 智能数据提取 - LLM策略实现关键区域的结构化提取 (parallel: true)
- [ ] 006.md - 资源收集重构 - 利用Crawl4AI内置功能简化资源下载逻辑 (parallel: true)
- [ ] 007.md - 输出格式兼容 - 确保JSON/HTML输出与现有脚本完全一致 (parallel: false)
- [ ] 008.md - 集成测试验证 - 全功能对比测试和安全性验证 (parallel: false)

Total tasks: 8
Parallel tasks: 4 (001, 002, 005, 006)
Sequential tasks: 4 (003, 004, 007, 008)
Estimated total effort: 26-32 hours (4-6天)