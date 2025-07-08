import re

def print_report_response(response):
    """
    Prints the report response in a readable format.

    Args:
        response (RunReportResponse): The response from the run_report method.
    """
    for row in response.rows:
        session_medium = row.dimension_values[0].value
        sessions = row.metric_values[0].value
        print(f"Session Medium: {session_medium}, Sessions: {sessions}")

def parse_property_id(property_id: str) -> str:
    """
    Parse the property_id to get only number and format it with properties/ prefix.
    
    Args:
        property_id (str): The GA4 property ID (e.g., '267108084' or 'properties/267108084')
    
    Returns:
        str: Formatted property ID with 'properties/' prefix
        
    Raises:
        ValueError: If the property_id doesn't contain any numbers
    """
    if not property_id:
        raise ValueError("Property ID cannot be empty")
        
    # extract only number from property_id
    match = re.search(r'\d+', property_id)
    if not match:
        raise ValueError(f"Invalid property ID format: {property_id}. Must contain at least one number.")
        
    numeric_id = match.group()
    # Add properties/ prefix
    return f"properties/{numeric_id}"
