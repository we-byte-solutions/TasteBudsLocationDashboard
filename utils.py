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
    if modifiers_df is None or modifiers_df.empty:
        return pd.DataFrame()

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
                    try:
                        # Calculate category counts with escaped patterns
                        counts = {
                            # Count chicken based on White/Dark meat selections
                            '1/2 Chix': interval_mods[
                                interval_mods['Modifier'].str.contains('White Meat|Dark Meat', case=False, regex=True, na=False) &
                                interval_mods['Parent Menu Selection'].str.contains('Rotisserie Chicken', case=False, regex=True, na=False)
                            ]['Qty'].sum(),

                            # Count ribs with escaped parentheses
                            '1/2 Ribs': interval_mods[
                                interval_mods['Parent Menu Selection'].str.contains(r'\(4\) (?:Dry|Thai) Ribs', case=False, regex=True, na=False)
                            ]['Qty'].sum(),

                            'Full Ribs': interval_mods[
                                interval_mods['Parent Menu Selection'].str.contains(r'\(8\) (?:Dry|Thai) Ribs', case=False, regex=True, na=False)
                            ]['Qty'].sum(),

                            # Count sides with escaped asterisks
                            'Corn': interval_mods[
                                interval_mods['Modifier'].str.contains(r'\*(?:Thai Green Beans|\*Green Beans)', case=False, regex=True, na=False)
                            ]['Qty'].sum(),

                            'Grits': interval_mods[
                                interval_mods['Modifier'].str.contains(r'\*Roasted Corn Grits', case=False, regex=True, na=False)
                            ]['Qty'].sum(),

                            'Pots': interval_mods[
                                interval_mods['Modifier'].str.contains(r'\*Zea Potatoes', case=False, regex=True, na=False)
                            ]['Qty'].sum(),

                            # Count portion modifications
                            '6oz Mod': interval_mods[
                                interval_mods['Modifier'].str.contains('6oz', case=False, regex=False, na=False)
                            ]['Qty'].sum(),

                            '8oz Mod': interval_mods[
                                interval_mods['Modifier'].str.contains('8oz', case=False, regex=False, na=False)
                            ]['Qty'].sum()
                        }

                        # Only add rows that have non-zero totals
                        total = sum(counts.values())
                        if total > 0:
                            report_data.append({
                                'Service': service,
                                'Interval': f"{hour:02d}:{minute:02d}",
                                **counts,
                                'Total': total
                            })
                    except Exception as e:
                        st.error(f"Error processing interval {hour}:{minute}: {str(e)}")
                        continue

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