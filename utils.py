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
    if items_df is None or items_df.empty:
        return pd.DataFrame()

    # Filter out void items and ensure string columns
    items_df = items_df.copy()
    items_df['Void?'] = items_df['Void?'].fillna('false').astype(str).str.lower()
    items_df = items_df[items_df['Void?'] != 'true']

    if modifiers_df is not None and not modifiers_df.empty:
        modifiers_df = modifiers_df.copy()
        modifiers_df['Void?'] = modifiers_df['Void?'].fillna('false').astype(str).str.lower()
        modifiers_df = modifiers_df[modifiers_df['Void?'] != 'true']

    # Ensure string columns for pattern matching
    items_df['Menu Item'] = items_df['Menu Item'].fillna('').astype(str)
    if modifiers_df is not None:
        modifiers_df['Modifier'] = modifiers_df['Modifier'].fillna('').astype(str)
        modifiers_df['Parent Menu Selection'] = modifiers_df['Parent Menu Selection'].fillna('').astype(str)

    report_data = []

    # Group data by date
    dates = sorted(items_df['Order Date'].dt.date.unique())

    for date in dates:
        # Filter data for current date
        date_items = items_df[items_df['Order Date'].dt.date == date]
        date_mods = modifiers_df[modifiers_df['Order Date'].dt.date == date] if modifiers_df is not None else pd.DataFrame()

        # Process each service period
        for service in ['Lunch', 'Dinner']:
            # Set service hours
            service_start = 6 if service == 'Lunch' else 16
            service_end = 16 if service == 'Lunch' else 24

            # Filter by service hours
            service_items = date_items[
                (date_items['Order Date'].dt.hour >= service_start) &
                (date_items['Order Date'].dt.hour < service_end)
            ]
            service_mods = date_mods[
                (date_mods['Order Date'].dt.hour >= service_start) &
                (date_mods['Order Date'].dt.hour < service_end)
            ] if not date_mods.empty else pd.DataFrame()

            # Process each hour
            for hour in range(service_start, service_end):
                # Get data for current hour
                hour_items = service_items[service_items['Order Date'].dt.hour == hour]
                hour_mods = service_mods[service_mods['Order Date'].dt.hour == hour] if not service_mods.empty else pd.DataFrame()

                # Process intervals
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
                    # Count chicken using White/Dark meat modifiers
                    chicken_count = len(interval_mods[
                        (interval_mods['Modifier'].str.contains('White Meat|Dark Meat', regex=True, case=False)) &
                        (interval_mods['Parent Menu Selection'].str.contains('Rotisserie Chicken', case=False))
                    ]) if not interval_mods.empty else 0

                    # Count ribs using Menu Item column
                    half_ribs = len(interval_items[
                        interval_items['Menu Item'].str.contains(r'\(4\)', regex=True, case=False)
                    ])

                    full_ribs = len(interval_items[
                        interval_items['Menu Item'].str.contains(r'\(8\)', regex=True, case=False)
                    ])

                    # Count sides from modifiers with QT pattern
                    green_beans = len(interval_mods[
                        interval_mods['Modifier'].str.contains(r'\*(?:QT )?(?:Thai )?Green Beans', regex=True, case=False)
                    ]) if not interval_mods.empty else 0

                    grits = len(interval_mods[
                        interval_mods['Modifier'].str.contains(r'\*(?:QT )?Roasted Corn Grits', regex=True, case=False)
                    ]) if not interval_mods.empty else 0

                    potatoes = len(interval_mods[
                        interval_mods['Modifier'].str.contains(r'\*(?:QT )?Zea Potatoes', regex=True, case=False)
                    ]) if not interval_mods.empty else 0

                    # Count portion modifications
                    six_oz = len(interval_mods[
                        interval_mods['Modifier'].str.contains('6oz', case=False)
                    ]) if not interval_mods.empty else 0

                    eight_oz = len(interval_mods[
                        interval_mods['Modifier'].str.contains('8oz', case=False)
                    ]) if not interval_mods.empty else 0

                    counts = {
                        '1/2 Chix': chicken_count,
                        '1/2 Ribs': half_ribs,
                        'Full Ribs': full_ribs,
                        '6oz Mod': six_oz,
                        '8oz Mod': eight_oz,
                        'Corn': green_beans,
                        'Grits': grits,
                        'Pots': potatoes
                    }

                    # Add row if there are any non-zero counts
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