import pandas as pd
import numpy as np 
from datetime import datetime, timedelta
import streamlit as st
import openpyxl

def load_category_mappings():
    """Load category mappings from Excel file"""
    try:
        # Read the Excel file
        items_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=0)
        modifiers_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=1)

        # Debug information
        st.sidebar.write("Items Mapping from Excel:")
        st.sidebar.write(items_df.head())

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

        # Debug the mappings
        st.sidebar.write("Debug - Mapped Categories:")
        st.sidebar.write("Items mappings sample:", dict(list(items_mapping.items())[:5]))
        st.sidebar.write("Modifiers mappings sample:", dict(list(modifiers_mapping.items())[:5]))

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

        # Convert Qty to numeric, replacing non-numeric values with 0
        items_df['Qty'] = pd.to_numeric(items_df['Qty'], errors='coerce').fillna(0)
        modifiers_df['Qty'] = pd.to_numeric(modifiers_df['Qty'], errors='coerce').fillna(0)

        # Debug data
        st.sidebar.write("Sample Menu Items and Quantities:")
        st.sidebar.write(items_df[['Menu Item', 'Qty']].head())

        return items_df, modifiers_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def create_time_intervals(df, interval_minutes=60):
    """Create time intervals for the data"""
    df['Hour'] = df['Order Date'].dt.hour
    df['Minute'] = df['Order Date'].dt.minute

    if interval_minutes == 30:
        df['Interval'] = df.apply(
            lambda x: f"{x['Hour']:02d}:{30 if x['Minute'] >= 30 else 00:02d}-{x['Hour']:02d}:{59 if x['Minute'] >= 30 else 29:02d}",
            axis=1
        )
    else:
        df['Interval'] = df.apply(
            lambda x: f"{x['Hour']:02d}:00-{x['Hour']:02d}:59",
            axis=1
        )
    return df

def get_service_periods(df):
    """Split data into Lunch and Dinner periods"""
    df['Service'] = df['Order Date'].dt.hour.apply(
        lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner'
    )
    return df

def calculate_category_counts(items_df, modifiers_df=None):
    """Calculate category counts using Qty values directly from CSV data"""
    categories = {
        '1/2 Chix': 0,
        '1/2 Ribs': 0,
        '6oz Mod': 0,
        '8oz Mod': 0,
        'Corn': 0,
        'Full Ribs': 0,
        'Grits': 0,
        'Pots': 0
    }

    # Process items from ItemSelectionDetails
    if not items_df.empty:
        grouped_items = items_df.groupby('Menu Item')['Qty'].sum()
        for menu_item, total_qty in grouped_items.items():
            menu_item = str(menu_item).strip()

            # Count based on menu item names
            if '1/2 Chicken' in menu_item:
                categories['1/2 Chix'] += total_qty
            elif 'Dry Ribs' in menu_item or 'Thai Ribs' in menu_item:
                if '(8)' in menu_item:
                    categories['Full Ribs'] += total_qty
                elif '(4)' in menu_item:
                    categories['1/2 Ribs'] += total_qty

    # Process modifiers from ModifiersSelectionDetails
    if modifiers_df is not None and not modifiers_df.empty:
        grouped_modifiers = modifiers_df.groupby('Modifier')['Qty'].sum()
        for modifier, total_qty in grouped_modifiers.items():
            modifier = str(modifier).strip()

            # Count based on modifier names
            if '*Roasted Corn Grits' in modifier:
                categories['Grits'] += total_qty
            elif '6oz' in modifier:
                categories['6oz Mod'] += total_qty
            elif '8oz' in modifier:
                categories['8oz Mod'] += total_qty
            elif 'Corn' in modifier:
                categories['Corn'] += total_qty
            elif '*Potatoes' in modifier or 'Pots' in modifier:
                categories['Pots'] += total_qty

    # Convert all counts to integers
    return {k: int(v) for k, v in categories.items()}

def generate_report_data(items_df, modifiers_df=None, interval_minutes=60):
    """Generate report data with all required calculations"""
    if items_df is None or items_df.empty:
        return pd.DataFrame()

    # Create time intervals and service periods
    items_df = create_time_intervals(items_df, interval_minutes)
    items_df = get_service_periods(items_df)

    if modifiers_df is not None and not modifiers_df.empty:
        modifiers_df = create_time_intervals(modifiers_df, interval_minutes)
        modifiers_df = get_service_periods(modifiers_df)

    report_data = []
    for service in ['Lunch', 'Dinner']:
        service_items_df = items_df[items_df['Service'] == service]
        service_modifiers_df = modifiers_df[modifiers_df['Service'] == service] if modifiers_df is not None else None

        intervals = sorted(service_items_df['Interval'].unique())
        for interval in intervals:
            interval_items_df = service_items_df[service_items_df['Interval'] == interval]
            interval_modifiers_df = service_modifiers_df[service_modifiers_df['Interval'] == interval] if service_modifiers_df is not None else None

            counts = calculate_category_counts(interval_items_df, interval_modifiers_df)
            total = sum(counts.values())

            row_data = {
                'Service': service,
                'Interval': interval,
                **counts,
                'Total': total
            }
            report_data.append(row_data)

    return pd.DataFrame(report_data)