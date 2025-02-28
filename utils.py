import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import get_data_from_db, get_last_update_time

def load_data():
    """Load and preprocess sales data from database"""
    items_df, modifiers_df = get_data_from_db()
    last_update = get_last_update_time()
    return items_df, modifiers_df, last_update

def create_time_intervals(df, interval_minutes=60):
    """Create time intervals for the data"""
    df['Time'] = df['order_date'].dt.strftime('%H:%M')
    df['Hour'] = df['order_date'].dt.hour
    df['Minute'] = df['order_date'].dt.minute

    if interval_minutes == 30:
        df['Interval'] = df.apply(lambda x: f"{x['Hour']:02d}:{30 if x['Minute'] >= 30 else 00:02d}-{x['Hour']:02d}:{59 if x['Minute'] >= 30 else 29:02d}", axis=1)
    else:
        df['Interval'] = df.apply(lambda x: f"{x['Hour']:02d}:00-{x['Hour']:02d}:59", axis=1)

    return df

def get_service_periods(df):
    """Split data into Lunch and Dinner periods"""
    df['Service'] = df['order_date'].dt.hour.apply(
        lambda x: 'Lunch' if 6 <= x < 16 else 'Dinner'
    )
    return df

def calculate_category_counts(df):
    """Calculate counts for each category"""
    categories = {
        '1/2 Chix': df[df['menu_item'].str.contains('Chicken', na=False) & 
                       (df['menu'].str.contains('Lunch|Dinner', na=False))]['item_id'].nunique(),
        '1/2 Ribs': df[df['menu_item'].str.contains('Ribs', na=False) & 
                       (df['menu'].str.contains('Lunch|Dinner', na=False))]['item_id'].nunique(),
        '6oz Mod': df[df['menu_item'].str.contains('6oz|6 oz', na=False)]['item_id'].nunique(),
        '8oz Mod': df[df['menu_item'].str.contains('8oz|8 oz', na=False)]['item_id'].nunique(),
        'Corn': df[df['menu_item'].str.contains('Corn', na=False)]['item_id'].nunique(),
        'Full Ribs': df[df['menu_item'].str.contains('Full.*Ribs|Ribs.*Full', na=False)]['item_id'].nunique(),
        'Grits': df[df['menu_item'].str.contains('Grits', na=False)]['item_id'].nunique(),
        'Pots': df[df['menu_item'].str.contains('Pot', na=False)]['item_id'].nunique()
    }
    return categories

def generate_report_data(df, interval_minutes=60):
    """Generate report data with all required calculations"""
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