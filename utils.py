import pandas as pd
import streamlit as st

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
    if items_df.empty:
        return pd.DataFrame()

    # Create time intervals and service periods
    items_df = items_df.copy()
    modifiers_df = modifiers_df.copy() if modifiers_df is not None else pd.DataFrame()

    # Add hour and service columns
    items_df['Hour'] = items_df['Order Date'].dt.hour
    items_df['Service'] = items_df['Hour'].apply(lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner')
    items_df['Minute'] = items_df['Order Date'].dt.minute

    if not modifiers_df.empty:
        modifiers_df['Hour'] = modifiers_df['Order Date'].dt.hour
        modifiers_df['Service'] = modifiers_df['Hour'].apply(lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner')
        modifiers_df['Minute'] = modifiers_df['Order Date'].dt.minute

    # Create time intervals
    def create_interval(hour, minute):
        if interval_minutes == 30:
            period = '30' if minute >= 30 else '00'
            return f"{hour:02d}:{period}"
        return f"{hour:02d}:00"

    items_df['Interval'] = items_df.apply(
        lambda x: create_interval(x['Hour'], x['Minute']), 
        axis=1
    )

    if not modifiers_df.empty:
        modifiers_df['Interval'] = modifiers_df.apply(
            lambda x: create_interval(x['Hour'], x['Minute']), 
            axis=1
        )

    report_data = []

    # Process each service period
    for service in ['Lunch', 'Dinner']:
        # Filter for service
        service_items = items_df[items_df['Service'] == service]
        service_mods = modifiers_df[modifiers_df['Service'] == service] if not modifiers_df.empty else pd.DataFrame()

        # Get unique intervals
        intervals = sorted(service_items['Interval'].unique()) if not service_items.empty else []

        for interval in intervals:
            # Filter data for current interval
            interval_items = service_items[service_items['Interval'] == interval]
            interval_mods = service_mods[service_mods['Interval'] == interval] if not service_mods.empty else pd.DataFrame()

            # Calculate counts using safe string operations
            counts = {
                '1/2 Chix': interval_mods[
                    interval_mods['Modifier'].str.contains('Dark Meat|White Meat', na=False, regex=True) &
                    interval_mods['Parent Menu Selection'].str.contains('Rotisserie Chicken', na=False)
                ]['Qty'].sum(),

                '1/2 Ribs': interval_mods[
                    interval_mods['Parent Menu Selection'].str.contains('(4) (Dry|Thai) Ribs', na=False, regex=True)
                ]['Qty'].sum(),

                'Full Ribs': interval_mods[
                    interval_mods['Parent Menu Selection'].str.contains('(8) (Dry|Thai) Ribs', na=False, regex=True)
                ]['Qty'].sum(),

                '6oz Mod': interval_mods[
                    interval_mods['Modifier'].str.contains('6oz', na=False)
                ]['Qty'].sum() if not interval_mods.empty else 0,

                '8oz Mod': interval_mods[
                    interval_mods['Modifier'].str.contains('8oz', na=False)
                ]['Qty'].sum() if not interval_mods.empty else 0,

                'Corn': interval_mods[
                    interval_mods['Modifier'].str.contains('*Thai Green Beans|*Green Beans', na=False, regex=True)
                ]['Qty'].sum() if not interval_mods.empty else 0,

                'Grits': interval_mods[
                    interval_mods['Modifier'].str.contains('*Roasted Corn Grits', na=False)
                ]['Qty'].sum() if not interval_mods.empty else 0,

                'Pots': interval_mods[
                    interval_mods['Modifier'].str.contains('*Zea Potatoes', na=False)
                ]['Qty'].sum() if not interval_mods.empty else 0
            }

            # Add row
            row_data = {
                'Service': service,
                'Interval': interval,
                **counts,
                'Total': sum(counts.values())
            }
            report_data.append(row_data)

    # Create DataFrame and sort by service and interval
    report_df = pd.DataFrame(report_data)
    if not report_df.empty:
        report_df = report_df.sort_values(['Service', 'Interval'])
        report_df = report_df.fillna(0)
        # Convert all numeric columns to integers
        numeric_cols = ['1/2 Chix', '1/2 Ribs', 'Full Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total']
        report_df[numeric_cols] = report_df[numeric_cols].astype(int)

    return report_df