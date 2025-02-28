import pandas as pd
import numpy as np 
from datetime import datetime, timedelta
import streamlit as st
import openpyxl

def load_category_mappings():
    """Load category mappings from Excel file"""
    try:
        workbook = openpyxl.load_workbook('attached_assets/Categories Current.xlsx')
        sheet_names = workbook.sheetnames

        # Read the workbook using pandas
        items_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=sheet_names[0])
        modifiers_df = pd.read_excel('attached_assets/Categories Current.xlsx', sheet_name=sheet_names[1])

        # Convert mappings to dictionaries for easier lookup
        items_dict = dict(zip(items_df.iloc[:, 0], items_df.iloc[:, 1]))  # First two columns
        modifiers_dict = dict(zip(modifiers_df.iloc[:, 0], modifiers_df.iloc[:, 1]))  # First two columns

        return items_dict, modifiers_dict
    except Exception as e:
        st.error(f"Error loading category mappings: {str(e)}")
        return {}, {}

def validate_csv_format(df, expected_columns):
    """Validate if uploaded CSV has required columns"""
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    return True, "Valid format"

def load_data(items_file, modifiers_file):
    """Load and preprocess sales data from CSV files"""
    try:
        items_df = pd.read_csv(items_file)
        modifiers_df = pd.read_csv(modifiers_file)

        # Validate required columns
        items_required_columns = ['Location', 'Order Date', 'Menu Item', 'Menu', 'Item Selection Id', 'Qty']
        valid_items, message = validate_csv_format(items_df, items_required_columns)
        if not valid_items:
            st.error(f"Invalid items file format: {message}")
            return None, None

        modifiers_required_columns = ['Location', 'Order Date', 'Modifier', 'Qty']
        valid_modifiers, message = validate_csv_format(modifiers_df, modifiers_required_columns)
        if not valid_modifiers:
            st.error(f"Invalid modifiers file format: {message}")
            return None, None

        # Convert date columns to datetime
        items_df['Order Date'] = pd.to_datetime(items_df['Order Date'])
        modifiers_df['Order Date'] = pd.to_datetime(modifiers_df['Order Date'])

        return items_df, modifiers_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def create_time_intervals(df, interval_minutes=60):
    """Create time intervals for the data"""
    df['Time'] = df['Order Date'].dt.strftime('%H:%M')
    df['Hour'] = df['Order Date'].dt.hour
    df['Minute'] = df['Order Date'].dt.minute

    if interval_minutes == 30:
        df['Interval'] = df.apply(lambda x: f"{x['Hour']:02d}:{30 if x['Minute'] >= 30 else 00:02d}-{x['Hour']:02d}:{59 if x['Minute'] >= 30 else 29:02d}", axis=1)
    else:
        df['Interval'] = df.apply(lambda x: f"{x['Hour']:02d}:00-{x['Hour']:02d}:59", axis=1)

    return df

def get_service_periods(df):
    """Split data into Lunch and Dinner periods"""
    df['Service'] = df['Order Date'].dt.hour.apply(
        lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner'
    )
    return df

def calculate_category_counts(items_df, modifiers_df=None):
    """Calculate category counts using Qty and mappings from Excel"""
    # Load category mappings
    items_mapping, modifiers_mapping = load_category_mappings()

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

    # Process items
    if not items_df.empty:
        for item_name, group in items_df.groupby('Menu Item'):
            if item_name in items_mapping:
                category = items_mapping[item_name]
                if category in categories:
                    categories[category] += group['Qty'].sum()

    # Process modifiers
    if modifiers_df is not None and not modifiers_df.empty:
        for modifier_name, group in modifiers_df.groupby('Modifier'):
            if modifier_name in modifiers_mapping:
                category = modifiers_mapping[modifier_name]
                if category in categories:
                    categories[category] += group['Qty'].sum()

    return categories

def generate_report_data(items_df, modifiers_df=None, interval_minutes=60):
    """Generate report data with all required calculations"""
    if items_df is None:
        return pd.DataFrame()

    items_df = create_time_intervals(items_df, interval_minutes)
    items_df = get_service_periods(items_df)

    if modifiers_df is not None:
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

            row_data = {
                'Service': service,
                'Interval': interval,
                **counts,
                'Total': sum(counts.values())
            }
            report_data.append(row_data)

    return pd.DataFrame(report_data)