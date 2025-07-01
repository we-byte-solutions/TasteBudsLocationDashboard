# Sales Analytics Dashboard

## Project Overview
Advanced Streamlit-powered sales analytics dashboard designed for comprehensive data processing and visualization of sales metrics. The application offers robust PLU (Product Look-Up) data handling, dynamic category calculations, and intelligent error management for seamless reporting across multiple data sources.

## Current Features
- Interactive Streamlit dashboard with location filtering and report visualization
- CSV file upload functionality with historical data persistence in PostgreSQL database
- Category counting logic using specific PLUs from updated category mapping spreadsheets
- Time interval options supporting both 1-hour and 30-minute data breakdowns
- Custom HTML table with proper time ordering (earliest to latest) maintaining totals at bottom
- Multi-location support with separate CSV processing for each location
- Location-specific data upload with form reset capability

## Tech Stack
- Python 3.11
- Streamlit for web interface
- Pandas for data manipulation
- PostgreSQL database for data persistence
- SQLAlchemy for database operations
- Advanced PLU data integration
- Responsive UI with diagnostic capabilities

## Data Processing Logic
- Categories pull counts from specific columns:
  - Items CSV: column N 'Master Id' and column Y 'Qty'
  - Modifiers CSV: column Z 'Qty' for side dish calculations
- PLU-based category calculations using updated spreadsheets
- Quantity values used for calculating totals based on PLUs
- Location-specific processing and filtering for proper data segregation

## Recent Changes
- 2025-07-01: Added comprehensive API integration functionality
  - Implemented flexible API data pulling system supporting multiple POS systems
  - Added support for Bearer tokens, API keys, Basic auth, and custom headers
  - Created sales data, menu items, and category mappings API endpoints
  - Added connection testing and data validation
  - Integrated API interface into main application with radio button selection
  - Enhanced multi-location upload workflow with form reset capability

## User Preferences
- Prefers simple, everyday language explanations
- Needs location-specific CSV file processing (each location has separate files)
- Requires historical data persistence across app restarts
- Values clear status updates during data processing

## Project Architecture
- main.py: Main Streamlit application interface and UI components
- utils.py: Data processing functions and database operations for PLU-based calculations
- .streamlit/config.toml: Streamlit configuration for deployment
- Database schema: PostgreSQL with new_sales_data table for persistent storage
- PLU mappings: Configurable category-to-PLU relationships for accurate counting

## Development Notes
- System combines data from both Items CSV and Modifiers CSV for accurate category totals
- Database operations preserve data for other locations when uploading new data
- Custom HTML table implementation ensures proper ordering with totals at bottom
- Debugging information available to track PLU usage during calculations