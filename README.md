# MLX TTS API

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

OpenAI-compatible TTS service based on [mlx-audio](https://github.com/Blaizzy/mlx-audio), optimized for Apple Silicon.

### Features

- OpenAI TTS API compatible (`/v1/audio/speech`)
- Multiple API keys support
- Concurrent request control
- Multiple audio formats (mp3, wav, opus, flac, aac, pcm)
- JSON response with character-level alignment (using Whisper)
- Multi-language support (English, Chinese, Japanese)

### Requirements

- macOS with Apple Silicon (M1/M2/M3)
- Python 3.10+
- espeak-ng (`brew install espeak-ng`)

### Installation

```bash
# Clone the repository
git clone https://github.com/user/mobai-tts.git
cd mobai-tts

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy config file
cp .env.example .env
```

### Configuration

Edit `.env` file:

```bash
# Server
HOST=0.0.0.0
PORT=8000

# API Keys (comma-separated, leave empty to disable auth)
API_KEYS=sk-key1,sk-key2

# Concurrency
MAX_WORKERS=4

# MLX-Audio
MLX_MODEL=prince-canuma/Kokoro-82M
DEFAULT_VOICE=af_heart
DEFAULT_LANG=a
DEFAULT_SAMPLE_RATE=24000

# Whisper alignment (for JSON response)
WHISPER_MODEL=tiny
```

### Running

```bash
# Foreground
python main.py

# Background
./start.sh

# Stop
./stop.sh
```

API docs available at http://localhost:8000/docs

### API Usage

#### Generate Speech (Audio)

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer sk-key1" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"Hello world","voice":"alloy"}' \
  --output speech.mp3
```

#### Generate Speech (JSON with alignment)

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer sk-key1" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"Hello world","voice":"alloy","response_format":"json"}'
```

Response:
```json
{
  "audio_base64": "//uQxAAA...",
  "alignment": {
    "characters": ["H", "e", "l", "l", "o"],
    "characterStartTimesSeconds": [0.0, 0.1, 0.2, 0.3, 0.4],
    "characterEndTimesSeconds": [0.1, 0.2, 0.3, 0.4, 0.5]
  }
}
```

#### Python Client

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-key1",
    base_url="http://localhost:8000/v1"
)

response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hello, world!"
)

response.stream_to_file("speech.mp3")
```

### Voice Options

| Voice   | Description      |
|---------|------------------|
| alloy   | American Female  |
| echo    | American Male    |
| fable   | British Female   |
| onyx    | British Male     |
| nova    | American Female  |
| shimmer | American Female  |

### Language Support

| Code | Language         | Extra Dependencies       |
|------|------------------|--------------------------|
| a    | American English | None                     |
| b    | British English  | None                     |
| z    | Chinese          | `pip install misaki[zh]` |
| j    | Japanese         | `pip install misaki[ja]` |

---

<a name="中文"></a>
## 中文

基于 [mlx-audio](https://github.com/Blaizzy/mlx-audio) 的 OpenAI 兼容 TTS 服务，专为 Apple Silicon 优化。

### 功能特性

- 兼容 OpenAI TTS API (`/v1/audio/speech`)
- 支持多个 API Key
- 并发请求控制
- 多种音频格式 (mp3, wav, opus, flac, aac, pcm)
- JSON 响应带字符级时间对齐（使用 Whisper）
- 多语言支持（英语、中文、日语）

### 系统要求

- macOS Apple Silicon (M1/M2/M3)
- Python 3.10+
- espeak-ng (`brew install espeak-ng`)

### 安装

```bash
# 克隆仓库
git clone https://github.com/user/mobai-tts.git
cd mobai-tts

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env
```

### 配置

编辑 `.env` 文件：

```bash
# 服务配置
HOST=0.0.0.0
PORT=8000

# API Keys（逗号分隔，留空则不验证）
API_KEYS=sk-key1,sk-key2

# 并发配置
MAX_WORKERS=4

# MLX-Audio 配置
MLX_MODEL=prince-canuma/Kokoro-82M
DEFAULT_VOICE=af_heart
DEFAULT_LANG=a
DEFAULT_SAMPLE_RATE=24000

# Whisper 对齐配置（用于 JSON 响应）
WHISPER_MODEL=tiny
```

### 运行

```bash
# 前台运行
python main.py

# 后台运行
./start.sh

# 停止服务
./stop.sh
```

启动后访问 http://localhost:8000/docs 查看 API 文档。

### API 使用

#### 生成语音（音频）

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer sk-key1" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"你好世界","voice":"alloy"}' \
  --output speech.mp3
```

#### 生成语音（JSON 带对齐）

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer sk-key1" \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","input":"你好世界","voice":"alloy","response_format":"json"}'
```

响应：
```json
{
  "audio_base64": "//uQxAAA...",
  "alignment": {
    "characters": ["你", "好", "世", "界"],
    "characterStartTimesSeconds": [0.0, 0.24, 0.48, 0.72],
    "characterEndTimesSeconds": [0.24, 0.48, 0.72, 0.96]
  }
}
```

#### Python 客户端

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-key1",
    base_url="http://localhost:8000/v1"
)

response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="你好，世界！"
)

response.stream_to_file("speech.mp3")
```

### 声音选项

| 声音    | 描述       |
|---------|-----------|
| alloy   | 美式女声   |
| echo    | 美式男声   |
| fable   | 英式女声   |
| onyx    | 英式男声   |
| nova    | 美式女声   |
| shimmer | 美式女声   |

### 语言支持

| 代码 | 语言     | 额外依赖                 |
|------|---------|--------------------------|
| a    | 美式英语 | 无                       |
| b    | 英式英语 | 无                       |
| z    | 中文     | `pip install misaki[zh]` |
| j    | 日语     | `pip install misaki[ja]` |

### 日志

日志文件位于 `logs/tts-YYYYMMDD.log`
