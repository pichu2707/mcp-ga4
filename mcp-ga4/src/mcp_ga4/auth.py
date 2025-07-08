# create a function to authenticate with google analytics
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from dotenv import load_dotenv
import os

def ga4_client(type='admin'):
    """
    Create an authenticated Google Analytics 4 client using service account credentials.
    Args:
        type (str): The type of client to create, either 'admin' or 'data'
    Returns:
        AnalyticsAdminServiceClient: An authenticated GA4 client
    """
    # Load environment variables from .env file
    load_dotenv()

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Raise an error if the credentials are not found
    if not os.path.isfile(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
        raise FileNotFoundError(f"Credentials file not found at: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    
    # Create the client
    try:
        if type == 'admin':
            client = AnalyticsAdminServiceClient()
        elif type == 'data':
            client = BetaAnalyticsDataClient()
        else:
            raise ValueError(f"Invalid client type: {type}")
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate Google Analytics client: {e}")

    return client
