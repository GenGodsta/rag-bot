from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

class MCPClient:
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.session: ClientSession | None = None
        self._stack = AsyncExitStack()

    async def connect(self):
        params = StdioServerParameters(command="python", args=[self.server_script])
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def call_tool(self, tool_name: str, args: dict):
        result = await self.session.call_tool(tool_name, args)
        if result.isError:
            raise RuntimeError(f"Tool {tool_name} failed: {result.content[0].text}")
        return result.content

    async def list_tools(self):
        return await self.session.list_tools()

    async def close(self):
        await self._stack.aclose()