# MLX TTS API

基于 [mlx-audio](https://github.com/Blaizzy/mlx-audio) 的 OpenAI 兼容 TTS 服务，专为 Apple Silicon 优化。

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env
```

## 配置

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
```

## 运行

```bash
python main.py
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

## API 使用

### 生成语音

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer sk-key1" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello, world!",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

### Python 客户端

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

## 声音选项

| Voice   | 描述       |
|---------|-----------|
| alloy   | 美式女声   |
| echo    | 美式男声   |
| fable   | 英式女声   |
| onyx    | 英式男声   |
| nova    | 美式女声   |
| shimmer | 美式女声   |

## 输出格式

支持：`mp3`, `wav`, `opus`, `flac`, `aac`, `pcm`

## 语言支持

修改 `DEFAULT_LANG` 配置：

| 代码 | 语言     | 额外依赖              |
|------|---------|----------------------|
| a    | 美式英语 | 无                   |
| b    | 英式英语 | 无                   |
| z    | 中文     | `pip install misaki[zh]` |
| j    | 日语     | `pip install misaki[ja]` |
