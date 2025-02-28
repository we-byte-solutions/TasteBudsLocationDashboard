import streamlit as st
import pandas as pd
from datetime import datetime
import utils

# Page config
st.set_page_config(
    page_title="Sales Count Report",
    layout="wide"
)

# Load custom CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state for data
if 'items_df' not in st.session_state:
    st.session_state.items_df = None
if 'modifiers_df' not in st.session_state:
    st.session_state.modifiers_df = None
if 'historical_items_df' not in st.session_state:
    st.session_state.historical_items_df = None
if 'historical_modifiers_df' not in st.session_state:
    st.session_state.historical_modifiers_df = None

# Sidebar
st.sidebar.title('Data Upload')

# File upload section
items_file = st.sidebar.file_uploader("Upload Items CSV", type=['csv'])
modifiers_file = st.sidebar.file_uploader("Upload Modifiers CSV", type=['csv'])

# Load data when files are uploaded
if items_file and modifiers_file:
    new_items_df, new_modifiers_df = utils.load_data(items_file, modifiers_file)
    if new_items_df is not None and new_modifiers_df is not None:
        # Append new data to historical data
        if st.session_state.historical_items_df is not None:
            st.session_state.historical_items_df = pd.concat([st.session_state.historical_items_df, new_items_df])
            st.session_state.historical_modifiers_df = pd.concat([st.session_state.historical_modifiers_df, new_modifiers_df])
        else:
            st.session_state.historical_items_df = new_items_df
            st.session_state.historical_modifiers_df = new_modifiers_df

        # Update current data
        st.session_state.items_df = st.session_state.historical_items_df
        st.session_state.modifiers_df = st.session_state.historical_modifiers_df

        st.sidebar.success('Files uploaded successfully! Historical data updated.')

# If no data is loaded, use sample data
if st.session_state.items_df is None:
    st.session_state.items_df, st.session_state.modifiers_df = utils.load_data(
        'attached_assets/ItemSelectionDetails.csv',
        'attached_assets/ModifiersSelectionDetails.csv'
    )
    st.session_state.historical_items_df = st.session_state.items_df
    st.session_state.historical_modifiers_df = st.session_state.modifiers_df

# Clear historical data button
if st.sidebar.button('Clear Historical Data'):
    st.session_state.historical_items_df = None
    st.session_state.historical_modifiers_df = None
    st.session_state.items_df = None
    st.session_state.modifiers_df = None
    st.experimental_rerun()

# Filters section
st.sidebar.title('Filters')

# Location filter
locations = st.session_state.items_df['Location'].unique()
selected_location = st.sidebar.selectbox('Location', locations)

# Date filter
dates = sorted(st.session_state.items_df['Order Date'].dt.date.unique())
selected_date = st.sidebar.date_input(
    'Date',
    value=dates[0],
    min_value=dates[0],
    max_value=dates[-1]
)

# Time interval filter
interval = st.sidebar.radio(
    'Time Interval',
    options=['1 hour', '30 minutes'],
    horizontal=True
)

# Filter data
filtered_df = st.session_state.items_df[
    (st.session_state.items_df['Location'] == selected_location) &
    (st.session_state.items_df['Order Date'].dt.date == selected_date)
]

# Generate report
interval_minutes = 30 if interval == '30 minutes' else 60
report_df = utils.generate_report_data(filtered_df, interval_minutes)

# Display logo
st.markdown('<div class="logo-container"><img src="attached_assets/image_1740704103897.png" alt="Logo"></div>', unsafe_allow_html=True)

# Display report header
st.markdown(f'<h1 class="report-title">{selected_location}</h1>', unsafe_allow_html=True)
st.markdown(f'<h2 class="report-title">{selected_date.strftime("%m/%d/%Y")}</h2>', unsafe_allow_html=True)
st.markdown('<h3 class="report-title">Category Sales Count Report</h3>', unsafe_allow_html=True)

# Create the report table
report_table = pd.DataFrame(columns=[
    'Service', 'Interval', '1/2 Chix', '1/2 Ribs', '6oz Mod', '8oz Mod',
    'Corn', 'Full Ribs', 'Grits', 'Pots', 'Total'
])

# Add data to report table
for service in ['Lunch', 'Dinner']:
    service_data = report_df[report_df['Service'] == service]

    # Add service rows
    report_table = pd.concat([report_table, service_data])

    # Add service total
    service_total = service_data.sum(numeric_only=True)
    service_total['Service'] = f'{service} Total'
    service_total['Interval'] = ''
    report_table = pd.concat([report_table, pd.DataFrame([service_total])])

# Add grand total
grand_total = report_df.sum(numeric_only=True)
grand_total['Service'] = 'Total'
grand_total['Interval'] = ''
report_table = pd.concat([report_table, pd.DataFrame([grand_total])])

# Display the report
st.dataframe(
    report_table,
    hide_index=True,
    use_container_width=True,
    column_config={
        'Service': st.column_config.TextColumn('Service', width='medium'),
        'Interval': st.column_config.TextColumn('Time', width='medium'),
        '1/2 Chix': st.column_config.NumberColumn('1/2 Chix', format='%d'),
        '1/2 Ribs': st.column_config.NumberColumn('1/2 Ribs', format='%d'),
        '6oz Mod': st.column_config.NumberColumn('6oz Mod', format='%d'),
        '8oz Mod': st.column_config.NumberColumn('8oz Mod', format='%d'),
        'Corn': st.column_config.NumberColumn('Corn', format='%d'),
        'Full Ribs': st.column_config.NumberColumn('Full Ribs', format='%d'),
        'Grits': st.column_config.NumberColumn('Grits', format='%d'),
        'Pots': st.column_config.NumberColumn('Pots', format='%d'),
        'Total': st.column_config.NumberColumn('Total', format='%d'),
    }
)