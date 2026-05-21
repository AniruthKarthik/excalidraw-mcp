from fastmcp import FastMCP

mcp = FastMCP("Learning MCP")


@mcp.tool
def greet(name: str) -> str:
    """Greet a user"""
    return f"Hello {name}"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


if __name__ == "__main__":
    mcp.run()