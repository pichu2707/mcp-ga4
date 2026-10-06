# server.py
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.utilities.logging import configure_logging, get_logger
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp_ga4 import resources, tools, prompts
from dotenv import load_dotenv
import os
import traceback
from contextlib import asynccontextmanager
# Load environment variables from .env file
load_dotenv()

# Configure logging using MCP utilities
configure_logging(
    level=os.getenv("MCP_LOG_LEVEL", "DEBUG")
)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(mcp: FastMCP):
    """
    Manage server lifecycle and resources.
    
    Args:
        mcp: The FastMCP server instance
    """
    # Server startup tasks
    logger.info("Starting MCP GA4 server...")
    yield
    # Server shutdown tasks
    logger.info("Shutting down MCP GA4 server...")

# Create the MCP server instance
mcp = FastMCP(
    "MCP GA4 GA4",
    transport=os.getenv("MCP_TRANSPORT", "stdio"),
    debug=os.getenv("MCP_DEBUG", "true") == "true",
    log_level=os.getenv("MCP_LOG_LEVEL", "DEBUG"),
    lifespan=lifespan,
    capabilities={
        "resources": {"listChanged": True},
        "tools": {"listChanged": True},
    }
)


# List GA4 properties
mcp.tool(
    name="list_ga4_properties",
    description="User-friendly property listing with fallback"
)(tools.list_properties_tool)

# Fetch a report from Google Analytics 4
mcp.tool(
    name="run_report",
    description="Get a GA4 report with optional filters"
)(tools.run_report)

# Register the tool to fetch GA4 property metadata (dimensions and metrics)
mcp.tool(
    name="get_metadata",
    description="Get the dimensions and metrics currently accepted in reporting methods for a GA4 property. Accepts property_id as parameter."
)(tools.get_metadata_tool)

# Check compatibility between dimensions and metrics for a GA4 property.
mcp.tool(
    name="check_compatibility",
    description="Check compatibility between dimensions and metrics for a GA4 property."
)(tools.check_compatibility_tool)

# Register resources
# Fetch a list of GA4 properties and their IDs
mcp.resource(
    "ga4://properties",
    name="list_ga4_properties",
    description="Raw GA4 properties list"
)(resources.list_ga4_properties)

# Get the dimensions and metrics currently accepted in reporting methods for a GA4 property.
mcp.resource(
    "ga4://properties/{property_id}/metadata",
    name="get_metadata",
    description="Get the dimensions and metrics currently accepted in reporting methods for a GA4 property."
)(resources.get_metadata)

# Maps natural language terms to GA4 API parameters.
mcp.resource(
    "mappings://ga4_terms/{term}",
    name="get_ga4_term_mappings",
    description="Maps natural language terms to GA4 API parameters."
)(resources.get_ga4_term_mappings)

# Add the prompt
# mcp.prompt(
#     name="ga4_property_id_instruction",
#     description="When calling the get_ga4_report tool, for the property_id parameter, always use the full property string "
#     "in the format 'properties/{property_id}', e.g., 'properties/267108084', "
#     "not just the numeric ID."
# )(prompts.ga4_property_id_instruction)

logger.info(f"FastMCP server will listen on port: {mcp.settings.port}")

def main():
    try:
        logger.info("Starting MCP GA4 server...")
        transport = os.getenv("MCP_TRANSPORT", 'stdio') #"streamable-http"
        
        if transport == "stdio":
            mcp.run(transport="stdio")
        else:
            # For streamable-http and SSE
            mcp.run(
                transport=transport,
                mount_path=os.getenv("MCP_PATH", "/mcp")
            )
        logger.info("MCP GA4 server started")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    main()