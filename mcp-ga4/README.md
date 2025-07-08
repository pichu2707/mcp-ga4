# MCP GA4 Server

An MCP (Model Context Protocol) server for Google Analytics 4 (GA4), enabling LLMs and clients to interact with GA4 data via the MCP standard. This project is designed for use with [Claude Desktop](https://github.com/Bartender-bit/Remote-MCP-Server-for-Claude-Desktop), [Cursor](https://www.cursor.so/), and other MCP-compatible clients.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
  - [Locally (Python)](#locally-python)
  - [With Docker](#with-docker)
- [Transports](#transports)
- [Configuration](#configuration)
  - [Google Credentials](#google-credentials)
  - [Environment Variables](#environment-variables)
- [Integration Examples](#integration-examples)
  - [Cursor](#cursor)
  - [Claude Desktop](#claude-desktop)
- [Contributing](#contributing)
- [License](#license)
- [References](#references)

---

## Features

- Exposes GA4 data and reporting via the Model Context Protocol (MCP)
- Multiple transport options: stdio, HTTP, streamable HTTP (SSE)
- Docker and docker-compose support for easy deployment
- Ready for integration with Claude Desktop and Cursor

## Requirements

- Python 3.12+ (or Docker)
- [uv](https://www.pythonuv.com/) (for local development)
- Google Cloud service account credentials with GA4 Data API and GA4 Admin access

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/mcp-ga4.git
   cd mcp-ga4
   ```

2. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Set up Google credentials:**
   - Download your service account JSON from Google Cloud Console.
   - Place it in the project root as `google-credentials.json`.

## Running the Server

### Locally (Python)

From the `mcp-ga4` directory:

```bash
uv run -m mcp_ga4.server
```

Or, from the root:

```bash
uv run mcp dev src/mcp_ga4/server.py
```

To test and debug with the MCP inspector, you can run:

   ```bash
   uv run mcp dev src/mcp_ga4/server.py
   ```


### With Docker

#### Build and run with Docker Compose

1. **Build and start the container:**
   ```bash
   docker-compose up --build
   ```

2. **Environment variables** (see below) can be set in the `docker-compose.yml` or via `.env`.

#### Standalone Docker

If you want to use the provided Dockerfile directly:

```bash
docker build -t mcp-ga4 .
docker run -it --rm \
  -v $(pwd)/google-credentials.json:/app/google-credentials.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials.json \
  -e MCP_TRANSPORT=streamable-http \
  -p 8000:8000 \
  mcp-ga4
```

## Transports

The server supports multiple MCP transport mechanisms:

- **stdio**: For direct integration with LLM clients (e.g., Claude Desktop, Cursor)
- **streamable-http**: For HTTP/SSE-based communication (default for Docker)
- **http**: Standard HTTP (if supported)
- **sse**: Decrecated

Set the transport via the `MCP_TRANSPORT` environment variable:

| Transport         | Value             | Use Case                        |
|-------------------|------------------|---------------------------------|
| Standard IO       | `stdio`          | Claude Desktop, Cursor          |
| Streamable HTTP   | `streamable-http`| Web clients, remote LLMs        |
| SSE               | `sse`            | (If implemented)                |

## Configuration

### Google Credentials

- Place your Google service account JSON as `google-credentials.json` in the project root.
- Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to its path.

### Environment Variables

| Variable                        | Description                                 | Example Value           |
|----------------------------------|---------------------------------------------|------------------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to your Google credentials JSON        | `./google-credentials.json` |
| `MCP_TRANSPORT`                  | Transport type (`stdio`, `streamable-http`) | `stdio`                |
| `MCP_LOG_LEVEL`                  | Logging level (`DEBUG`, `INFO`, etc.)       | `DEBUG`                |
| `MCP_PORT`                       | Port for HTTP/SSE server                    | `8000`                 |
| `PYTHONPATH`                     | Python path for module resolution           | `./mcp-ga4/src`        |

## Integration Examples

### Cursor

To use the server with Cursor, add the following to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ga4-local-stdio": {
      "command": "uv",
      "args": [
        "run",
        "-m",
        "mcp_ga4.server"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "./google-credentials.json",
        "MCP_TRANSPORT": "stdio",
        "PYTHONPATH": "${workspaceFolder}/mcp-ga4/src",
        "MCP_LOG_LEVEL": "DEBUG",
        "UV_PYTHON": "3.12"
      },
      "cwd": "${workspaceFolder}/mcp-ga4"
    }
  }
}
```

### Claude Desktop

1. Open your Claude Desktop config at:
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```
2. Add your MCP server under `mcpServers`:

```json
{
    "mcpServers": {
        "ga4-local-stdio": {
            "command": "uv",
      "args": [
          "run",
        "-m",
        "mcp_ga4.server"
      ],
      "env": {
          "GOOGLE_APPLICATION_CREDENTIALS": "/ABSOLUTE/PATH/TO/google-credentials.json",
        "MCP_TRANSPORT": "stdio",
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/mcp-ga4/src",
        "MCP_LOG_LEVEL": "DEBUG",
        "UV_PYTHON": "3.12"
      },
      "cwd": "/ABSOLUTE/PATH/TO/mcp-ga4"
    }
  }
}
```
3. Save and restart Claude Desktop.

For more details, see the [Claude Desktop Remote MCP Server Guide](https://github.com/Bartender-bit/Remote-MCP-Server-for-Claude-Desktop).

### Cursor Remote Streamable-HTTP

```json
    "mcp-ga4-http": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp",
      "note": "For HTTP-SSE connections, add this URL directly in Client"
    }
```

### Claude Desktop Remote Streamable-HTTP

```json
    "mcp-ga4-http": {
      "command": "npx",
      "args": ["mcp-remote", "http://127.0.0.1:8000/mcp"]
    }
```


## Contributing

Pull requests are welcome! Please open an issue to discuss major changes.

## License

[MIT](LICENSE)

## References

- [Model Context Protocol (MCP) Introduction](https://modelcontextprotocol.io/introduction)
- [How to Write a Good README](https://www.freecodecamp.org/news/how-to-write-a-good-readme-file/)
- [Make a README](https://www.makeareadme.com/)
- [Claude Desktop Remote MCP Server](https://github.com/Bartender-bit/Remote-MCP-Server-for-Claude-Desktop)

---

Feel free to further customize the README for your organization or add more usage examples as your project evolves.