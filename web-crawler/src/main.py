import uvicorn
import asyncio

from mcp.server.fastmcp import FastMCP
from crawler.web_crawler import web_crawler

mcp = FastMCP("spec2Test-Crawler", stateless_http=True, json_response=True)

@mcp.tool()
async def web_crawl(
    url: str,
    use_dfs: bool = False,
    max_depth: int = 2,
    max_pages: int = 50,
    use_auth: bool = True
) -> str:
    """
    Crawl a web page or website to extract structured information including links, inputs, buttons, XPaths and content in markdown format.
    
    Args:
        url: The target URL to crawl (example: "http://www.example.com:8080" - can include subdomains to crawl deeper into the application)
        use_dfs: Whether to use Depth-First Search (DFS) crawling strategy (default: False - uses Breadth-First Search). DFS goes deep into site hierarchy, BFS explores breadth first
        max_depth: Maximum crawling depth (default: 2) - for DFS this is how deep to go into the site hierarchy, for BFS this is how many levels of breadth to explore
        max_pages: Maximum number of pages to crawl as a safety limit (default: 50) to prevent excessive crawling
        use_auth: Whether to replay captured auth actions before crawling (default: True) for starting the crawl logged in. Not recommended to crawl login and registration pages.
    
    Returns:
        Structured text containing:
        - All discovered links with their URLs, names, types, and XPath selectors
        - Interactive elements (buttons) with their types and XPath selectors  
        - Input fields with their types and XPath selectors
        - Page content converted to clean markdown format
    """
    # Convert localhost/127.0.0.1 to host.docker.internal for Docker compatibility
    if "localhost" in url or "127.0.0.1" in url:
        url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
    
    return await web_crawler(url, use_dfs, max_depth, max_pages, use_auth)

if __name__ == "__main__":
    """Run the MCP server"""    
    uvicorn.run(mcp.streamable_http_app, host="0.0.0.0", port=8000)