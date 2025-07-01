import requests
import pandas as pd
import streamlit as st
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import utils

class APIDataPuller:
    """
    Flexible API integration class for pulling various types of data
    into the sales analytics dashboard.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Sales-Analytics-Dashboard/1.0',
            'Content-Type': 'application/json'
        })
    
    def set_authentication(self, auth_type: str, **kwargs):
        """
        Set authentication for API requests
        
        Args:
            auth_type: Type of authentication ('bearer', 'basic', 'api_key', 'custom', 'toast_client')
            **kwargs: Authentication parameters
        """
        if auth_type == 'bearer':
            token = kwargs.get('token')
            if token:
                self.session.headers['Authorization'] = f'Bearer {token}'
        elif auth_type == 'api_key':
            key = kwargs.get('key')
            header_name = kwargs.get('header', 'X-API-Key')
            if key:
                self.session.headers[header_name] = key
        elif auth_type == 'basic':
            username = kwargs.get('username')
            password = kwargs.get('password')
            if username and password:
                self.session.auth = (username, password)
        elif auth_type == 'custom':
            headers = kwargs.get('headers', {})
            self.session.headers.update(headers)
        elif auth_type == 'toast_client':
            # Store Toast credentials for login
            self.toast_client_id = kwargs.get('client_id')
            self.toast_client_secret = kwargs.get('client_secret')
    
    def authenticate_toast(self, base_url: str) -> bool:
        """
        Authenticate with Toast API using client credentials
        
        Args:
            base_url: Base URL for Toast API (e.g., https://ws-api.toasttab.com)
            
        Returns:
            True if authentication successful, False otherwise
        """
        if not hasattr(self, 'toast_client_id') or not hasattr(self, 'toast_client_secret'):
            return False
            
        login_url = f"{base_url}/authentication/v1/authentication/login"
        
        login_data = {
            "clientId": self.toast_client_id,
            "clientSecret": self.toast_client_secret,
            "userAccessType": "TOAST_MACHINE_CLIENT"
        }
        
        try:
            response = self.session.post(
                login_url,
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                auth_data = response.json()
                access_token = auth_data.get('accessToken')
                if access_token:
                    # Set the bearer token for subsequent requests
                    self.session.headers['Authorization'] = f'Bearer {access_token}'
                    return True
            return False
            
        except Exception as e:
            print(f"Toast authentication error: {e}")
            return False
    
    def pull_sales_data(self, base_url: str, location: str, date_range: tuple, 
                       endpoint_path: str = '/api/sales') -> Optional[pd.DataFrame]:
        """
        Pull sales data from a POS system or sales API
        
        Args:
            base_url: Base URL of the API
            location: Location identifier
            date_range: Tuple of (start_date, end_date)
            endpoint_path: API endpoint path
            
        Returns:
            DataFrame with sales data or None if error
        """
        try:
            start_date, end_date = date_range
            
            params = {
                'location': location,
                'start_date': start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                'end_date': end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
                'format': 'json'
            }
            
            url = f"{base_url.rstrip('/')}{endpoint_path}"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to DataFrame format expected by the system
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict) and 'data' in data:
                df = pd.DataFrame(data['data'])
            else:
                df = pd.DataFrame([data])
            
            # Standardize column names to match existing system
            column_mapping = {
                'item_id': 'PLU',
                'product_id': 'PLU', 
                'plu_code': 'PLU',
                'master_id': 'Master Id',
                'quantity': 'Qty',
                'qty': 'Qty',
                'order_time': 'Order Date',
                'transaction_time': 'Order Date',
                'timestamp': 'Order Date',
                'store_location': 'Location',
                'location_name': 'Location',
                'store_name': 'Location',
                'item_name': 'Menu Item',
                'product_name': 'Menu Item',
                'modifier_name': 'Modifier',
                'is_void': 'Void?',
                'voided': 'Void?'
            }
            
            # Rename columns if they exist
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df.rename(columns={old_name: new_name}, inplace=True)
            
            # Ensure required columns exist
            required_columns = ['Order Date', 'Location', 'Qty']
            for col in required_columns:
                if col not in df.columns:
                    st.warning(f"Missing required column: {col}")
                    return None
            
            # Process data types
            df['Order Date'] = pd.to_datetime(df['Order Date'])
            df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
            
            if 'Void?' in df.columns:
                df['Void?'] = df['Void?'].astype(str).str.lower()
            else:
                df['Void?'] = 'false'
            
            return df
            
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Error processing API data: {str(e)}")
            return None
    
    def pull_menu_items(self, base_url: str, endpoint_path: str = '/api/menu') -> Optional[pd.DataFrame]:
        """
        Pull menu items and their PLU mappings from an API
        
        Args:
            base_url: Base URL of the API
            endpoint_path: API endpoint path
            
        Returns:
            DataFrame with menu items and PLU mappings
        """
        try:
            url = f"{base_url.rstrip('/')}{endpoint_path}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict) and 'items' in data:
                df = pd.DataFrame(data['items'])
            else:
                df = pd.DataFrame([data])
            
            return df
            
        except requests.exceptions.RequestException as e:
            st.error(f"Menu API request failed: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Error processing menu data: {str(e)}")
            return None
    
    def pull_category_mappings(self, base_url: str, endpoint_path: str = '/api/categories') -> Optional[Dict]:
        """
        Pull category to PLU mappings from an API
        
        Args:
            base_url: Base URL of the API
            endpoint_path: API endpoint path
            
        Returns:
            Dictionary with category mappings
        """
        try:
            url = f"{base_url.rstrip('/')}{endpoint_path}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Expected format: {"category_name": [plu1, plu2, ...]}
            if isinstance(data, dict):
                return data
            else:
                st.warning("Unexpected category mapping format")
                return None
                
        except requests.exceptions.RequestException as e:
            st.error(f"Category API request failed: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Error processing category data: {str(e)}")
            return None
    
    def test_connection(self, base_url: str, endpoint_path: str = '/api/health') -> bool:
        """
        Test API connection
        
        Args:
            base_url: Base URL of the API
            endpoint_path: Health check endpoint
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            url = f"{base_url.rstrip('/')}{endpoint_path}"
            response = self.session.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

def create_api_interface():
    """
    Create Streamlit interface for API configuration and data pulling
    """
    st.sidebar.subheader("API Data Source")
    
    # Authentication setup (outside expander for global access)
    auth_type = st.sidebar.selectbox(
        "Authentication Type",
        ["None", "Toast POS Client", "API Key", "Bearer Token", "Basic Auth", "Custom Headers"]
    )
    
    # API Configuration
    with st.sidebar.expander("🔧 API Configuration", expanded=True):
        
        # Set default URL based on auth type
        default_url = ""
        if auth_type == "Toast POS Client":
            default_url = "https://ws-api.toasttab.com"
            
        api_base_url = st.text_input(
            "API Base URL", 
            value=default_url,
            placeholder="https://api.your-pos-system.com",
            help="Base URL of your POS system or data API"
        )
        
        auth_config = {}
        if auth_type == "Toast POS Client":
            st.info("Toast POS Authentication - Client Credentials")
            client_id = st.text_input("Client ID", value="3Oo5OQGDxStzViylPqBhJsp7gqTmP9DR")
            client_secret = st.text_input("Client Secret", 
                                        value="LUGY6f9VM_-tKdLYcOM1pm2em0jcTbTBRAFO2fd1qT1RkgdZ1Akf0mUg7DdrNIt0",
                                        type="password")
            if client_id and client_secret:
                auth_config = {"type": "toast_client", "client_id": client_id, "client_secret": client_secret}
                # Auto-set Toast API base URL
                if not api_base_url:
                    api_base_url = "https://ws-api.toasttab.com"
        
        elif auth_type == "API Key":
            api_key = st.text_input("API Key", type="password")
            header_name = st.text_input("Header Name", value="X-API-Key")
            if api_key:
                auth_config = {"type": "api_key", "key": api_key, "header": header_name}
        
        elif auth_type == "Bearer Token":
            token = st.text_input("Bearer Token", type="password")
            if token:
                auth_config = {"type": "bearer", "token": token}
        
        elif auth_type == "Basic Auth":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if username and password:
                auth_config = {"type": "basic", "username": username, "password": password}
        
        elif auth_type == "Custom Headers":
            headers_text = st.text_area(
                "Headers (JSON format)",
                placeholder='{"Authorization": "Custom auth-value", "X-Custom": "value"}'
            )
            if headers_text:
                try:
                    headers = json.loads(headers_text)
                    auth_config = {"type": "custom", "headers": headers}
                except json.JSONDecodeError:
                    st.error("Invalid JSON format for headers")
    
    # API Operations
    if api_base_url:
        api_puller = APIDataPuller()
        
        # Set authentication if configured
        if auth_config:
            auth_type = auth_config.pop("type")
            api_puller.set_authentication(auth_type, **auth_config)
            
            # Special handling for Toast authentication
            if auth_type == "toast_client":
                if st.sidebar.button("🔐 Authenticate with Toast", use_container_width=True):
                    with st.spinner("Authenticating with Toast..."):
                        if api_puller.authenticate_toast(api_base_url):
                            st.sidebar.success("✅ Toast authentication successful")
                        else:
                            st.sidebar.error("❌ Toast authentication failed")
        
        # Test connection
        col1, col2 = st.sidebar.columns(2)
        
        if col1.button("Test Connection", use_container_width=True):
            if api_puller.test_connection(api_base_url):
                st.sidebar.success("✅ API connection successful")
            else:
                st.sidebar.error("❌ API connection failed")
        
        # Pull data options
        data_type = st.sidebar.selectbox(
            "Data to Pull",
            ["Sales Data", "Menu Items", "Category Mappings"]
        )
        
        if data_type == "Sales Data":
            # Sales data pulling interface
            location_for_api = st.sidebar.text_input(
                "Location ID for API",
                help="Location identifier used by your API"
            )
            
            # Date range selection
            col1, col2 = st.sidebar.columns(2)
            start_date = col1.date_input("Start Date", value=datetime.now().date() - timedelta(days=1))
            end_date = col2.date_input("End Date", value=datetime.now().date())
            
            # Set appropriate endpoint based on auth type
            default_endpoint = "/orders/v2/orders" if auth_type == "Toast POS Client" else "/api/sales"
            sales_endpoint = st.sidebar.text_input(
                "Sales Endpoint", 
                value=default_endpoint,
                help="API endpoint for sales data"
            )
            
            if col2.button("Pull Sales Data", use_container_width=True):
                if location_for_api:
                    with st.sidebar.status("Pulling sales data from API...") as status:
                        # Pull items data
                        items_df = api_puller.pull_sales_data(
                            api_base_url, 
                            location_for_api, 
                            (start_date, end_date),
                            sales_endpoint
                        )
                        
                        # For now, assume modifiers come from the same endpoint
                        # In practice, you might have separate endpoints
                        modifiers_df = items_df.copy() if items_df is not None else None
                        
                        if items_df is not None and modifiers_df is not None:
                            # Process the data similar to CSV upload
                            new_locations = sorted(items_df['Location'].unique())
                            new_dates = set(items_df['Order Date'].dt.date)
                            
                            status.update(label="Processing API data...")
                            
                            # Store in session state (similar to CSV processing)
                            if st.session_state.get('items_df') is not None:
                                st.session_state.items_df = pd.concat([st.session_state.items_df, items_df])
                                st.session_state.modifiers_df = pd.concat([st.session_state.modifiers_df, modifiers_df])
                            else:
                                st.session_state.items_df = items_df
                                st.session_state.modifiers_df = modifiers_df
                            
                            # Update locations
                            db_locations, _ = utils.get_available_locations_and_dates()
                            st.session_state.locations = sorted(set(db_locations + new_locations))
                            
                            # Process and save data
                            for date in new_dates:
                                for location in new_locations:
                                    date_items = items_df[
                                        (items_df['Order Date'].dt.date == date) &
                                        (items_df['Location'] == location)
                                    ]
                                    date_mods = modifiers_df[
                                        (modifiers_df['Order Date'].dt.date == date) &
                                        (modifiers_df['Location'] == location)
                                    ]
                                    
                                    report_df = utils.generate_report_data(date_items, date_mods, interval_type='1 Hour')
                                    if not report_df.empty:
                                        utils.save_report_data(date, location, report_df)
                            
                            status.update(label="API data processing complete!", state="complete")
                            st.sidebar.success(f"Successfully pulled {len(items_df)} records from API")
                        else:
                            st.sidebar.error("Failed to pull data from API")
                else:
                    st.sidebar.error("Please enter a location ID")
        
        elif data_type == "Menu Items":
            menu_endpoint = st.sidebar.text_input(
                "Menu Endpoint", 
                value="/api/menu",
                help="API endpoint for menu items"
            )
            
            if st.sidebar.button("Pull Menu Items", use_container_width=True):
                menu_df = api_puller.pull_menu_items(api_base_url, menu_endpoint)
                if menu_df is not None:
                    st.sidebar.success(f"Retrieved {len(menu_df)} menu items")
                    st.sidebar.dataframe(menu_df.head())
        
        elif data_type == "Category Mappings":
            category_endpoint = st.sidebar.text_input(
                "Category Endpoint", 
                value="/api/categories",
                help="API endpoint for category mappings"
            )
            
            if st.sidebar.button("Pull Categories", use_container_width=True):
                categories = api_puller.pull_category_mappings(api_base_url, category_endpoint)
                if categories:
                    st.sidebar.success(f"Retrieved {len(categories)} categories")
                    st.sidebar.json(categories)
    
    # Add API setup examples
    with st.sidebar.expander("📖 API Setup Examples", expanded=False):
        st.write("**Test API Endpoint:**")
        st.code("https://jsonplaceholder.typicode.com/posts")
        st.write("*Use this for testing the connection feature*")
        st.write("")
        st.write("**Common POS Systems:**")
        st.write("• Square: connect.squareup.com")
        st.write("• Toast: api.toasttab.com") 
        st.write("• Clover: api.clover.com")
        st.write("")
        st.write("**Authentication:**")
        st.write("• Most systems use Bearer tokens")
        st.write("• Some use API keys in headers")
        st.write("• Test with your system's documentation")

# Example API response formats for documentation
API_EXAMPLES = {
    "sales_data": {
        "description": "Expected sales data API response format",
        "example": {
            "data": [
                {
                    "item_id": 81831,
                    "item_name": "1/2 Chicken Plate",
                    "quantity": 2,
                    "order_time": "2024-07-01T12:30:00Z",
                    "location": "Downtown",
                    "is_void": False
                }
            ]
        }
    },
    "menu_items": {
        "description": "Expected menu items API response format", 
        "example": {
            "items": [
                {
                    "plu_code": 81831,
                    "name": "1/2 Chicken Plate",
                    "category": "Entrees",
                    "price": 12.99
                }
            ]
        }
    },
    "categories": {
        "description": "Expected category mappings API response format",
        "example": {
            "1/2 Chix": [81831, 81990, 81991],
            "1/2 Ribs": [82151, 82149, 82147],
            "Full Ribs": [2273, 2276, 2280]
        }
    }
}