import pandas as pd
import streamlit as st

def load_category_mappings(items_categories, modifiers_categories):
    """Load category mappings from Excel files"""
    try:
        items_mapping = pd.read_excel(items_categories)
        modifiers_mapping = pd.read_excel(modifiers_categories)
        return items_mapping, modifiers_mapping
    except Exception as e:
        st.error(f"Error loading category mappings: {str(e)}")
        return None, None

def load_data(items_file, modifiers_file):
    """Load and preprocess sales data from CSV files"""
    try:
        # Read CSV files
        items_df = pd.read_csv(items_file)
        modifiers_df = pd.read_csv(modifiers_file)

        # Convert date columns to datetime
        items_df['Order Date'] = pd.to_datetime(items_df['Order Date'])
        modifiers_df['Order Date'] = pd.to_datetime(modifiers_df['Order Date'])

        # Convert Qty to numeric, handling 'false' values
        items_df['Qty'] = pd.to_numeric(items_df['Qty'].replace('false', '0'), errors='coerce').fillna(0)
        modifiers_df['Qty'] = pd.to_numeric(modifiers_df['Qty'].replace('false', '0'), errors='coerce').fillna(0)

        return items_df, modifiers_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def generate_report_data(items_df, modifiers_df=None, interval_minutes=60):
    """Generate report data with simplified processing"""
    if items_df is None or items_df.empty:
        return pd.DataFrame()

    # Filter out void items
    items_df = items_df.copy()
    items_df['Void?'] = items_df['Void?'].fillna('false').astype(str).str.lower()
    items_df = items_df[items_df['Void?'] != 'true']

    if modifiers_df is not None and not modifiers_df.empty:
        modifiers_df = modifiers_df.copy()
        modifiers_df['Void?'] = modifiers_df['Void?'].fillna('false').astype(str).str.lower()
        modifiers_df = modifiers_df[modifiers_df['Void?'] != 'true']

    # Load category mappings
    items_mapping, modifiers_mapping = load_category_mappings(
        'attached_assets/Items_Category Details.xlsx',
        'attached_assets/Modifiers_Category Details.xlsx'
    )

    report_data = []

    # Process each date
    dates = sorted(items_df['Order Date'].dt.date.unique())

    for date in dates:
        # Filter data for current date
        date_items = items_df[items_df['Order Date'].dt.date == date]
        date_mods = modifiers_df[modifiers_df['Order Date'].dt.date == date] if modifiers_df is not None else pd.DataFrame()

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
            service_mods = date_mods[
                (date_mods['Order Date'].dt.hour >= start_hour) &
                (date_mods['Order Date'].dt.hour < end_hour)
            ] if not date_mods.empty else pd.DataFrame()

            # Process each hour
            for hour in range(start_hour, end_hour):
                # Filter by hour
                hour_items = service_items[service_items['Order Date'].dt.hour == hour]
                hour_mods = service_mods[service_mods['Order Date'].dt.hour == hour] if not service_mods.empty else pd.DataFrame()

                # Process intervals
                minutes = [0] if interval_minutes == 60 else [0, 30]
                for minute in minutes:
                    # Filter by interval
                    if interval_minutes == 30:
                        interval_items = hour_items[
                            (hour_items['Order Date'].dt.minute >= minute) &
                            (hour_items['Order Date'].dt.minute < minute + 30)
                        ]
                        interval_mods = hour_mods[
                            (hour_mods['Order Date'].dt.minute >= minute) &
                            (hour_mods['Order Date'].dt.minute < minute + 30)
                        ] if not hour_mods.empty else pd.DataFrame()
                    else:
                        interval_items = hour_items
                        interval_mods = hour_mods

                    # Calculate counts based on category mappings
                    counts = {
                        '1/2 Chix': len(interval_mods[
                            (interval_mods['Modifier'].str.contains('White Meat|Dark Meat', regex=True, case=False)) &
                            (interval_mods['Parent Menu Selection'].str.contains('Rotisserie Chicken', case=False))
                        ]) if not interval_mods.empty else 0,

                        '1/2 Ribs': len(interval_items[
                            interval_items['Menu Item'].str.contains('(4)', case=False)
                        ]),

                        'Full Ribs': len(interval_items[
                            interval_items['Menu Item'].str.contains('(8)', case=False)
                        ]),

                        '6oz Mod': len(interval_mods[
                            interval_mods['Modifier'].str.contains('6oz', case=False)
                        ]) if not interval_mods.empty else 0,

                        '8oz Mod': len(interval_mods[
                            interval_mods['Modifier'].str.contains('8oz', case=False)
                        ]) if not interval_mods.empty else 0,

                        'Corn': len(interval_mods[
                            interval_mods['Modifier'].str.contains('Green Beans', case=False)
                        ]) if not interval_mods.empty else 0,

                        'Grits': len(interval_mods[
                            interval_mods['Modifier'].str.contains('Roasted Corn Grits', case=False)
                        ]) if not interval_mods.empty else 0,

                        'Pots': len(interval_mods[
                            interval_mods['Modifier'].str.contains('Zea Potatoes', case=False)
                        ]) if not interval_mods.empty else 0
                    }

                    # Only add rows with non-zero totals
                    total = sum(counts.values())
                    if total > 0:
                        report_data.append({
                            'Service': service,
                            'Interval': f"{hour:02d}:{minute:02d}",
                            **counts,
                            'Total': total
                        })

    # Create DataFrame and format
    if not report_data:
        return pd.DataFrame()

    report_df = pd.DataFrame(report_data)
    report_df = report_df.sort_values(['Service', 'Interval'])
    report_df = report_df.fillna(0)

    # Convert numeric columns to integers
    numeric_cols = ['1/2 Chix', '1/2 Ribs', 'Full Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total']
    report_df[numeric_cols] = report_df[numeric_cols].astype(int)

    return report_df