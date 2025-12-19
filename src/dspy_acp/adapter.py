"""ACP (Agent Client Protocol) adapter for DSPy."""

import asyncio
import asyncio.subprocess as aio_subprocess
import os
import threading
from typing import Any, Optional

import dspy
from acp import (
    PROTOCOL_VERSION,
    Client,
    connect_to_agent,
    text_block,
)
from acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AvailableCommandsUpdate,
    ClientCapabilities,
    CurrentModeUpdate,
    Implementation,
    PermissionOption,
    RequestPermissionResponse,
    TextContentBlock,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    UserMessageChunk,
)


class _ACPClient(Client):
    """Internal ACP client that handles session notifications."""

    def __init__(self):
        self.accumulated_text = ""

    def reset(self):
        """Reset accumulated text for a new prompt."""
        self.accumulated_text = ""

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        """Handle permission requests - auto-approve for now."""
        # Parameters required by interface but not used in this simple implementation
        _ = options, session_id, tool_call, kwargs
        return RequestPermissionResponse(outcome={"outcome": "approved"})

    async def session_update(
        self,
        session_id: str,
        update: UserMessageChunk
        | AgentMessageChunk
        | AgentThoughtChunk
        | ToolCallStart
        | ToolCallProgress
        | AgentPlanUpdate
        | AvailableCommandsUpdate
        | CurrentModeUpdate,
        **kwargs: Any,
    ) -> None:
        """Handle session update notifications from the agent."""
        # Parameters required by interface but not used
        _ = session_id, kwargs
        if isinstance(update, AgentMessageChunk):
            content = update.content
            if isinstance(content, TextContentBlock):
                self.accumulated_text += content.text


class _AsyncRunner:
    """Runs async code in a background thread with persistent event loop."""

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()

    def start(self):
        """Start the background event loop thread."""
        if self._thread is not None:
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._started.wait()

    def _run_loop(self):
        """Run the event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()

    def run(self, coro):
        """Run a coroutine and return its result."""
        if self._loop is None:
            self.start()

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def stop(self):
        """Stop the background event loop."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._loop = None
            self._thread = None


class ACPAdapter(dspy.BaseLM):
    """
    DSPy adapter for ACP (Agent Client Protocol) agents.

    This adapter uses the official agent-client-protocol SDK to communicate
    with ACP-compatible agents via JSON-RPC over stdin/stdout.

    Args:
        model: Model identifier for DSPy tracking.
        command: Command to launch the ACP agent.
        auth_method: Authentication method. Options depend on the selected ACP agent.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in response.

    Example:
        >>> from dspy_acp import ACPAdapter
        >>> import dspy
        >>>
        >>> lm = ACPAdapter(command=["path/to/your-acp-agent"])
        >>> dspy.configure(lm=lm)
    """

    def __init__(
        self,
        model: str = "acp",
        command: Optional[list[str]] = None,
        auth_method: str = "chatgpt",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        if not command:
            raise ValueError(
                "command is required. Use CodexACPAdapter for the codex-acp default."
            )
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.command = command
        self.auth_method = auth_method
        self._runner = _AsyncRunner()
        self._proc: Optional[aio_subprocess.Process] = None
        self._conn = None
        self._client: Optional[_ACPClient] = None
        self._session_id: Optional[str] = None
        self._initialized = False

    async def _start_process(self):
        """Start the ACP agent process."""
        self._proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=aio_subprocess.PIPE,
            stdout=aio_subprocess.PIPE,
            stderr=None,
        )

        if self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("Agent process does not expose stdio pipes")

        self._client = _ACPClient()
        self._conn = connect_to_agent(self._client, self._proc.stdin, self._proc.stdout)

    async def _ensure_session(self) -> None:
        """Ensure we have an active connection and session."""
        if not self._initialized:
            await self._start_process()

            # Initialize the connection
            await self._conn.initialize(
                protocol_version=PROTOCOL_VERSION,
                client_capabilities=ClientCapabilities(),
                client_info=Implementation(
                    name="dspy-acp", title="DSPy ACP Adapter", version="0.1.0"
                ),
            )

            # Authenticate
            print(f"Authenticating with method: {self.auth_method}")
            if self.auth_method == "chatgpt":
                print("A browser window will open for ChatGPT login...")

            await self._conn.authenticate(method_id=self.auth_method)
            print("Authentication successful!")

            # Create a new session
            session_response = await self._conn.new_session(
                cwd=os.getcwd(), mcp_servers=[]
            )
            self._session_id = session_response.session_id
            self._initialized = True

    async def _send_prompt_async(self, prompt: str) -> str:
        """Send a prompt and return the response asynchronously."""
        await self._ensure_session()

        # Reset the client's accumulated text
        self._client.reset()

        # Send the prompt and wait for response
        await self._conn.prompt(
            session_id=self._session_id,
            prompt=[text_block(prompt)],
        )

        return self._client.accumulated_text

    def forward(
        self,
        prompt: Optional[str] = None,
        messages: Optional[list] = None,
        **kwargs,
    ):
        """
        Main entry point for DSPy. Converts input to prompt and returns response.
        """
        _ = kwargs  # Unused but part of interface
        # Convert messages to prompt if needed
        if prompt is None and messages is not None:
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        elif prompt is None:
            prompt = ""

        try:
            text = self._runner.run(self._send_prompt_async(prompt))
        except Exception as e:
            print(f"Error calling ACP server: {e}")
            text = ""

        # Return OpenAI-style response object
        class _Msg:
            def __init__(self, content: str):
                self.content = content
                self.tool_calls = None

        class _Choice:
            def __init__(self, message: _Msg):
                self.message = message
                self.logprobs = None

        class _Response:
            def __init__(self, text: str, model: str):
                self.choices = [_Choice(_Msg(text))]
                self.usage = {}
                self.model = model

        return _Response(text=text, model=self.model)

    async def _close_async(self) -> None:
        """Close the connection asynchronously."""
        # Close connection first (this stops background tasks)
        if self._conn is not None:
            try:
                await self._conn.close()
            except Exception:
                pass
            self._conn = None
            # Allow background tasks to complete
            await asyncio.sleep(0.1)

        # Then terminate the process
        if self._proc is not None:
            if self._proc.returncode is None:
                self._proc.terminate()
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=5.0)
                except (ProcessLookupError, asyncio.TimeoutError):
                    pass
            self._proc = None

        self._session_id = None
        self._initialized = False
        self._client = None

    def close(self) -> None:
        """Clean up the connection and subprocess."""
        if self._proc is not None or self._conn is not None:
            try:
                self._runner.run(self._close_async())
            except Exception:
                pass
        self._runner.stop()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __deepcopy__(self, memo):
        _ = memo  # Unused but required by interface
        return self

    def dump_state(self) -> dict:
        return {"model": self.model}

    def load_state(self, state: dict) -> None:
        self.model = state.get("model", "acp")


class CodexACPAdapter(ACPAdapter):
    """Convenience wrapper for codex-acp via npx."""

    def __init__(
        self,
        model: str = "acp",
        command: Optional[list[str]] = None,
        auth_method: str = "chatgpt",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        command = command or ["npx", "@zed-industries/codex-acp"]
        super().__init__(
            model=model,
            command=command,
            auth_method=auth_method,
            temperature=temperature,
            max_tokens=max_tokens,
        )
