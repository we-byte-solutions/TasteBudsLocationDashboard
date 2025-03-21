import pandas as pd
import streamlit as st

def load_data(items_file, modifiers_file):
    """Load and preprocess sales data from CSV files"""
    try:
        # Read CSV files
        items_df = pd.read_csv(items_file)
        modifiers_df = pd.read_csv(modifiers_file)

        # Debug print column names
        st.write("Items columns:", items_df.columns.tolist())
        st.write("Modifiers columns:", modifiers_df.columns.tolist())
        st.write("Sample items data:", items_df.head())
        st.write("Sample modifiers data:", modifiers_df.head())

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
        st.error("No items data available")
        return pd.DataFrame()

    st.write("Processing data with:", len(items_df), "items and", 
             len(modifiers_df) if modifiers_df is not None else 0, "modifiers")

    report_data = []

    # Add hour and service columns
    items_df = items_df.copy()
    items_df['Hour'] = items_df['Order Date'].dt.hour
    items_df['Service'] = items_df['Hour'].apply(lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner')

    if modifiers_df is not None and not modifiers_df.empty:
        modifiers_df = modifiers_df.copy()
        modifiers_df['Hour'] = modifiers_df['Order Date'].dt.hour
        modifiers_df['Service'] = modifiers_df['Hour'].apply(lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner')

    # Process each service period
    for service in ['Lunch', 'Dinner']:
        st.write(f"Processing {service} service")

        service_items = items_df[items_df['Service'] == service]
        service_mods = modifiers_df[modifiers_df['Service'] == service] if modifiers_df is not None else pd.DataFrame()

        if service_items.empty and service_mods.empty:
            st.write(f"No data for {service}")
            continue

        # Get unique hours for this service
        hours = sorted(set(service_items['Hour'].unique()) | 
                      set(service_mods['Hour'].unique() if not service_mods.empty else []))

        st.write(f"Hours for {service}:", hours)

        for hour in hours:
            # Get data for this hour
            hour_items = service_items[service_items['Hour'] == hour]
            hour_mods = service_mods[service_mods['Hour'] == hour] if not service_mods.empty else pd.DataFrame()

            # Create intervals
            minutes = [0] if interval_minutes == 60 else [0, 30]

            for minute in minutes:
                # Filter data for current interval
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

                # Calculate counts
                counts = {
                    '1/2 Chix': interval_items[
                        interval_items['Parent Menu Selection'].str.contains('Rotisserie Chicken', case=False, na=False)
                    ]['Qty'].sum(),

                    '1/2 Ribs': interval_items[
                        interval_items['Parent Menu Selection'].str.contains(r'\(4\) (?:Dry|Thai) Ribs', case=False, na=False, regex=True)
                    ]['Qty'].sum(),

                    'Full Ribs': interval_items[
                        interval_items['Parent Menu Selection'].str.contains(r'\(8\) (?:Dry|Thai) Ribs', case=False, na=False, regex=True)
                    ]['Qty'].sum(),

                    '6oz Mod': interval_mods[
                        interval_mods['Modifier'].str.contains('6oz', case=False, na=False)
                    ]['Qty'].sum() if not interval_mods.empty else 0,

                    '8oz Mod': interval_mods[
                        interval_mods['Modifier'].str.contains('8oz', case=False, na=False)
                    ]['Qty'].sum() if not interval_mods.empty else 0,

                    'Corn': interval_mods[
                        interval_mods['Modifier'].str.contains('Green Beans', case=False, na=False)
                    ]['Qty'].sum() if not interval_mods.empty else 0,

                    'Grits': interval_mods[
                        interval_mods['Modifier'].str.contains('Roasted Corn Grits', case=False, na=False)
                    ]['Qty'].sum() if not interval_mods.empty else 0,

                    'Pots': interval_mods[
                        interval_mods['Modifier'].str.contains('Zea Potatoes', case=False, na=False)
                    ]['Qty'].sum() if not interval_mods.empty else 0
                }

                st.write(f"Counts for {service} {hour:02d}:{minute:02d}:", counts)

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
        st.error("No report data generated")
        return pd.DataFrame()

    report_df = pd.DataFrame(report_data)
    report_df = report_df.sort_values(['Service', 'Interval'])
    report_df = report_df.fillna(0)

    # Convert all numeric columns to integers
    numeric_cols = ['1/2 Chix', '1/2 Ribs', 'Full Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total']
    report_df[numeric_cols] = report_df[numeric_cols].astype(int)

    st.write("Final report shape:", report_df.shape)
    return report_df