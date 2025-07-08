from mcp.server.fastmcp import Context
from typing import List, Dict
from mcp_ga4.auth import ga4_client
from mcp_ga4.utils import parse_property_id
import asyncio

def list_ga4_properties() -> List[Dict]:
        """
        Get a list of all GA4 properties objects accessible by the service account
        Returns:
            List[Dict]: List of GA4 properties objects with their property_id and display_name
        """
        # Get authenticated client
        try:
            client = ga4_client(type='admin')
        except Exception as e:
            raise RuntimeError(f"Failed to authenticate Google Analytics client: {e}")

        # Get account summaries
        try:
            account_summaries = client.list_account_summaries()
        except Exception as e:
            raise RuntimeError(f"Failed to list account summaries: {e}")

        # Collect all properties from all account summaries
        properties = []
        for account_summary in account_summaries:
            for prop in account_summary.property_summaries:
                property_dict = {
                    'property_id': prop.property,
                    'display_name': prop.display_name
                }
                properties.append(property_dict)
        return properties 

# @mcp.resource(
#     "ga4://properties/{property_id}/metadata",
#     name="GA4 reporting metadata",
#     description="Get the dimensions and metrics currently accepted in reporting methods for a GA4 property."
# )
async def get_metadata(property_id: str) -> Dict:
    """
    Get the dimensions and metrics currently accepted in reporting methods for a GA4 property.
    Args:
        property_id (str): The GA4 property ID (e.g., '267108084' or 'properties/267108084')
    Returns:
        Dict: Metadata about the GA4 property (dimensions and metrics)
    Raises:
        RuntimeError: If authentication fails or metadata cannot be fetched
        ValueError: If the property_id format is invalid
    """
    if not property_id:
        raise ValueError("Property ID cannot be empty")

    # Get authenticated client
    try:
        client = ga4_client(type='data')
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate Google Analytics client: {e}")

    try:
        # Use the utility function to parse the property ID
        parsed_property_id = parse_property_id(property_id)
        name = f"{parsed_property_id}/metadata"
        
        # Since GA4 client doesn't support async natively, we'll run it in a thread pool
        response = await asyncio.to_thread(client.get_metadata, name=name)

        # Format the response as a dictionary
        dimensions = [
            {
                'apiName': dim.api_name,
                'uiName': dim.ui_name,
                'description': dim.description,
                'deprecatedApiNames': list(dim.deprecated_api_names),
                'customDefinition': dim.custom_definition,
                'category': dim.category
            }
            for dim in response.dimensions
        ]
        metrics = [
            {
                'apiName': met.api_name,
                'uiName': met.ui_name,
                'description': met.description,
                'deprecatedApiNames': list(met.deprecated_api_names),
                'type': met.type_,
                'expression': met.expression,
                'customDefinition': met.custom_definition,
                'category': met.category
            }
            for met in response.metrics
        ]
        return {
            'property': name,
            'dimensions': dimensions,
            'metrics': metrics
        }
    except ValueError as e:
        # Re-raise ValueError from parse_property_id
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to fetch GA4 metadata: {e}")

def get_ga4_term_mappings(term: str) -> dict:
    """
    Maps natural language terms to GA4 API parameters.
    Example: "exit clicks" → {"dimension": "eventName", "value": "exit_click_goal"}
    """
    term_mappings = {
        "exit%20clicks": {
            "metadata": "dimension",
            "name": "eventName",
            "value": "exit_click_goal",
            "operator": "="
        },
        "pageviews": {
            "metadata": "metric",
            "name": "screenPageViews",
            "value": "screenPageViews",
            "operator": "="
        },
        "mobile users": {
            "metadata": "dimension",
            "name": "deviceCategory",
            "value": "mobile",
            "operator": "="
        }
    }
    return term_mappings.get(term.lower(), {})
