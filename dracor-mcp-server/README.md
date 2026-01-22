# DraCor MCP Server (HTTP Streaming)

A Model Context Protocol (MCP) server for interacting with the Drama Corpora Project (DraCor) API v1. This version supports HTTP streaming transport for cloud deployment on Railway.com.

## Features

- **Resources**: Access corpora, plays, characters, text, and network data via URI-based resources
- **Tools**: Search plays, compare plays, analyze character relations, analyze play structure, and more
- **Prompts**: Pre-built analysis templates for plays, characters, networks, gender analysis, and historical context
- **Dual Transport**: Supports both stdio (for Claude Desktop) and streamable-http (for cloud deployment)

## Quick Start

### Local Development (stdio mode)

```bash
# Install dependencies
pip install -e .

# Run in stdio mode (default)
python main.py
```

### Local HTTP Testing

```bash
# Run in HTTP mode
TRANSPORT=streamable-http python main.py

# Test health endpoint
curl http://localhost:8000/health

# Test with MCP Inspector
npx -y @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Railway Deployment

### Prerequisites

1. A [Railway](https://railway.com) account
2. This repository connected to Railway

### Deployment Steps

1. **Create a new project** on Railway
2. **Connect your GitHub repository**
3. **Set the root directory** to `dracor-mcp-server`
4. **Configure environment variables**:
   - `TRANSPORT`: `streamable-http`
   - `DRACOR_API_BASE_URL`: `https://dracor.org/api/v1` (optional, this is the default)

Railway will automatically:
- Detect the Python project from `pyproject.toml`
- Build using Nixpacks
- Use the configuration from `railway.json`
- Set the `PORT` environment variable

### Railway Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSPORT` | `stdio` | Set to `streamable-http` for Railway |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port (Railway sets automatically) |
| `DRACOR_API_BASE_URL` | `https://dracor.org/api/v1` | DraCor API endpoint |
| `LOG_LEVEL` | `info` | Logging level |

## HTTP Endpoints

When running in HTTP mode, the following endpoints are available:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp` | POST | MCP requests (streamable HTTP) |
| `/sse` | GET | Server-Sent Events stream |
| `/health` | GET | Health check for Railway |

## MCP Client Configuration

### Claude Desktop (stdio mode)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dracor": {
      "command": "python",
      "args": ["/path/to/dracor-mcp-server/main.py"],
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

### HTTP Mode (Remote)

For clients that support HTTP MCP connections, use:

```
https://your-railway-url.railway.app/mcp
```

## Available Tools

| Tool | Description |
|------|-------------|
| `search_plays` | Search for plays with multiple filters |
| `compare_plays` | Compare two plays by metrics |
| `analyze_character_relations` | Analyze character relationships |
| `analyze_play_structure` | Analyze play structure (acts, scenes) |
| `find_character_across_plays` | Find a character across all plays |
| `analyze_full_text` | Full text analysis including TEI |

## Available Resources

| Resource URI | Description |
|--------------|-------------|
| `info://` | API information |
| `corpora://` | List all corpora |
| `corpus://{corpus_name}` | Corpus details |
| `plays://{corpus_name}` | List plays in corpus |
| `play://{corpus_name}/{play_name}` | Play details |
| `characters://{corpus_name}/{play_name}` | Character list |
| `network_data://{corpus_name}/{play_name}` | Network data (CSV) |
| `tei_text://{corpus_name}/{play_name}` | Full TEI XML |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
