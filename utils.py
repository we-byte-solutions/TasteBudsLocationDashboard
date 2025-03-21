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
    """Generate report data"""
    if items_df is None or items_df.empty:
        return pd.DataFrame()

    report_data = []

    # Process each service period
    for service in ['Lunch', 'Dinner']:
        # Define service hours
        start_hour = 6 if service == 'Lunch' else 16
        end_hour = 16 if service == 'Lunch' else 24

        # Filter data for service period
        service_items = items_df[
            (items_df['Order Date'].dt.hour >= start_hour) &
            (items_df['Order Date'].dt.hour < end_hour)
        ]

        service_mods = modifiers_df[
            (modifiers_df['Order Date'].dt.hour >= start_hour) &
            (modifiers_df['Order Date'].dt.hour < end_hour)
        ] if modifiers_df is not None else pd.DataFrame()

        # Process each hour
        for hour in range(start_hour, end_hour):
            # Create intervals
            intervals = [0] if interval_minutes == 60 else [0, 30]

            for minute in intervals:
                # Filter data for interval
                hour_mask = service_items['Order Date'].dt.hour == hour

                if interval_minutes == 30:
                    minute_mask = (
                        (service_items['Order Date'].dt.minute >= minute) &
                        (service_items['Order Date'].dt.minute < minute + 30)
                    )
                    interval_items = service_items[hour_mask & minute_mask]

                    if not service_mods.empty:
                        mod_minute_mask = (
                            (service_mods['Order Date'].dt.minute >= minute) &
                            (service_mods['Order Date'].dt.minute < minute + 30)
                        )
                        interval_mods = service_mods[hour_mask & mod_minute_mask]
                    else:
                        interval_mods = pd.DataFrame()
                else:
                    interval_items = service_items[hour_mask]
                    interval_mods = service_mods[service_mods['Order Date'].dt.hour == hour] if not service_mods.empty else pd.DataFrame()

                # Calculate counts
                counts = {
                    '1/2 Chix': interval_items[interval_items['Item'].str.contains('Rotisserie Chicken', na=False)]['Qty'].sum(),
                    '1/2 Ribs': interval_items[interval_items['Item'].str.contains(r'\(4\) (Dry|Thai) Ribs', na=False, regex=True)]['Qty'].sum(),
                    'Full Ribs': interval_items[interval_items['Item'].str.contains(r'\(8\) (Dry|Thai) Ribs', na=False, regex=True)]['Qty'].sum(),
                    'Corn': interval_mods[interval_mods['Modifier'].str.contains('Thai Green Beans|Green Beans', na=False, regex=True)]['Qty'].sum() if not interval_mods.empty else 0,
                    'Grits': interval_mods[interval_mods['Modifier'].str.contains('Roasted Corn Grits', na=False)]['Qty'].sum() if not interval_mods.empty else 0,
                    'Pots': interval_mods[interval_mods['Modifier'].str.contains('Zea Potatoes', na=False)]['Qty'].sum() if not interval_mods.empty else 0,
                    '6oz Mod': interval_mods[interval_mods['Modifier'].str.contains('6oz', na=False)]['Qty'].sum() if not interval_mods.empty else 0,
                    '8oz Mod': interval_mods[interval_mods['Modifier'].str.contains('8oz', na=False)]['Qty'].sum() if not interval_mods.empty else 0
                }

                # Add row if there are any counts
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
        return pd.DataFrame(columns=['Service', 'Interval', '1/2 Chix', '1/2 Ribs', 'Full Ribs', 
                                   '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total'])

    report_df = pd.DataFrame(report_data)
    report_df = report_df.sort_values(['Service', 'Interval'])
    report_df = report_df.fillna(0)

    # Convert numeric columns to integers
    numeric_cols = ['1/2 Chix', '1/2 Ribs', 'Full Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total']
    report_df[numeric_cols] = report_df[numeric_cols].astype(int)

    return report_df