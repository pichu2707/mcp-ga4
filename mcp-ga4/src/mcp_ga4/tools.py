from mcp.server.fastmcp import Context
from mcp_ga4.auth import ga4_client
from mcp_ga4.utils import print_report_response
from typing import Optional, Dict, List, Union
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Metric,
    Dimension,
    FilterExpression,
    Filter,
    FilterExpressionList
)
import asyncio
import inspect
import json
from mcp_ga4.models import GA4ReportParams
from mcp_ga4.utils import parse_property_id

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

async def list_properties_tool(ctx: Context) -> List[Dict]:
    """
    Tool version that:
    1. First tries the resource
    2. Falls back to direct call if resource unavailable
    3. Adds error handling for the client
    """
    try:
        # Try resource first
        return await ctx.request_resource("ga4://properties", {})
    except Exception as e:
        try:
            # Fallback to direct call
            from .resources import list_ga4_properties
            return list_ga4_properties()
        except Exception as fallback_error:
            await ctx.error(f"Failed to fetch properties: {str(fallback_error)}")
            return []

async def get_metadata_tool(ctx: Context, property_id: str) -> Dict:
    """
    Tool version to fetch GA4 property metadata (dimensions and metrics).
    Tries to use the resource first, then falls back to direct call.
    """
    try:
        # Try resource first
        property_id = parse_property_id(property_id)
        return await ctx.request_resource("ga4://properties/{property_id}/metadata", {"property_id": property_id})
    except Exception as e:
        try:
            from .resources import get_metadata
            return await get_metadata(property_id)
        except Exception as fallback_error:
            await ctx.error(f"Failed to fetch property metadata: {str(fallback_error)}")
            return {"error": str(fallback_error)}

async def run_report(
    ctx: Context,
    params: GA4ReportParams
) -> dict:
    """
    Enhanced with safe property validation
    """
    # Get properties through the tool (not resource directly)
    properties = await list_properties_tool(ctx)
    
    if not properties:
        await ctx.error("No GA4 properties accessible")
        return {
            "error": "No properties available",
            "code": 503
        }

    # Validate property_id format
    if not params.property_id.startswith("properties/"):
        params.property_id = f"properties/{params.property_id}"
    
    # Check existence
    if not any(p['property_id'] == params.property_id for p in properties):
        await ctx.error(f"Invalid property: {params.property_id}")
        return {
            "error": "Invalid property ID",
            "valid_properties": properties,
            "code": 400
        }

    def _normalize_property_id(property_id: str) -> str:
        """Ensure property_id is in the format 'properties/123456'."""
        if property_id.isdigit():
            return f"properties/{property_id}"
        return property_id

    property_id = _normalize_property_id(params.property_id)
    
    async def safe_await(method, *args, **kwargs):
        if method and inspect.iscoroutinefunction(method):
            return await method(*args, **kwargs)
        elif method:
            return method(*args, **kwargs)
        # else do nothing

    def _build_single_filter(condition: dict) -> FilterExpression:
        """Handles individual filter conditions
        
        Args:
            condition: A dictionary containing:
                - field: The field name to filter on
                - value: The value to filter with
                - operator: One of:
                    For strings: "EXACT", "BEGINS_WITH", "ENDS_WITH", "CONTAINS", "FULL_REGEXP", "PARTIAL_REGEXP"
                    For numbers: "EQUAL", "LESS_THAN", "LESS_THAN_OR_EQUAL", "GREATER_THAN", "GREATER_THAN_OR_EQUAL"
                - case_sensitive: (optional) boolean for string filters
        """
        # Map human-friendly operators to GA4 API operators
        string_operator_map = {
            "=": "EXACT",
            "!=": "NOT_EXACT",
            "contains": "CONTAINS",
            "starts_with": "BEGINS_WITH",
            "ends_with": "ENDS_WITH",
            "regex": "FULL_REGEXP",
            "partial_regex": "PARTIAL_REGEXP",
            # Direct API values
            "EXACT": "EXACT",
            "NOT_EXACT": "NOT_EXACT",
            "BEGINS_WITH": "BEGINS_WITH",
            "ENDS_WITH": "ENDS_WITH",
            "CONTAINS": "CONTAINS",
            "FULL_REGEXP": "FULL_REGEXP",
            "PARTIAL_REGEXP": "PARTIAL_REGEXP"
        }
        
        numeric_operator_map = {
            "=": "EQUAL",
            "!=": "NOT_EQUAL",
            ">": "GREATER_THAN",
            ">=": "GREATER_THAN_OR_EQUAL",
            "<": "LESS_THAN",
            "<=": "LESS_THAN_OR_EQUAL",
            # Direct API values
            "EQUAL": "EQUAL",
            "NOT_EQUAL": "NOT_EQUAL",
            "GREATER_THAN": "GREATER_THAN",
            "GREATER_THAN_OR_EQUAL": "GREATER_THAN_OR_EQUAL",
            "LESS_THAN": "LESS_THAN",
            "LESS_THAN_OR_EQUAL": "LESS_THAN_OR_EQUAL"
        }
        
        operator = condition["operator"]
        field_name = condition["field"]
        value = condition["value"]
        
        # Determine if this is a numeric or string filter based on the operator
        if operator in string_operator_map:
            match_type = string_operator_map[operator]
            if match_type not in ["EXACT", "NOT_EXACT", "BEGINS_WITH", "ENDS_WITH", "CONTAINS", "FULL_REGEXP", "PARTIAL_REGEXP"]:
                raise ValueError(f"Invalid string operator: {operator}. Valid operators are: {', '.join(string_operator_map.keys())}")
            
            return FilterExpression(
                filter=Filter(
                    field_name=field_name,
                    string_filter=Filter.StringFilter(
                        match_type=match_type,
                        value=str(value),
                        case_sensitive=condition.get("case_sensitive", False)
                    )
                )
            )
        elif operator in numeric_operator_map:
            operation = numeric_operator_map[operator]
            if operation not in ["EQUAL", "NOT_EQUAL", "GREATER_THAN", "GREATER_THAN_OR_EQUAL", "LESS_THAN", "LESS_THAN_OR_EQUAL"]:
                raise ValueError(f"Invalid numeric operator: {operator}. Valid operators are: {', '.join(numeric_operator_map.keys())}")
            
            # Convert value to float for numeric comparison
            try:
                numeric_value = float(value)
            except ValueError:
                raise ValueError(f"Invalid numeric value: {value}")
            
            return FilterExpression(
                filter=Filter(
                    field_name=field_name,
                    numeric_filter=Filter.NumericFilter(
                        operation=operation,
                        value=numeric_value
                    )
                )
            )
        else:
            raise ValueError(f"Invalid operator: {operator}. Must be one of: {', '.join(list(string_operator_map.keys()) + list(numeric_operator_map.keys()))}")

    def _build_filter_expression(filters: List[Union[dict, List[dict]]]) -> FilterExpression:
        """Converts human-friendly filters to GA4's FilterExpression"""
        expressions = []
        
        for f in filters:
            if isinstance(f, dict) and "AND" in f:
                # AND group
                and_group = FilterExpressionList(
                    expressions=[_build_single_filter(cond) for cond in f["AND"]]
                )
                expressions.append(FilterExpression(and_group=and_group))
                
            elif isinstance(f, dict) and "OR" in f:
                # OR group
                or_group = FilterExpressionList(
                    expressions=[_build_single_filter(cond) for cond in f["OR"]]
                )
                expressions.append(FilterExpression(or_group=or_group))
                
            else:
                # Single condition
                expressions.append(_build_single_filter(f))
        
        return FilterExpression(and_group=FilterExpressionList(expressions=expressions))

    try:
        client = ga4_client("data")
        await safe_await(getattr(ctx, "report_progress", None), 0.1)

        # Build base request
        request = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=params.start_date, end_date=params.end_date)],
            metrics=[Metric(name=m) for m in params.metrics],
            dimensions=[Dimension(name=d) for d in params.dimensions] if params.dimensions else [],
            limit=params.limit
        )

        # Handle complex filters
        if params.dimension_filters:
            request.dimension_filter = _build_filter_expression(params.dimension_filters)
        
        await safe_await(getattr(ctx, "report_progress", None), 0.3)

        # Execute and stream results
        response = client.run_report(request)
        result = {
            "rows": [],
            "row_count": response.row_count
        }

        batch_size = min(50, params.limit) if params.limit else 50
        for i, row in enumerate(response.rows):
            if params.limit and i >= params.limit:
                break
                
            result["rows"].append({
                "dimensions": [d.value for d in row.dimension_values],
                "metrics": [float(m.value) for m in row.metric_values]
            })

            if i % batch_size == 0:
                progress = 0.3 + 0.7 * (i / (params.limit if params.limit else len(response.rows)))
                await safe_await(getattr(ctx, "stream", None), f"Rows processed: {i}/{params.limit if params.limit else 'all'}")
                await safe_await(getattr(ctx, "report_progress", None), progress)

        await safe_await(getattr(ctx, "info", None), f"Report complete. {len(result['rows'])} rows returned.")
        return result

    except Exception as e:
        await safe_await(getattr(ctx, "error", None), f"GA4 Error: {str(e)}")
        return {"error": str(e), "code": 500}

async def check_compatibility_tool(
    ctx: Context,
    property_id: str,
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    dimension_filter: Optional[Dict] = None,
    metric_filter: Optional[Dict] = None,
    compatibility_filter: Optional[str] = None
) -> Dict:
    """
    Check compatibility between dimensions and metrics for a GA4 property.
    
    Args:
        ctx: The MCP context
        property_id: The GA4 property ID
        dimensions: List of dimension names to check
        metrics: List of metric names to check
        dimension_filter: Optional filter expression for dimensions as a dict
        metric_filter: Optional filter expression for metrics as a dict
        compatibility_filter: Optional filter to only return compatible dimensions/metrics
        
    Returns:
        Dict containing compatibility information for dimensions and metrics
    """
    try:
        # Normalize property ID
        if not property_id.startswith("properties/"):
            property_id = f"properties/{property_id}"
            
        # Try resource first
        return await ctx.request_resource(
            "ga4://properties/{property_id}/checkCompatibility",
            {
                "property_id": property_id,
                "dimensions": dimensions or [],
                "metrics": metrics or [],
                "dimension_filter": dimension_filter,
                "metric_filter": metric_filter,
                "compatibility_filter": compatibility_filter
            }
        )
    except Exception as e:
        try:
            # Fallback to direct API call
            client = ga4_client("data")
            
            # Convert dict filters to FilterExpression if provided
            dimension_filter_expr = None
            if dimension_filter:
                dimension_filter_expr = FilterExpression(**dimension_filter)
                
            metric_filter_expr = None
            if metric_filter:
                metric_filter_expr = FilterExpression(**metric_filter)
            
            # Construct the request body
            request_body = {
                "dimensions": [{"name": d} for d in (dimensions or [])],
                "metrics": [{"name": m} for m in (metrics or [])],
            }
            
            if dimension_filter_expr:
                request_body["dimension_filter"] = dimension_filter_expr
            if metric_filter_expr:
                request_body["metric_filter"] = metric_filter_expr
            if compatibility_filter:
                request_body["compatibility_filter"] = compatibility_filter
            
            # Make the API call
            response = client.check_compatibility(
                request={
                    "property": property_id,
                    **request_body
                }
            )
            
            return {
                "dimension_compatibilities": [
                    {
                        "dimension_metadata": d.dimension_metadata,
                        "compatibility": d.compatibility
                    }
                    for d in response.dimension_compatibilities
                ],
                "metric_compatibilities": [
                    {
                        "metric_metadata": m.metric_metadata,
                        "compatibility": m.compatibility
                    }
                    for m in response.metric_compatibilities
                ]
            }
        except Exception as fallback_error:
            await ctx.error(f"Failed to check compatibility: {str(fallback_error)}")
            return {"error": str(fallback_error)}
    
    