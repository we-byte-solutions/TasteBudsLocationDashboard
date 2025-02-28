import pandas as pd
import numpy as np 
from datetime import datetime, timedelta
import streamlit as st
import openpyxl

def load_category_mappings():
    """Load category mappings from Excel file"""
    try:
        # Read both sheets from Excel file
        items_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=0)
        modifiers_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=1)

        # Print debug information
        st.sidebar.write("Debug - Excel Sheets:")
        st.sidebar.write("Items sheet columns:", items_df.columns.tolist())
        st.sidebar.write("Sample items data:", items_df.head())
        st.sidebar.write("Modifiers sheet columns:", modifiers_df.columns.tolist())
        st.sidebar.write("Sample modifiers data:", modifiers_df.head())

        # Create mappings from the first two columns
        items_dict = dict(zip(items_df.iloc[:, 0], items_df.iloc[:, 1]))
        modifiers_dict = dict(zip(modifiers_df.iloc[:, 0], modifiers_df.iloc[:, 1]))

        return items_dict, modifiers_dict
    except Exception as e:
        st.error(f"Error loading category mappings: {str(e)}")
        return {}, {}

def load_data(items_file, modifiers_file):
    """Load and preprocess sales data from CSV files"""
    try:
        items_df = pd.read_csv(items_file)
        modifiers_df = pd.read_csv(modifiers_file)

        # Convert date columns to datetime
        items_df['Order Date'] = pd.to_datetime(items_df['Order Date'])
        modifiers_df['Order Date'] = pd.to_datetime(modifiers_df['Order Date'])

        # Convert Qty columns to numeric
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
    """Calculate category counts using Qty values"""
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

    # Debug current data
    st.sidebar.write("Debug - Input Data:")
    st.sidebar.write("Items shape:", items_df.shape if items_df is not None else "None")
    st.sidebar.write("Modifiers shape:", modifiers_df.shape if modifiers_df is not None else "None")

    # Load category mappings
    items_mapping, modifiers_mapping = load_category_mappings()

    # Process items
    if not items_df.empty:
        for item_name, qty in zip(items_df['Menu Item'], items_df['Qty']):
            item_name = str(item_name).strip()
            if item_name in items_mapping:
                category = items_mapping[item_name]
                if category in categories:
                    categories[category] += float(qty)

    # Process modifiers
    if modifiers_df is not None and not modifiers_df.empty:
        for modifier_name, qty in zip(modifiers_df['Modifier'], modifiers_df['Qty']):
            modifier_name = str(modifier_name).strip()
            if modifier_name in modifiers_mapping:
                category = modifiers_mapping[modifier_name]
                if category in categories:
                    categories[category] += float(qty)

    # Debug final counts
    st.sidebar.write("Debug - Category Counts:", categories)

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