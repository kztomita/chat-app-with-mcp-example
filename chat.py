import anthropic
import argparse
import asyncio
from dotenv import load_dotenv
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

load_dotenv(dotenv_path="./.env")

api_key = os.getenv("API_KEY")

# Create server parameters for stdio connection
config_server_params_list = [
    StdioServerParameters(
        command="./.venv/bin/python",       # Executable
        args=["mcp-servers/get-uuid.py"],   # Optional command line arguments
        env=None,                           # Optional environment variables
    ),
    StdioServerParameters(
        command="./.venv/bin/python",
        args=["mcp-servers/get-datetime.py"],
        env=None,
    ),
]

async def get_server_tools(server_params: StdioServerParameters) -> list:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write
        ) as session:
            # Initialize the connection
            await session.initialize()
            tools_result = await session.list_tools()
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                })
    return tools

class MCPSeverConnector:
    """ Class that provides an interface for connecting to MCP Server """
    def __init__(self, server_params_list: list):
        self.server_params_list = server_params_list
        self.tools = None
        self.name_map = None

    async def load(self):
        self.tools = []
        self.name_map = {}   # Mapping table from name to server_params

        # List available tools
        for server_params in self.server_params_list:
            server_tools = await get_server_tools(server_params)
            for tool in server_tools:
                self.tools += server_tools
                self.name_map[tool["name"]] = server_params

    def get_server_tools(self) -> list:
        return self.tools

    def _get_server_params_by_name(self, name: str) -> StdioServerParameters | None:
        """Get the corresponding StdioServerParameters from the name of ToolUseBlock"""
        if name in self.name_map:
            return self.name_map[name]
        return None

    async def call_tool(self, name: str, args: dict) -> types.CallToolResult:
        """
        Calling tools.

        Parameters:
            name: str
                The name of the tool to call.
            args: dict
                The arguments to pass to the specified tool.

        Returns:
            types.CallToolResult
                The result of the tool invocation.

        Raises:
            Exception
                Raised if the tool invocation results in an error.
        """
        # Identify and call server_params from name
        server_params = self._get_server_params_by_name(name)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(
                    read, write
            ) as session:
                # Initialize the connection
                await session.initialize()

                result = await session.call_tool(name, args)
                if result.isError:
                    raise Exception("Error calling tool: {}".format(result.content))
        return result



class Application:
    def __init__(self, role: str, server_params_list: list):
        self.role_description = role
        self.server_connector = MCPSeverConnector(server_params_list)

    async def run(self):
        await self.server_connector.load()
        await self.startup()

    async def startup(self):
        handler = ChatHandler(self.server_connector, self.role_description)
        chat_controller = ChatController(handler)
        await chat_controller.run()


def show_usage(usage):
    print("Cache Creation Input Tokens: {}".format(usage.cache_creation_input_tokens))
    print("Cache Read Input Tokens: {}".format(usage.cache_read_input_tokens))
    print("Input Tokens: {}".format(usage.input_tokens))
    print("Output Tokens: {}".format(usage.output_tokens))


def find_tool_use_block(message_content: list) -> anthropic.types.tool_use_block.ToolUseBlock | None:
    """
    Find the first ToolUseBlock in the content.
    :param message_content: The content of the message.
    :return: The first ToolUseBlock found, or None if not found.
    """
    for element in message_content:
        if isinstance(element, anthropic.types.tool_use_block.ToolUseBlock):
            return element
    return None


class ChatHandler:
    def __init__(self, server_connector: MCPSeverConnector, role_descr: str | None):
        self.server_connector = server_connector
        self.role_description = role_descr

    async def send(self, messages: list, use_tool: bool = True) -> list:
        args = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 1024,
            "messages": messages,
        }
        if use_tool:
            args["tools"] = self.server_connector.get_server_tools()

        if self.role_description is not None:
            args["system"] = self.role_description

        reply = ""
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(**args) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                reply += text
            print("\n")

            show_usage(stream.get_final_message().usage)

            message = stream.get_final_message()
            #print(message)

            tool_use_block = find_tool_use_block(message.content)
            if tool_use_block is None:
                # Add a conversation history
                messages.append({"role": "assistant", "content": reply})
            else:
                # https://docs.anthropic.com/ja/docs/build-with-claude/tool-use/overview
                messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": reply,
                            },
                            {
                                "type": "tool_use",
                                "id": tool_use_block.id,
                                "name": tool_use_block.name,
                                "input": tool_use_block.input,
                            },
                        ]
                    }
                )

                print("Calling {} {}".format(tool_use_block.name, tool_use_block.input))

                args = {}
                if isinstance(tool_use_block.input, dict):
                    args = tool_use_block.input

                await self.call_tool(tool_use_block, messages, args)
                # Send to LLM including results from Tool(MCP Server).
                await self.send(messages, False)

        return messages

    async def call_tool(self, tool_use_block: anthropic.types.tool_use_block.ToolUseBlock, messages: list, args: dict):
        """
        Call a Tool from MCP Server.

        Parameters:
            tool_use_block: anthropic.types.tool_use_block.ToolUseBlock
                ToolUseBlock returned by the LLM
            messages: list
                Message context.
                When returning from this method, a message with type tool_result is added.
            args: dict
                API arguments

        Raises:
        Exception
            If the tool call fails or returns an error, an exception is raised with details about the failure.
        """
        result = await self.server_connector.call_tool(tool_use_block.name, args)

        print("Result: {}".format(result.content[0].text))
        # Append an MCP Server result.
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": result.content[0].text,
                }
            ]
        })


def read_message() -> str:
    content = ""
    for line in sys.stdin:
        content += line

    content = content.strip()
    return content


class ChatController:
    def __init__(self, chat_handler: ChatHandler):
        self.chat_handler = chat_handler

    async def run(self):
        messages = []
        is_tty = sys.stdin.isatty()
        while True:
            if is_tty:
                print("Please enter the text and press Ctrl + D:")

            try:
                content = read_message()
            except KeyboardInterrupt:
                break

            if content == "":
                print("Empty message.")
                continue

            if content.find("/show context") == 0:
                print(messages)
                continue
            elif content.find("/reset") == 0:
                messages = []
                print("Reset context.")
                continue
            elif content.find("/exit") == 0:
                print("Bye.")
                break

            print("Sending...")

            messages.append({"role": "user", "content": content})
            messages = await self.chat_handler.send(messages)
            if not is_tty:
                break


def get_claude_role(file: str) -> str:
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"Role file '{file}' does not exist.")
    with open(file, "r") as f:
        role = f.read().strip()
    return role


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--role", metavar="filename", help="File with Claude's role description.")
    args = parser.parse_args()

    role = None
    if args.role:
        role = get_claude_role(args.role)

    app = Application(role, config_server_params_list)
    asyncio.run(app.run())

if __name__ == '__main__':
    main()
