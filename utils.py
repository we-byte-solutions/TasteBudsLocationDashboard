import pandas as pd
import numpy as np 
from datetime import datetime, timedelta
import streamlit as st
import openpyxl

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

        return items_df, modifiers_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def create_time_intervals(df, interval_minutes=60):
    """Create time intervals for the data"""
    df['Hour'] = df['Order Date'].dt.hour
    df['Minute'] = df['Order Date'].dt.minute

    # Create intervals based on the selected time period
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
    """Calculate category counts for a specific time interval"""
    categories = {
        '1/2 Chix': 0,
        '1/2 Ribs': 0,
        'Full Ribs': 0,
        '6oz Mod': 0,
        '8oz Mod': 0,
        'Corn': 0,
        'Grits': 0,
        'Pots': 0
    }

    # Process modifiers from ModifiersSelectionDetails
    if modifiers_df is not None and not modifiers_df.empty:
        for _, row in modifiers_df.iterrows():
            modifier = str(row['Modifier']).strip()
            menu_selection = str(row['Parent Menu Selection']).strip()
            qty = row['Qty']

            # Check ribs in parent menu selection
            if '(4) Dry Ribs' in menu_selection or '(4) Thai Ribs' in menu_selection:
                categories['1/2 Ribs'] += qty
            elif '(8) Dry Ribs' in menu_selection or '(8) Thai Ribs' in menu_selection:
                categories['Full Ribs'] += qty

            # Check modifiers
            if '*Roasted Corn Grits' in modifier:
                categories['Grits'] += qty
            elif '*Zea Potatoes' in modifier:
                categories['Pots'] += qty
            elif '*Thai Green Beans' in modifier or '*Green Beans' in modifier:
                categories['Corn'] += qty
            elif '6oz' in modifier:
                categories['6oz Mod'] += qty
            elif '8oz' in modifier:
                categories['8oz Mod'] += qty

    # Process chicken items from Parent Menu Selection
    if not items_df.empty:
        chicken_items = items_df[items_df['Parent Menu Selection'].str.contains('Rotisserie Chicken', na=False)]
        categories['1/2 Chix'] += chicken_items['Qty'].sum()

    return categories

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

        # Get intervals for this service period
        intervals = sorted(service_items_df['Interval'].unique())

        # Create service modifiers dataframe if modifiers exist
        service_modifiers_df = None
        if modifiers_df is not None and not modifiers_df.empty:
            service_modifiers_df = modifiers_df[modifiers_df['Service'] == service]

        for interval in intervals:
            # Filter items for this interval
            interval_items_df = service_items_df[service_items_df['Interval'] == interval]

            # Filter modifiers for this interval if they exist
            interval_modifiers_df = None
            if service_modifiers_df is not None:
                interval_modifiers_df = service_modifiers_df[service_modifiers_df['Interval'] == interval]

            # Calculate counts
            counts = calculate_category_counts(interval_items_df, interval_modifiers_df)
            total = sum(counts.values())

            # Create row data
            row_data = {
                'Service': service,
                'Interval': interval,
                **counts,
                'Total': total
            }
            report_data.append(row_data)

    return pd.DataFrame(report_data)