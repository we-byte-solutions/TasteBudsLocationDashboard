"""
Sample API integration examples and mock endpoints for testing.
This file contains examples of how to integrate with common POS systems and APIs.
"""

# Example API configurations for popular POS systems
SAMPLE_API_CONFIGS = {
    "square": {
        "name": "Square POS",
        "base_url": "https://connect.squareup.com",
        "auth_type": "Bearer Token",
        "endpoints": {
            "orders": "/v2/orders/search",
            "items": "/v2/catalog/list",
            "locations": "/v2/locations"
        },
        "sample_headers": {
            "Authorization": "Bearer YOUR_SQUARE_ACCESS_TOKEN",
            "Square-Version": "2023-10-18",
            "Content-Type": "application/json"
        }
    },
    "toast": {
        "name": "Toast POS",
        "base_url": "https://api.toasttab.com",
        "auth_type": "Bearer Token",
        "endpoints": {
            "orders": "/orders/v2/orders",
            "menu": "/config/v2/menus",
            "locations": "/config/v2/restaurants"
        },
        "sample_headers": {
            "Authorization": "Bearer YOUR_TOAST_ACCESS_TOKEN",
            "Toast-Restaurant-External-ID": "YOUR_RESTAURANT_ID"
        }
    },
    "custom": {
        "name": "Custom API",
        "base_url": "https://your-api.com",
        "auth_type": "API Key",
        "endpoints": {
            "sales": "/api/v1/sales",
            "menu": "/api/v1/menu",
            "categories": "/api/v1/categories"
        },
        "sample_headers": {
            "X-API-Key": "YOUR_API_KEY",
            "Content-Type": "application/json"
        }
    }
}

# Sample data transformation functions for different API formats
def transform_square_data(square_response):
    """Transform Square API response to expected format"""
    transformed_data = []
    
    if 'orders' in square_response:
        for order in square_response['orders']:
            order_time = order.get('created_at', '')
            location_id = order.get('location_id', '')
            
            for line_item in order.get('line_items', []):
                item_data = {
                    'PLU': line_item.get('catalog_object_id', ''),
                    'Menu Item': line_item.get('name', ''),
                    'Qty': int(line_item.get('quantity', 0)),
                    'Order Date': order_time,
                    'Location': location_id,
                    'Void?': 'false'
                }
                transformed_data.append(item_data)
    
    return transformed_data

def transform_toast_data(toast_response):
    """Transform Toast API response to expected format"""
    transformed_data = []
    
    for order in toast_response:
        order_time = order.get('openedDate', '')
        location_id = order.get('restaurantGuid', '')
        
        for selection in order.get('selections', []):
            item_data = {
                'PLU': selection.get('itemGuid', ''),
                'Menu Item': selection.get('displayName', ''),
                'Qty': int(selection.get('quantity', 0)),
                'Order Date': order_time,
                'Location': location_id,
                'Void?': str(selection.get('voided', False)).lower()
            }
            transformed_data.append(item_data)
    
    return transformed_data

# Mock API server for testing (simple HTTP server)
MOCK_API_DATA = {
    "/api/sales": {
        "data": [
            {
                "item_id": 81831,
                "item_name": "1/2 Chicken Plate",
                "quantity": 2,
                "order_time": "2024-07-01T12:30:00Z",
                "location": "Downtown",
                "is_void": False
            },
            {
                "item_id": 82151,
                "item_name": "1/2 Ribs Plate", 
                "quantity": 1,
                "order_time": "2024-07-01T13:15:00Z",
                "location": "Downtown",
                "is_void": False
            },
            {
                "item_id": 2307,
                "item_name": "Corn Side",
                "quantity": 3,
                "order_time": "2024-07-01T14:00:00Z", 
                "location": "Downtown",
                "is_void": False
            }
        ]
    },
    "/api/menu": {
        "items": [
            {"plu_code": 81831, "name": "1/2 Chicken Plate", "category": "Entrees"},
            {"plu_code": 82151, "name": "1/2 Ribs Plate", "category": "Entrees"},
            {"plu_code": 2273, "name": "Full Ribs Plate", "category": "Entrees"},
            {"plu_code": 2307, "name": "Corn Side", "category": "Sides"}
        ]
    },
    "/api/categories": {
        "1/2 Chix": [81831, 81990, 81991],
        "1/2 Ribs": [82151, 82149, 82147],
        "Full Ribs": [2273, 2276, 2280],
        "Corn": [2307, 3082, 3648, 2303]
    },
    "/api/health": {
        "status": "ok",
        "timestamp": "2024-07-01T12:00:00Z"
    }
}

# Instructions for setting up API integrations
API_SETUP_INSTRUCTIONS = """
## API Integration Setup Guide

### 1. Square POS Integration
1. Create a Square Developer account
2. Create a new application
3. Get your Access Token from the Developer Dashboard
4. Use sandbox environment for testing
5. Production requires approval from Square

**Required Scopes:** ORDERS_READ, ITEMS_READ

### 2. Toast POS Integration  
1. Contact Toast for API access
2. Get Restaurant External ID
3. Obtain access token through OAuth flow
4. Use staging environment for testing

**Required Permissions:** Read orders, Read menu items

### 3. Custom API Setup
1. Ensure your API returns data in expected format
2. Set up authentication (API key, Bearer token, etc.)
3. Configure proper CORS headers if needed
4. Test endpoints with sample data

### 4. Common API Response Formats

**Sales Data Response:**
```json
{
  "data": [
    {
      "item_id": 12345,
      "item_name": "Product Name",
      "quantity": 2,
      "order_time": "2024-07-01T12:30:00Z",
      "location": "Store Location",
      "is_void": false
    }
  ]
}
```

**Menu Items Response:**
```json
{
  "items": [
    {
      "plu_code": 12345,
      "name": "Product Name", 
      "category": "Category Name",
      "price": 12.99
    }
  ]
}
```

### 5. Testing Your API
1. Use the "Test Connection" button to verify connectivity
2. Start with small date ranges
3. Check data format matches expectations
4. Verify authentication is working
"""