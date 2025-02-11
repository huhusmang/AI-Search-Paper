# AI Search Papers 项目 📚

## 项目概述

AI Search Papers 项目旨在通过 LLM 的语义理解能力，帮助用户从指定范围的的学术论文数据库中（NDSS, CCS 等）快速筛选出符合要求的论文。项目利用语言模型评估论文与用户查询的相关性，并从论文标题和摘要中提取有意义的关键词。适合文献调研时，快速获取顶会中相关的论文列表。

## 功能特色

- **数据丰富**: 集成 DBLP 和 Semantic Scholar 数据，提供全面的学术论文信息。
- **自动爬取**: 一键获取并更新论文的摘要和其他关键信息，确保数据的完整性。
- **语义搜索**: 利用 LLM 技术进行高效的语义搜索，支持多种会议和年份的筛选。
- **关键词提取**: 自动从论文中提取关键词，辅助文献调研。
- **前端应用**: 提供用户友好的 Streamlit 界面，方便用户进行交互式搜索。

## 模块结构

### 1. 引擎模块（Engine Module）
- **位置**: `src/engine`
- **功能**: 从 DBLP 和 Semantic Scholar 等会议获取和处理学术论文信息。
- **主要文件**:
  - `dblp.py`: 从 DBLP 获取会议论文。
  - `sema.py`: 从 Semantic Scholar 获取会议论文。
  - `enrich.py`: 使用 Semantic Scholar 信息丰富 DBLP 数据。
  - `enrich_missing.py`: 更新丰富数据中缺失的摘要。
  - `stats.py`: 分析和总结数据，特别是关注摘要的可用性。
  - `spider`: 爬取会议论文的爬虫模块。

### 2. 搜索模块（AI Search Module）
- **位置**: `src/search`
- **功能**: 实现论文的语义搜索和关键词提取。
- **主要文件**:
  - `ai_query.py`: 使用 LLM 从论文列表中提取与用户查询相关的论文。
  - `label.py`: 使用 LLM 从论文中自动提取关键词。
  - `config.py`: 定义模型参数和 API 密钥的配置类。
  - `utils.py`: 提供与语言模型交互的实用函数。

## 安装与运行

### 环境要求
- Python 版本: >= 3.10

### 安装依赖
在项目根目录下运行以下命令安装所需依赖：

```bash
pip install -r requirements.txt
```

### 运行示例

1. **设置 API 密钥**: 确保在 `config.py` 中设置必要的 API 密钥。
2. **运行引擎模块**:
    ```bash
    # 获取 DBLP 数据
    python3 -m src.engine.dblp

    # 获取 Semantic Scholar 数据
    python3 -m src.engine.sema

    # 丰富 DBLP 数据
    python3 -m src.engine.enrich

    # 分析数据
    python3 -m src.engine.stats

    # 更新缺失摘要
    python3 -m src.engine.enrich_missing -c sp
    ```

3. **运行搜索模块**:
    ```bash
    # 关键词提取
    python3 -m src.label --conference sp --save-partial

    # 语义搜索
    python3 -m src.search.ai_query --query "Paper on the use of LLM-assisted static analysis to detect vulnerabilities in web applications" --conference sp --year 2015-2024 --save-partial
    ```

4. **前端应用**:
   - 运行 `app.py` 启动 Streamlit 应用:
     ```bash
     streamlit run app.py
     ```
   - 在浏览器中访问 `http://localhost:8501` 查看应用。

## TODO
- [ ] 通过向量相似度搜索降低搜索成本

## 贡献指南

欢迎对本项目进行贡献！请提交 PR 或报告问题。
