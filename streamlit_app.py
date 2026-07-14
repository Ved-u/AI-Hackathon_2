import asyncio
import concurrent.futures
import io
import json
import re
import sys
import threading
from pathlib import Path
import streamlit as st
from mcp_client_for_ollama.client import MCPClient
from rich.console import Console

DEFAULT_CONFIG = Path("bacnet-server.json")

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

def strip_ansi_codes(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def load_default_server_url():
    if DEFAULT_CONFIG.exists():
        try:
            data = json.loads(DEFAULT_CONFIG.read_text())
            servers = data.get("mcpServers", {})
            # Pick first server url if present
            for entry in servers.values():
                url = entry.get("url")
                if url:
                    return url
        except Exception:
            return ""
    return ""

def get_client():
    # Create threaded MCP client with optional desired model from session_state
    desired_model = st.session_state.get("desired_model")
    if "mcp_client" not in st.session_state:
        st.session_state.mcp_client = ThreadedMCPClient(model=desired_model)
    else:
        client = st.session_state.mcp_client
        if desired_model and desired_model != client.model:
            client.stop()
            st.session_state.mcp_client = ThreadedMCPClient(model=desired_model)

    return st.session_state.mcp_client

class DualWriter:
    """Write text to both the terminal and a secondary in-memory buffer."""

    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary

    def write(self, text):
        self.primary.write(text)
        self.primary.flush()
        self.secondary.write(text)

    def flush(self):
        try:
            self.primary.flush()
        except Exception:
            pass
        self.secondary.flush()

    def isatty(self):
        return getattr(self.primary, "isatty", lambda: False)()

    @property
    def encoding(self):
        return getattr(self.primary, "encoding", "utf-8")

    def __getattr__(self, name):
        return getattr(self.primary, name)


class ThreadedMCPClient:
    """A wrapper that keeps MCPClient and its async lifecycle inside a dedicated thread."""

    def __init__(self, model: str | None = None):
        self.model = model
        self.stdout_buffer = io.StringIO()
        self.console_file = DualWriter(sys.stdout, self.stdout_buffer)
        self.console = Console(file=self.console_file, force_terminal=True, markup=True)
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_ready = threading.Event()
        self.client_ready = threading.Event()
        self._stop_event = threading.Event()
        self._task_lock = threading.Lock()
        self._buffer_lock = threading.Lock()
        self.thread.start()
        self.loop_ready.wait()
        self.client_ready.wait()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop_ready.set()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = self.console_file
        sys.stderr = self.console_file
        try:
            self.client = MCPClient(model=self.model) if self.model else MCPClient()
            # Override the internally created console if possible
            try:
                self.client.console = self.console
                self.client.server_connector.console = self.console
                self.client.model_manager.console = self.console
                self.client.model_config_manager.console = self.console
                self.client.prompt_manager.console = self.console
                self.client.resource_manager.console = self.console
                self.client.resource_handler.console = self.console
                self.client.streaming_manager.console = self.console
                self.client.tool_display_manager.console = self.console
                self.client.hil_manager.console = self.console
            except Exception:
                pass
            self.client_ready.set()
            self.loop.run_until_complete(self._worker())
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def clear_console_buffer(self):
        with self._buffer_lock:
            self.stdout_buffer.truncate(0)
            self.stdout_buffer.seek(0)

    def get_console_buffer(self) -> str:
        with self._buffer_lock:
            return self.stdout_buffer.getvalue()

    async def _worker(self):
        while not self._stop_event.is_set():
            await asyncio.sleep(0.1)

    def _run_coroutine(self, coro):
        future = concurrent.futures.Future()

        def _done_callback(task):
            try:
                result = task.result()
            except Exception as exc:
                future.set_exception(exc)
            else:
                future.set_result(result)

        async def _wrapper():
            task = self.loop.create_task(coro)
            task.add_done_callback(_done_callback)
            return await task

        with self._task_lock:
            self.loop.call_soon_threadsafe(asyncio.create_task, _wrapper())
            return future.result()

    def connect_to_server(self, url: str):
        return self._run_coroutine(self.client.connect_to_servers(server_urls=[url]))

    def process_query(self, query: str) -> tuple[str, str]:
        self.clear_console_buffer()
        result = self._run_coroutine(self.client.process_query(query))
        self.console_file.flush()
        return result, self.get_console_buffer()

    def stop(self):
        self._stop_event.set()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=3)


def connect_to_server(client: ThreadedMCPClient, url: str):
    return client.connect_to_server(url)


def process_query(client: ThreadedMCPClient, query: str) -> tuple[str, str]:
    return client.process_query(query)

def main():
    st.set_page_config(page_title="ollmcp Chat UI", layout="wide")
    st.title("ollmcp — Streamlit Chat UI")

    # Sidebar: server URL and model selection
    default_url = load_default_server_url()
    default_model = "qwen3.5:latest"
    with st.sidebar.form("connect"):
        st.write("Connect to MCP server")
        server_url = st.text_input("MCP server URL (streamable HTTP or SSE)", value=default_url)
        model_choice = st.text_input(
            "Ollama model (e.g. qwen3.5:latest)",
            value=st.session_state.get("desired_model") or default_model
        )
        connect = st.form_submit_button("Connect")

    # Create or update client based on selected model
    desired_model = model_choice.strip() or None
    if desired_model:
        st.session_state.desired_model = desired_model

    client = get_client()

    if connect and server_url:
        with st.spinner("Connecting to server..."):
            try:
                connect_to_server(client, server_url)
                st.success("Connected — tools and prompts loaded")
            except Exception as e:
                st.error(f"Failed to connect: {e}")

    # Chat area
    if "history" not in st.session_state:
        st.session_state.history = []
    if "logs" not in st.session_state:
        st.session_state.logs = []

    query = st.text_input("Your message", key="chat_input")
    if st.button("Send") and query:
        with st.spinner("Processing..."):
            import contextlib

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            response = None
            out_logs = ""
            err_logs = ""
            try:
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                    response, console_logs = process_query(client, query)
            except Exception as e:
                response = f"(exception) {type(e).__name__}: {e}"
                console_logs = ""
            finally:
                out_logs = stdout_buf.getvalue()
                err_logs = stderr_buf.getvalue()

        # Capture debug logs separately from the model response.
        console_logs = strip_ansi_codes(console_logs or "").strip()
        out_logs = strip_ansi_codes(out_logs or "").strip()
        err_logs = strip_ansi_codes(err_logs or "").strip()

        st.session_state.history.append((query, response))
        st.session_state.logs.append({
            "query": query,
            "console": console_logs,
            "stdout": out_logs,
            "stderr": err_logs,
        })
        # `st.experimental_rerun()` may be unavailable in some Streamlit versions.
        # Clear the input field instead and let Streamlit rerun naturally on next interaction.
        try:
            rerun = getattr(st, "experimental_rerun")
        except Exception:
            rerun = None

        if callable(rerun):
            rerun()
        else:
            # No safe rerun available for this Streamlit version; do nothing.
            # Leaving the input value as-is avoids Streamlit session_state assignment errors.
            pass

    # Display chat history
    for q, a in reversed(st.session_state.history):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**Assistant:**\n\n{a}")

    # Display logs in a separate panel for debug visibility
    with st.expander("Model and transport logs", expanded=True):
        st.markdown(f"**Captured log entries:** {len(st.session_state.logs)}")
        if st.session_state.logs:
            for entry in reversed(st.session_state.logs):
                st.markdown(f"**Query:** {entry['query']}")
                if entry["console"]:
                    st.markdown("**Console:**")
                    st.text(entry["console"])
                if entry["stdout"]:
                    st.markdown("**STDOUT:**")
                    st.text(entry["stdout"])
                if entry["stderr"]:
                    st.markdown("**STDERR:**")
                    st.text(entry["stderr"])
                if not (entry["console"] or entry["stdout"] or entry["stderr"]):
                    st.text("No debug logs captured for this query.")
                st.markdown("---")
        else:
            st.write("No debug logs captured yet.")

if __name__ == "__main__":
    main()
