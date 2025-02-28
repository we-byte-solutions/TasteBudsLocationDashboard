import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Get database connection string from environment
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_engine():
    """Create SQLAlchemy engine for database connection"""
    return create_engine(DATABASE_URL)

def create_tables():
    """Create necessary database tables if they don't exist"""
    engine = get_db_engine()
    
    with engine.connect() as conn:
        # Create items_data table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS items_data (
                id SERIAL PRIMARY KEY,
                location VARCHAR(255),
                order_id VARCHAR(255),
                order_number VARCHAR(255),
                sent_date TIMESTAMP,
                order_date TIMESTAMP,
                service VARCHAR(50),
                dining_option VARCHAR(100),
                menu_item VARCHAR(255),
                menu VARCHAR(255),
                item_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create modifiers_data table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS modifiers_data (
                id SERIAL PRIMARY KEY,
                location VARCHAR(255),
                order_id VARCHAR(255),
                modifier_id VARCHAR(255),
                modifier VARCHAR(255),
                parent_menu_selection VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.commit()

def import_csv_to_db(items_file, modifiers_file):
    """Import CSV data into database tables"""
    engine = get_db_engine()
    
    # Read and process items CSV
    items_df = pd.read_csv(items_file)
    items_df['sent_date'] = pd.to_datetime(items_df['Sent Date'])
    items_df['order_date'] = pd.to_datetime(items_df['Order Date'])
    
    # Read and process modifiers CSV
    modifiers_df = pd.read_csv(modifiers_file)
    
    # Insert data into database
    items_df.to_sql('items_data', engine, if_exists='append', index=False)
    modifiers_df.to_sql('modifiers_data', engine, if_exists='append', index=False)
    
    return datetime.now()

def get_data_from_db():
    """Retrieve data from database for report generation"""
    engine = get_db_engine()
    
    with engine.connect() as conn:
        items_df = pd.read_sql('SELECT * FROM items_data', conn)
        modifiers_df = pd.read_sql('SELECT * FROM modifiers_data', conn)
        
        # Convert date columns to datetime
        items_df['order_date'] = pd.to_datetime(items_df['order_date'])
        
        return items_df, modifiers_df

def get_last_update_time():
    """Get the timestamp of the last data update"""
    engine = get_db_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT MAX(created_at) as last_update
            FROM (
                SELECT created_at FROM items_data
                UNION ALL
                SELECT created_at FROM modifiers_data
            ) updates
        """))
        last_update = result.fetchone()[0]
        
        return last_update or datetime.now()
