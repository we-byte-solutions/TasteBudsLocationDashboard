import pandas as pd
import streamlit as st
import openpyxl

def load_category_mappings():
    """Load category mappings from Excel file"""
    try:
        # Read the Excel file
        items_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=0)
        modifiers_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=1)

        # Create mappings from the first two columns
        items_mapping = {}
        modifiers_mapping = {}

        # Process items mappings
        for idx, row in items_df.iterrows():
            item_name = str(row.iloc[0]).strip()
            category = str(row.iloc[1]).strip()
            if category in ['1/2 Chix', '1/2 Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Full Ribs', 'Grits', 'Pots']:
                items_mapping[item_name] = category

        # Process modifiers mappings
        for idx, row in modifiers_df.iterrows():
            modifier_name = str(row.iloc[0]).strip()
            category = str(row.iloc[1]).strip()
            if category in ['1/2 Chix', '1/2 Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Full Ribs', 'Grits', 'Pots']:
                modifiers_mapping[modifier_name] = category

        return items_mapping, modifiers_mapping
    except Exception as e:
        st.error(f"Error loading category mappings: {str(e)}")
        return {}, {}

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
    if modifiers_df is None or modifiers_df.empty:
        return pd.DataFrame()

    # Load category mappings
    items_mapping, modifiers_mapping = load_category_mappings()

    report_data = []

    # Add hour and service information
    modifiers_df = modifiers_df.copy()
    modifiers_df['Hour'] = modifiers_df['Order Date'].dt.hour
    modifiers_df['Service'] = modifiers_df['Hour'].apply(lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner')
    modifiers_df['Minute'] = modifiers_df['Order Date'].dt.minute

    # Process each service period
    for service in ['Lunch', 'Dinner']:
        # Filter by service period
        service_mods = modifiers_df[modifiers_df['Service'] == service]

        if service_mods.empty:
            continue

        # Get unique hours for this service period
        hours = sorted(service_mods['Hour'].unique())

        for hour in hours:
            # Get data for this hour
            hour_mods = service_mods[service_mods['Hour'] == hour]

            # Create intervals
            minutes = [0] if interval_minutes == 60 else [0, 30]

            for minute in minutes:
                # Filter data for current interval
                if interval_minutes == 30:
                    interval_mods = hour_mods[
                        (hour_mods['Minute'] >= minute) &
                        (hour_mods['Minute'] < minute + 30)
                    ]
                else:
                    interval_mods = hour_mods

                if not interval_mods.empty:
                    # Initialize category counts
                    counts = {
                        '1/2 Chix': 0,
                        '1/2 Ribs': 0,
                        'Full Ribs': 0,
                        '6oz Mod': 0,
                        '8oz Mod': 0,
                        'Corn': 0,
                        'Grits': 0,
                        'Pots': 0
                    }

                    # Process modifiers using mappings
                    for _, row in interval_mods.iterrows():
                        modifier = str(row['Modifier']).strip()
                        if modifier in modifiers_mapping:
                            category = modifiers_mapping[modifier]
                            counts[category] += row['Qty']

                        # Check parent menu selection for items
                        menu_item = str(row['Parent Menu Selection']).strip()
                        if menu_item in items_mapping:
                            category = items_mapping[menu_item]
                            counts[category] += row['Qty']

                    # Only add rows that have non-zero totals
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