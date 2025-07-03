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
            print("Missing Toast credentials")
            return False
            
        login_url = f"{base_url}/authentication/v1/authentication/login"
        
        login_data = {
            "clientId": self.toast_client_id,
            "clientSecret": self.toast_client_secret,
            "userAccessType": "TOAST_MACHINE_CLIENT"
        }
        
        try:
            print(f"Attempting Toast login to: {login_url}")
            print(f"Client ID: {self.toast_client_id}")
            
            response = self.session.post(
                login_url,
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            if response.status_code == 200:
                auth_data = response.json()
                # Toast API returns token in nested structure
                token_data = auth_data.get('token', {})
                access_token = token_data.get('accessToken')
                
                if access_token:
                    # Set the bearer token for subsequent requests
                    self.session.headers['Authorization'] = f'Bearer {access_token}'
                    print("Authentication successful!")
                    return True
                else:
                    print("No access token in response")
            return False
            
        except Exception as e:
            print(f"Toast authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def pull_sales_data(self, base_url: str, location: str, date_range: tuple, 
                       endpoint_path: str = '/api/sales') -> Optional[pd.DataFrame]:
        """
        Pull sales data from a POS system or sales API
        
        Args:
            base_url: Base URL of the API
            location: Location identifier (Toast Restaurant External ID)
            date_range: Tuple of (start_date, end_date)
            endpoint_path: API endpoint path
            
        Returns:
            DataFrame with sales data or None if error
        """
        try:
            start_date, end_date = date_range
            
            # Handle Toast API specifically
            if 'toasttab.com' in base_url and endpoint_path == '/orders/v2/orders':
                return self._pull_toast_orders(base_url, location, start_date, end_date)
            
            # Generic API handling
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
            return self._process_generic_api_response(data, location)
                
        except Exception as e:
            print(f"Error pulling sales data: {e}")
            return None
    
    def _get_toast_restaurants(self, base_url: str) -> Optional[list]:
        """
        Get list of restaurants accessible with current Toast credentials
        """
        try:
            auth_header = self.session.headers.get('Authorization', '')
            if not auth_header and hasattr(st, 'session_state') and hasattr(st.session_state, 'toast_token'):
                auth_header = f"Bearer {st.session_state.toast_token}"
                
            if not auth_header:
                return None
                
            # Try different restaurant endpoints
            endpoints_to_try = [
                "/config/v2/restaurants",
                "/restaurants/v1/restaurants",
                "/config/v1/restaurants"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    headers = {'Authorization': auth_header}
                    response = self.session.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        restaurants = response.json()
                        if restaurants:
                            print(f"Found restaurants using endpoint: {endpoint}")
                            return restaurants
                except Exception as e:
                    continue
                    
            return None
        except Exception as e:
            print(f"Error getting restaurants: {str(e)}")
            return None
    
    def _pull_toast_orders(self, base_url: str, restaurant_id: str, start_date, end_date) -> Optional[pd.DataFrame]:
        """
        Pull orders from Toast API using the ordersBulk endpoint
        """
        try:
            from datetime import datetime, timezone
            
            # Convert dates to ISO format for Toast API
            start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            start_iso = start_datetime.isoformat()
            end_iso = end_datetime.isoformat()
            
            # First, try to get available restaurants to validate the restaurant_id
            restaurants = self._get_toast_restaurants(base_url)
            if restaurants:
                print("Available restaurants:")
                for restaurant in restaurants:
                    name = restaurant.get('restaurantName', restaurant.get('name', 'Unknown'))
                    guid = restaurant.get('guid', restaurant.get('id', 'No GUID'))
                    print(f"  - {name} (GUID: {guid})")
                
                # Check if provided restaurant_id matches any available restaurant
                valid_restaurant = None
                for restaurant in restaurants:
                    if (restaurant.get('guid') == restaurant_id or 
                        restaurant.get('externalId') == restaurant_id or
                        restaurant.get('id') == restaurant_id):
                        valid_restaurant = restaurant
                        break
                
                if valid_restaurant:
                    # Use the correct GUID from the restaurant data
                    restaurant_guid = valid_restaurant.get('guid', valid_restaurant.get('id', restaurant_id))
                    print(f"Using validated restaurant GUID: {restaurant_guid}")
                else:
                    print(f"Warning: Restaurant ID {restaurant_id} not found in available restaurants")
                    # Try to use the first available restaurant
                    if restaurants:
                        first_restaurant = restaurants[0]
                        restaurant_guid = first_restaurant.get('guid', first_restaurant.get('id'))
                        if restaurant_guid:
                            print(f"Using first available restaurant GUID: {restaurant_guid}")
                        else:
                            restaurant_guid = restaurant_id
                    else:
                        restaurant_guid = restaurant_id
            else:
                restaurant_guid = restaurant_id
                print(f"Could not retrieve restaurants list, using provided ID: {restaurant_guid}")
            
            url = f"{base_url}/orders/v2/ordersBulk"
            
            # Get the current authorization header - try session state first
            auth_header = self.session.headers.get('Authorization', '')
            if not auth_header and hasattr(st, 'session_state') and hasattr(st.session_state, 'toast_token'):
                auth_header = f"Bearer {st.session_state.toast_token}"
                self.session.headers['Authorization'] = auth_header
                
            if not auth_header:
                print("No authorization token found - please authenticate first")
                return None
                
            headers = {
                'Toast-Restaurant-External-ID': restaurant_guid,
                'Authorization': auth_header
            }
            
            # Try using businessDate format as alternative
            business_date = start_date.strftime('%Y%m%d')
            
            # Use businessDate instead of date range - might have different permissions
            params = {
                'businessDate': business_date
            }
            
            print(f"Toast API request: {url}")
            print(f"Headers: {headers}")
            print(f"Params: {params}")
            
            response = self.session.get(url, params=params, headers=headers)
            
            print(f"Toast API response status: {response.status_code}")
            print(f"Toast API response: {response.text[:500]}")
            
            if response.status_code == 200:
                orders_data = response.json()
                return self._process_toast_orders(orders_data, restaurant_guid)
            elif response.status_code == 403:
                print(f"Permission denied. This usually means:")
                print(f"1. Client credentials don't have access to restaurant {restaurant_guid}")
                print(f"2. Restaurant External ID is incorrect")
                print(f"3. API client needs additional permissions from Toast")
                print(f"Full error: {response.text}")
                return None
            elif response.status_code == 400:
                print(f"Bad request - malformed restaurant identifier: {restaurant_guid}")
                print(f"This means the restaurant GUID format is incorrect.")
                print(f"Full error: {response.text}")
                return None
            else:
                print(f"Toast API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error pulling Toast orders: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _process_toast_orders(self, orders_data: list, restaurant_id: str) -> pd.DataFrame:
        """
        Process Toast orders data into the expected format
        """
        # Create GUID to location mapping based on existing location data
        guid_to_location = {
            'c89fbdf2-f5d4-4109-90db-cc4b101fa4e3': 'Covington',
            'e15eb797-90c2-43aa-80f0-bf6a62ee4ceb': 'Metairie', 
            'd130031a-d7b0-40a9-bd0b-523661d41e3f': 'Kenner',
            '90b9c29c-2ccd-46d6-ac41-28c34e3d60ab': 'Denham Springs',
            '4b78f3a8-15c8-4da8-9210-e2e253a24157': 'Ridgeland',
            'bf64bd9a-85bd-4d0a-a6f9-96b92299ca8d': 'Taste Buds CSK Lab',
            'eff435a1-e629-4c1a-bb83-e0312cc5b5f0': 'Baton Rouge',
            '333ed1d7-ee67-45de-b776-10230825984b': 'Lafayette',
            '69f27d73-93ae-4092-ae21-bb9ad2e5e1ee': 'New Orleans',
            '97a109e1-b68c-49ce-b33c-07a609781f6c': 'Harvey',
            'c4431eef-a069-4b7b-bd0a-94a81ddf382e': 'Harahan'
        }
        
        # Get the proper location name, fallback to restaurant_id if not found
        location_name = guid_to_location.get(restaurant_id, restaurant_id)
        
        processed_items = []
        
        print(f"Processing {len(orders_data)} orders for restaurant {restaurant_id}")
        
        for i, order in enumerate(orders_data):
            print(f"Order {i+1} structure: {list(order.keys())}")
            
            order_date = order.get('openedDate', order.get('paidDate', ''))
            order_guid = order.get('guid', '')
            voided = order.get('voided', False)
            display_number = order.get('displayNumber', 'Unknown')
            
            print(f"Order {i+1}: Date={order_date}, GUID={order_guid}, Voided={voided}")
            
            # For now, create basic order records that can be processed by our PLU system
            # Each order gets a basic item record with a generic PLU
            if not voided and order_date:  # Skip voided orders and orders without dates
                basic_item = {
                    'PLU': '9999',  # Use generic PLU that maps to "Toast Orders" category
                    'Menu Item': f"Toast Order #{display_number}",
                    'Qty': 1,
                    'Order Date': order_date,
                    'Location': location_name,
                    'Void?': 'false',
                    'Order GUID': order_guid,
                    'Revenue Center': order.get('revenueCenter', {}).get('guid', ''),
                    'Source': order.get('source', 'Unknown')
                }
                processed_items.append(basic_item)
                print(f"Added order record for {order_guid} (Order #{display_number})")
            
        print(f"Total processed items: {len(processed_items)}")
        
        df = pd.DataFrame(processed_items)
        
        if not df.empty:
            # Convert Order Date to proper datetime
            df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
            
            # Ensure Qty is numeric
            df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
        
        return df
    
    def _process_generic_api_response(self, data, location: str) -> pd.DataFrame:
        """
        Process generic API response into expected format
        """
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
        
        # Ensure required columns exist with defaults
        if 'PLU' not in df.columns:
            df['PLU'] = ''
        if 'Menu Item' not in df.columns:
            df['Menu Item'] = ''
        if 'Qty' not in df.columns:
            df['Qty'] = 1
        if 'Order Date' not in df.columns:
            df['Order Date'] = pd.Timestamp.now()
        if 'Location' not in df.columns:
            df['Location'] = location
        if 'Void?' not in df.columns:
            df['Void?'] = 'false'
        
        # Process data types
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
        df['Void?'] = df['Void?'].astype(str).str.lower()
        
        return df
    
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
    Create Streamlit interface for Toast API configuration and data pulling
    """
    st.sidebar.subheader("Toast POS API")
    
    # Show successful locations if any
    if 'successful_locations' in st.session_state and st.session_state.successful_locations:
        st.sidebar.markdown("### ✅ Recent Data Pulls")
        for location in st.session_state.successful_locations:
            st.sidebar.write(f"• {location}")
        st.sidebar.markdown("---")
    
    # Fixed authentication type for Toast
    auth_type = "Toast POS Client"
    
    # API Configuration (simplified for Toast)
    with st.sidebar.expander("🔧 API Configuration", expanded=True):
        api_base_url = "https://ws-api.toasttab.com"
        st.text(f"API URL: {api_base_url}")
        
        auth_config = {}
        if auth_type == "Toast POS Client":
            st.info("Toast POS Authentication - Client Credentials")
            client_id = st.text_input("Client ID", value="3Oo5OQGDxStzViylPqBhJsp7gqTmP9DR")
            client_secret = st.text_input("Client Secret", 
                                        value="LUGY6f9VM_-tKdLYcOM1pm2em0jcTbTBRAFO2fd1qT1RkgdZ1Akf0mUg7DdrNIt0",
                                        type="password")
            if client_id and client_secret:
                # Clean up any potential whitespace
                client_id = client_id.strip()
                client_secret = client_secret.strip()
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
            auth_type_val = auth_config.get("type")
            auth_params = {k: v for k, v in auth_config.items() if k != "type"}
            api_puller.set_authentication(auth_type_val, **auth_params)
            
            # Special handling for Toast authentication
            if auth_type_val == "toast_client":
                # Show authentication status
                if st.session_state.get('toast_authenticated', False):
                    st.sidebar.success("✅ Toast authenticated")
                    st.sidebar.info(f"Token: ...{st.session_state.get('toast_token', '')[-20:]}")
                
                if st.sidebar.button("🔐 Authenticate with Toast", use_container_width=True):
                    with st.spinner("Authenticating with Toast..."):
                        # Test authentication directly with a simple approach
                        try:
                            import requests
                            login_url = f"{api_base_url}/authentication/v1/authentication/login"
                            login_data = {
                                "clientId": auth_config.get("client_id"),
                                "clientSecret": auth_config.get("client_secret"),
                                "userAccessType": "TOAST_MACHINE_CLIENT"
                            }
                            
                            response = requests.post(
                                login_url,
                                json=login_data,
                                headers={'Content-Type': 'application/json'}
                            )
                            
                            if response.status_code == 200:
                                auth_data = response.json()
                                token_data = auth_data.get('token', {})
                                access_token = token_data.get('accessToken')
                                
                                if access_token:
                                    st.sidebar.success("✅ Toast authentication successful")
                                    st.session_state.toast_authenticated = True
                                    st.session_state.toast_token = access_token
                                    # Also set the token in the API puller session for reuse
                                    api_puller.session.headers['Authorization'] = f'Bearer {access_token}'
                                else:
                                    st.sidebar.error("❌ No access token received")
                                    st.sidebar.json(auth_data)
                            else:
                                st.sidebar.error(f"❌ Authentication failed (Status: {response.status_code})")
                                st.sidebar.text(response.text[:500])
                                
                        except Exception as e:
                            st.sidebar.error(f"❌ Authentication error: {str(e)}")
                            st.session_state.toast_authenticated = False
        
        # Test connection
        col1, col2 = st.sidebar.columns(2)
        
        if col1.button("Test Connection", use_container_width=True):
            if auth_type_val == "toast_client":
                # Test Toast specific endpoints
                try:
                    import requests
                    auth_header = st.session_state.get('toast_token', '')
                    if auth_header:
                        # Try different Toast API endpoints to find accessible ones
                        test_headers = {'Authorization': f'Bearer {auth_header}'}
                        
                        # Test various endpoints to see what's accessible
                        test_endpoints = [
                            "/config/v2/restaurants",
                            "/restaurants/v1/restaurants", 
                            "/orders/v2/payments",
                            "/usermgmt/v1/users/me"
                        ]
                        
                        for endpoint in test_endpoints:
                            try:
                                response = requests.get(f"{api_base_url}{endpoint}", headers=test_headers, timeout=5)
                                if response.status_code == 200:
                                    st.sidebar.success(f"✅ Accessible endpoint: {endpoint}")
                                    if 'restaurants' in endpoint:
                                        data = response.json()
                                        if isinstance(data, list) and data:
                                            st.sidebar.write("Available restaurants:")
                                            for restaurant in data[:3]:
                                                st.sidebar.write(f"• {restaurant.get('restaurantName', 'Unknown')} ({restaurant.get('guid', 'No GUID')})")
                                    break
                                elif response.status_code == 403:
                                    st.sidebar.warning(f"⚠ Forbidden: {endpoint}")
                                elif response.status_code == 404:
                                    st.sidebar.info(f"ℹ Not found: {endpoint}")
                                else:
                                    st.sidebar.error(f"❌ {endpoint}: {response.status_code}")
                            except Exception as e:
                                st.sidebar.error(f"Error testing {endpoint}: {str(e)}")
                        

                        
                        response = requests.get(f"{api_base_url}/config/v2/restaurants", headers=test_headers, timeout=10)
                        
                        if response.status_code == 200:
                            restaurants = response.json()
                            st.sidebar.success(f"✅ Connected! Found {len(restaurants)} restaurants")
                            if restaurants:
                                st.sidebar.write("Available restaurants:")
                                for restaurant in restaurants[:3]:  # Show first 3
                                    st.sidebar.write(f"• {restaurant.get('restaurantName', 'Unknown')} ({restaurant.get('guid', 'No GUID')})")
                        else:
                            st.sidebar.error(f"❌ API test failed: {response.status_code}")
                            st.sidebar.text(response.text[:200])
                    else:
                        st.sidebar.error("❌ Please authenticate first")
                except Exception as e:
                    st.sidebar.error(f"❌ Connection test error: {str(e)}")
            else:
                if api_puller.test_connection(api_base_url):
                    st.sidebar.success("✅ API connection successful")
                else:
                    st.sidebar.error("❌ API connection failed")
        
        # Pull data options
        data_type = "Sales Data"  # Fixed for Toast integration
        
        if data_type == "Sales Data":
            # Sales data pulling interface
            if auth_type_val == "toast_client":
                # Define restaurant locations with correct GUIDs (no dropdown needed)
                restaurant_options = {
                    "Zea Rotisserie & Bar - Covington": "c89fbdf2-f5d4-4109-90db-cc4b101fa4e3",
                    "Zea Rotisserie & Bar - New Orleans": "69f27d73-93ae-4092-ae21-bb9ad2e5e1ee", 
                    "Zea Rotisserie & Bar- Harvey": "97a109e1-b68c-49ce-b33c-07a609781f6c",
                    "Zea Rotisserie & Cafe - Harahan": "c4431eef-a069-4b7b-bd0a-94a81ddf382e",
                    "Zea Rotisserie & Bar - Metairie": "e15eb797-90c2-43aa-80f0-bf6a62ee4ceb",
                    "Zea Rotisserie & Bar - Kenner": "d130031a-d7b0-40a9-bd0b-523661d41e3f",
                    "Zea Rotisserie & Bar - Baton Rouge": "eff435a1-e629-4c1a-bb83-e0312cc5b5f0",
                    "Zea Rotisserie & Bar - Lafayette": "333ed1d7-ee67-45de-b776-10230825984b",
                    "Zea Rotisserie & Bar - Denham Springs": "90b9c29c-2ccd-46d6-ac41-28c34e3d60ab",
                    "Zea Rotisserie & Bar - Ridgeland": "4b78f3a8-15c8-4da8-9210-e2e253a24157",
                    "Taste Buds CSK Lab": "bf64bd9a-85bd-4d0a-a6f9-96b92299ca8d"
                }
                
                st.sidebar.info("🏪 Will pull data for all restaurant locations")
            else:
                location_for_api = st.sidebar.text_input(
                    "Location ID for API",
                    help="Location identifier used by your API"
                )
            
            # Date range selection
            col1, col2 = st.sidebar.columns(2)
            # Set dates to previous calendar day since there's business activity every day
            yesterday = datetime.now().date() - timedelta(days=1)
            start_date = col1.date_input("Start Date", value=yesterday)
            end_date = col2.date_input("End Date", value=yesterday)
            
            # Set appropriate endpoint based on auth type
            sales_endpoint = "/orders/v2/ordersBulk" if auth_type_val == "toast_client" else "/api/sales"
            
            if st.sidebar.button("Pull Sales Data", use_container_width=True):
                if start_date and end_date:
                    if auth_type_val == "toast_client":
                        # Toast: Pull all locations
                        with st.spinner("Pulling data for all locations..."):
                            all_data_processed = []
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            # Make sure we're authenticated
                            if not st.session_state.get('toast_authenticated', False):
                                st.error("Please authenticate with Toast first")
                                st.stop()
                            
                            for i, (restaurant_name, restaurant_guid) in enumerate(restaurant_options.items()):
                                progress = (i + 1) / len(restaurant_options)
                                progress_bar.progress(progress)
                                status_text.write(f"Processing {restaurant_name}...")
                                
                                # Use the direct Toast API call instead of generic pull_sales_data
                                items_df = api_puller._pull_toast_orders(
                                    api_base_url, 
                                    restaurant_guid, 
                                    start_date, 
                                    end_date
                                )
                                
                                if items_df is not None and not items_df.empty:
                                    # Ensure location is set correctly
                                    items_df['Location'] = restaurant_name
                                    modifiers_df = items_df.copy()
                                    
                                    # Process and save data for each date
                                    new_dates = set(items_df['Order Date'].dt.date) if 'Order Date' in items_df.columns else {start_date}
                                    
                                    for date in new_dates:
                                        date_items = items_df[items_df['Order Date'].dt.date == date] if 'Order Date' in items_df.columns else items_df
                                        date_mods = modifiers_df[modifiers_df['Order Date'].dt.date == date] if 'Order Date' in modifiers_df.columns else modifiers_df
                                        
                                        try:
                                            print(f"Generating report data for {restaurant_name} on {date}")
                                            print(f"Date items columns: {list(date_items.columns) if not date_items.empty else 'Empty'}")
                                            print(f"Date items sample: {date_items.head(2).to_dict('records') if not date_items.empty else 'Empty'}")
                                            
                                            report_df = utils.generate_report_data(date_items, date_mods, interval_type='1 Hour')
                                            print(f"Generated report_df shape: {report_df.shape if not report_df.empty else 'Empty'}")
                                            
                                            if not report_df.empty:
                                                print(f"Saving report data for {restaurant_name} on {date}")
                                                utils.save_report_data(date, restaurant_name, report_df)
                                                print(f"Successfully saved data for {restaurant_name}")
                                                all_data_processed.append(f"{restaurant_name}: {len(date_items)} records")
                                            else:
                                                print(f"No report data generated for {restaurant_name} on {date} - empty report_df")
                                        except Exception as e:
                                            print(f"Error processing {restaurant_name}: {str(e)}")
                                            import traceback
                                            traceback.print_exc()
                                            st.error(f"Error processing {restaurant_name}: {str(e)}")
                                            continue
                                
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Only show locations with data
                            if all_data_processed:
                                # Extract successful location names for sidebar display
                                successful_locations = [summary.split(":")[0] for summary in all_data_processed]
                                st.session_state.successful_locations = successful_locations
                                
                                st.success(f"✅ Successfully processed data for {len(all_data_processed)} locations with orders")
                                st.write("**Processing Summary:**")
                                for summary in all_data_processed:
                                    st.write(f"• {summary}")
                                    
                                # Update locations list
                                db_locations, _ = utils.get_available_locations_and_dates()
                                st.session_state.locations = sorted(set(db_locations))
                                
                                # Refresh the page to show successful locations in sidebar
                                st.rerun()
                            else:
                                st.warning("No orders found for any location on this date")
                                
                    else:
                        # Other APIs: Single location
                        if location_for_api:
                            with st.sidebar.status("Pulling sales data from API...") as status:
                                items_df = api_puller.pull_sales_data(
                                    api_base_url, 
                                    location_for_api, 
                                    (start_date, end_date),
                                    sales_endpoint
                                )
                                
                                modifiers_df = items_df.copy() if items_df is not None else None
                                
                                if items_df is not None and modifiers_df is not None:
                                    new_locations = sorted(items_df['Location'].unique())
                                    new_dates = set(items_df['Order Date'].dt.date)
                                    
                                    status.update(label="Processing API data...")
                                    
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
                else:
                    st.sidebar.error("Please select start and end dates")
        
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