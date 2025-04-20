# PDF Processing System

一个强大的PDF处理系统，可以将PDF文件转换为Markdown格式，建立向量数据库，并使用大型语言模型（LLM）生成综合摘要。

## 功能特点

- 将PDF文件转换为Markdown格式，保留文本格式和图像
- 使用向量数据库存储和检索文档内容
- 利用大型语言模型（如OpenAI、Grok AI）生成文档摘要
- 支持生成英文和中文摘要
- 运行时间管理，每15秒更新一次进度
- 错误日志记录，只在出错时输出日志

## 目录结构

```
.
├── config.py              # 配置文件
├── convert_pdfs.py        # PDF转换为Markdown的脚本
├── input/                 # 输入PDF文件目录
├── logs/                  # 错误日志目录
├── main.py                # 主程序
├── output/                # 输出目录
│   ├── markdown/          # 转换后的Markdown文件
│   │   └── images/        # 提取的图像
│   ├── summary.md         # 生成的英文摘要
│   ├── summary_chinese.md # 生成的中文摘要
│   └── vectordb/          # 向量数据库
├── process_documents.py   # 文档处理和摘要生成
├── setup_vectordb.py      # 向量数据库设置
└── timer.py               # 运行时间管理
```

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/pdf-processing-system.git
cd pdf-processing-system
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 创建 `.env` 文件并添加API密钥：

```
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1  # 可选
GROK_API_KEY=your_grok_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  # 可选
```

## 使用方法

1. 将PDF文件放入 `input/` 目录

2. 运行程序：

```bash
# 运行所有步骤
python main.py --all

# 或者单独运行各个步骤
python main.py --convert     # 仅转换PDF为Markdown
python main.py --setup-db    # 仅设置向量数据库
python main.py --process     # 仅处理文档并生成摘要
python main.py --config      # 显示配置信息
```

3. 查看生成的摘要：
   - 英文摘要：`output/summary.md`
   - 中文摘要：`output/summary_chinese.md`

## 配置

在 `config.py` 文件中可以修改以下配置：

- 模型选择：OpenAI、Grok AI、Anthropic
- 温度参数：控制输出的随机性（0.0-1.0）
- 向量数据库设置：块大小、重叠大小等

## 运行时间管理

系统内置了运行时间管理功能，每15秒更新一次进度，帮助监控长时间运行的任务。可以使用 `--no-timer` 选项禁用此功能：

```bash
python main.py --all --no-timer
```

## 错误日志

系统只在出错时记录日志，日志文件保存在 `logs/error.log`。正常运行时不会产生日志输出。

## 依赖项

- langchain：基础LangChain框架
- langchain-core：核心组件
- langchain-openai：OpenAI集成
- langchain-anthropic：Anthropic Claude集成
- langchain-groq：Groq集成（用于Grok AI）
- langchain-community：社区扩展
- langchain-chroma：ChromaDB集成
- langgraph：构建LangChain图
- chromadb：向量数据库
- python-dotenv：环境变量管理
- pydantic：数据验证
- PyMuPDF (fitz)：PDF处理
- fastembed：嵌入生成

## 许可证

[MIT](LICENSE)
