# AI-Hackathon_2
source code for ollama-MCP-client
https://github.com/jonigl/mcp-client-for-ollama.git

# install below dependencies:
ollama pull qwen3.5:latest
(install python 3.13 as 3.14 may have some forward compatibility issues)
python -m pip install --upgrade pip
pip install bacnet-mcp
pip install -e mcp-client-for-ollama
or
pip install --upgrade ollmcp

# add installed folder to system/user path
example: C:\Users\ved\AppData\Roaming\Python\Python314\Scripts

# paste the code changes files at below location
C:\Users\ved\AppData\Roaming\Python\Python314\site-packages\bacnet_mcp

# run via:
# start the bacnet MCP server (example)
bacnet-mcp --host 127.0.0.1 --port 47808 --address 10.116.43.34/24   (this command will run only if above script path is added to user/sys variable)
npx @modelcontextprotocol/inspector (for debugging)
# add the server to ollmcp
ollmcp mcp add bacnet --transport http http://127.0.0.1:47808/mcp
# run the TUI client
ollmcp

# Optional: Streamlit UI
pip install streamlit
python -m streamlit run streamlit_app.py

# to add device-ip as name 
fill the devices.json

# to use the MCP server with Claude-Code paste the following JSON in config.json of claude-desktop/settings/devloper tools and then install these packages
pip install uv
uv tool install mcp-proxy

{  "mcpServers": {
   "bacnet": {
      "command": "mcp-proxy",
      "args": [
        "http://127.0.0.1:47808/mcp",
        "--transport=streamablehttp"
      ]
    }
  },
  "preferences": .......................
}
