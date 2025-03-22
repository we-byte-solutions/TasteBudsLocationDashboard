import pandas as pd
import streamlit as st
import os
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL)

def init_db():
    """Initialize database tables"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS new_sales_data (
                id SERIAL PRIMARY KEY,
                location TEXT NOT NULL,
                order_date DATE NOT NULL,
                service TEXT NOT NULL,
                interval_time TEXT NOT NULL,
                half_chix INTEGER NOT NULL DEFAULT 0,
                half_ribs INTEGER NOT NULL DEFAULT 0,
                full_ribs INTEGER NOT NULL DEFAULT 0,
                six_oz_mod INTEGER NOT NULL DEFAULT 0,
                eight_oz_mod INTEGER NOT NULL DEFAULT 0,
                corn INTEGER NOT NULL DEFAULT 0,
                grits INTEGER NOT NULL DEFAULT 0,
                pots INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0,
                UNIQUE (location, order_date, service, interval_time)
            )
        """))
        conn.commit()

def load_data(items_file, modifiers_file):
    """Load and preprocess sales data from CSV files"""
    try:
        # Read CSV files
        items_df = pd.read_csv(items_file)
        modifiers_df = pd.read_csv(modifiers_file)

        # Ensure string columns are properly handled
        string_columns = ['Menu Item', 'Modifier', 'Parent Menu Selection', 'Location', 'Void?']
        for df in [items_df, modifiers_df]:
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str)

        # Convert date columns to datetime
        items_df['Order Date'] = pd.to_datetime(items_df['Order Date'])
        modifiers_df['Order Date'] = pd.to_datetime(modifiers_df['Order Date'])

        # Convert Qty to numeric, handling any non-numeric values
        items_df['Qty'] = pd.to_numeric(items_df['Qty'].replace({'false': '0', 'true': '0'}), errors='coerce').fillna(0)
        modifiers_df['Qty'] = pd.to_numeric(modifiers_df['Qty'].replace({'false': '0', 'true': '0'}), errors='coerce').fillna(0)

        # Filter out void items (convert to lowercase for comparison)
        items_df = items_df[items_df['Void?'].str.lower().replace({'nan': 'false'}) != 'true']
        modifiers_df = modifiers_df[modifiers_df['Void?'].str.lower().replace({'nan': 'false'}) != 'true']

        return items_df, modifiers_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def save_report_data(date, location, report_df):
    """Save report data to database"""
    if report_df.empty:
        return

    try:
        # Delete existing data for this date and location
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM new_sales_data 
                WHERE order_date = :date AND location = :location
            """), {
                'date': date,
                'location': location
            })

            # Insert new data
            for _, row in report_df.iterrows():
                conn.execute(text("""
                    INSERT INTO new_sales_data 
                    (location, order_date, service, interval_time, 
                    half_chix, half_ribs, full_ribs, six_oz_mod, eight_oz_mod,
                    corn, grits, pots, total)
                    VALUES 
                    (:location, :order_date, :service, :interval_time,
                    :half_chix, :half_ribs, :full_ribs, :six_oz_mod, :eight_oz_mod,
                    :corn, :grits, :pots, :total)
                """), {
                    'location': location,
                    'order_date': date,
                    'service': row['Service'],
                    'interval_time': row['Interval'],
                    'half_chix': row['1/2 Chix'],
                    'half_ribs': row['1/2 Ribs'],
                    'full_ribs': row['Full Ribs'],
                    'six_oz_mod': row['6oz Mod'],
                    'eight_oz_mod': row['8oz Mod'],
                    'corn': row['Corn'],
                    'grits': row['Grits'],
                    'pots': row['Pots'],
                    'total': row['Total']
                })
            conn.commit()
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

def get_report_data(date, location):
    """Retrieve report data from database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT service as "Service",
                       interval_time as "Interval",
                       half_chix as "1/2 Chix",
                       half_ribs as "1/2 Ribs",
                       full_ribs as "Full Ribs",
                       six_oz_mod as "6oz Mod",
                       eight_oz_mod as "8oz Mod",
                       corn as "Corn",
                       grits as "Grits",
                       pots as "Pots",
                       total as "Total"
                FROM new_sales_data
                WHERE order_date = :date
                AND location = :location
                ORDER BY 
                    CASE service 
                        WHEN 'Lunch' THEN 1 
                        WHEN 'Dinner' THEN 2 
                    END,
                    interval_time
            """), {'date': date, 'location': location})

            df = pd.DataFrame(result.fetchall())
            if not df.empty:
                df = df.sort_values(['Service', 'Interval'])
            return df
    except Exception as e:
        st.error(f"Error retrieving data: {str(e)}")
        return pd.DataFrame()

def calculate_interval_counts(interval_items, interval_mods):
    """Calculate counts for a specific interval"""
    # Initialize counts
    counts = {
        '1/2 Chix': 0, '1/2 Ribs': 0, 'Full Ribs': 0,
        '6oz Mod': 0, '8oz Mod': 0,
        'Corn': 0, 'Grits': 0, 'Pots': 0
    }

    if not interval_mods.empty:
        # Count chicken orders
        chicken_mods = interval_mods[
            (interval_mods['Modifier'].str.contains('White Meat|Dark Meat', regex=True, case=False)) &
            (interval_mods['Parent Menu Selection'].str.contains('Rotisserie Chicken', case=False))
        ]
        counts['1/2 Chix'] = chicken_mods.groupby('Order Id')['Qty'].sum().sum()

        # Count sides
        sides_mapping = {
            r'\*(?:Thai )?Green Beans': 'Corn',
            r'\*Roasted Corn Grits': 'Grits',
            r'\*Zea Potatoes': 'Pots'
        }

        for pattern, key in sides_mapping.items():
            side_counts = interval_mods[
                interval_mods['Modifier'].str.contains(pattern, regex=True, case=False)
            ].groupby(['Order Id', 'Item Selection Id'])['Qty'].sum().sum()
            counts[key] = side_counts

        # Count portion modifications
        portion_mods = interval_mods[interval_mods['Modifier'].str.contains('6oz|8oz', regex=True, case=False)]
        counts['6oz Mod'] = portion_mods[
            portion_mods['Modifier'].str.contains('6oz', case=False)
        ].groupby(['Order Id', 'Item Selection Id'])['Qty'].sum().sum()

        counts['8oz Mod'] = portion_mods[
            portion_mods['Modifier'].str.contains('8oz', case=False)
        ].groupby(['Order Id', 'Item Selection Id'])['Qty'].sum().sum()

    # Count ribs
    if not interval_items.empty:
        ribs_items = interval_items[interval_items['Menu Item'].str.contains(r'\(4\)|\(8\)', regex=True, case=False)]
        counts['1/2 Ribs'] = ribs_items[
            ribs_items['Menu Item'].str.contains(r'\(4\)', regex=True, case=False)
        ].groupby('Order Id')['Qty'].sum().sum()

        counts['Full Ribs'] = ribs_items[
            ribs_items['Menu Item'].str.contains(r'\(8\)', regex=True, case=False)
        ].groupby('Order Id')['Qty'].sum().sum()

    # Calculate total
    counts['Total'] = sum(counts.values())

    return {k: int(v) for k, v in counts.items()}

def generate_report_data(items_df, modifiers_df=None, interval_minutes=60):
    """Generate report data with quantity-based counting"""
    if items_df is None or items_df.empty:
        return pd.DataFrame()

    report_data = []
    dates = sorted(items_df['Order Date'].dt.date.unique())

    for date in dates:
        # Filter data for current date
        date_items = items_df[items_df['Order Date'].dt.date == date]

        if modifiers_df is not None:
            date_mods = modifiers_df[modifiers_df['Order Date'].dt.date == date]
        else:
            date_mods = pd.DataFrame()

        # Process each service period
        for service in ['Lunch', 'Dinner']:
            # Define service hours
            start_hour = 6 if service == 'Lunch' else 16
            end_hour = 16 if service == 'Lunch' else 24

            # Filter by service period
            service_items = date_items[
                (date_items['Order Date'].dt.hour >= start_hour) &
                (date_items['Order Date'].dt.hour < end_hour)
            ]

            if not date_mods.empty:
                service_mods = date_mods[
                    (date_mods['Order Date'].dt.hour >= start_hour) &
                    (date_mods['Order Date'].dt.hour < end_hour)
                ]
            else:
                service_mods = pd.DataFrame()

            # Process each time interval
            for hour in range(start_hour, end_hour):
                # Process intervals
                minutes = [0] if interval_minutes == 60 else [0, 30]
                for minute in minutes:
                    # Filter data for current interval
                    if interval_minutes == 30:
                        interval_end = minute + 30
                        interval_items = service_items[
                            (service_items['Order Date'].dt.hour == hour) &
                            (service_items['Order Date'].dt.minute >= minute) &
                            (service_items['Order Date'].dt.minute < interval_end)
                        ]

                        if not service_mods.empty:
                            interval_mods = service_mods[
                                (service_mods['Order Date'].dt.hour == hour) &
                                (service_mods['Order Date'].dt.minute >= minute) &
                                (service_mods['Order Date'].dt.minute < interval_end)
                            ]
                        else:
                            interval_mods = pd.DataFrame()
                    else:
                        interval_items = service_items[service_items['Order Date'].dt.hour == hour]
                        interval_mods = service_mods[service_mods['Order Date'].dt.hour == hour] if not service_mods.empty else pd.DataFrame()

                    # Calculate counts
                    counts = calculate_interval_counts(interval_items, interval_mods)

                    if sum(counts.values()) > 0:
                        report_data.append({
                            'Service': service,
                            'Interval': f"{hour:02d}:{minute:02d}",
                            **counts
                        })

    # Create DataFrame and format
    if not report_data:
        return pd.DataFrame()

    report_df = pd.DataFrame(report_data)
    report_df = report_df.sort_values(['Service', 'Interval'])

    # Ensure all numeric columns are integers
    numeric_cols = ['1/2 Chix', '1/2 Ribs', 'Full Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total']
    report_df[numeric_cols] = report_df[numeric_cols].fillna(0).astype(int)

    return report_df