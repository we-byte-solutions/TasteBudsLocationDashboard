import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

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
        items_required_columns = ['Location', 'Order Date', 'Menu Item', 'Menu', 'Item Id']
        valid_items, message = validate_csv_format(items_df, items_required_columns)
        if not valid_items:
            st.error(f"Invalid items file format: {message}")
            return None, None

        modifiers_required_columns = ['Location', 'Order Date', 'Modifier']
        valid_modifiers, message = validate_csv_format(modifiers_df, modifiers_required_columns)
        if not valid_modifiers:
            st.error(f"Invalid modifiers file format: {message}")
            return None, None

        # Convert date columns to datetime
        items_df['Order Date'] = pd.to_datetime(items_df['Order Date'])

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

def calculate_category_counts(df):
    """Calculate counts for each category"""
    categories = {
        '1/2 Chix': df[df['Menu Item'].str.contains('Chicken', na=False) & 
                       (df['Menu'].str.contains('Lunch|Dinner', na=False))]['Item Id'].nunique(),
        '1/2 Ribs': df[df['Menu Item'].str.contains('Ribs', na=False) & 
                       (df['Menu'].str.contains('Lunch|Dinner', na=False))]['Item Id'].nunique(),
        '6oz Mod': df[df['Menu Item'].str.contains('6oz|6 oz', na=False)]['Item Id'].nunique(),
        '8oz Mod': df[df['Menu Item'].str.contains('8oz|8 oz', na=False)]['Item Id'].nunique(),
        'Corn': df[df['Menu Item'].str.contains('Corn', na=False)]['Item Id'].nunique(),
        'Full Ribs': df[df['Menu Item'].str.contains('Full.*Ribs|Ribs.*Full', na=False)]['Item Id'].nunique(),
        'Grits': df[df['Menu Item'].str.contains('Grits', na=False)]['Item Id'].nunique(),
        'Pots': df[df['Menu Item'].str.contains('Pot', na=False)]['Item Id'].nunique()
    }
    return categories

def generate_report_data(df, interval_minutes=60):
    """Generate report data with all required calculations"""
    if df is None:
        return pd.DataFrame()

    df = create_time_intervals(df, interval_minutes)
    df = get_service_periods(df)

    report_data = []

    for service in ['Lunch', 'Dinner']:
        service_df = df[df['Service'] == service]
        intervals = sorted(service_df['Interval'].unique())

        for interval in intervals:
            interval_df = service_df[service_df['Interval'] == interval]
            counts = calculate_category_counts(interval_df)

            row_data = {
                'Service': service,
                'Interval': interval,
                **counts,
                'Total': sum(counts.values())
            }
            report_data.append(row_data)

    return pd.DataFrame(report_data)