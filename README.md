# AI-Hackathon_2
source code for ollama-MCP-client
https://github.com/jonigl/mcp-client-for-ollama.git

install below dependencies:
ollama pull qwen3.5:latest
(install python 3.13 as 3.14 may have some forward compatibility issues)
python -m pip install --upgrade pip
pip install bacnet-mcp
-----add installed folder to system/user path----
example: C:\Users\ved\AppData\Roaming\Python\Python314\Scripts
-------
run via:
bacnet-mcp --host 0.0.0.0 --port 47808 --address 10.183.155.34/24   (this command will run only if above script path is added to user/sys variable)
npx @modelcontextprotocol/inspector (for debugging)
ollmcp -m qwen3.5 -u http://127.0.0.1:8000/mcp
