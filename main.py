import streamlit as st
import pandas as pd
from datetime import datetime
import utils
from database import import_csv_to_db

# Page config
st.set_page_config(
    page_title="Sales Count Report",
    layout="wide"
)

# Load custom CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state for tracking last update
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# File uploader for new data
st.sidebar.title('Data Import')
items_file = st.sidebar.file_uploader("Upload Items CSV", type=['csv'])
modifiers_file = st.sidebar.file_uploader("Upload Modifiers CSV", type=['csv'])

if items_file and modifiers_file:
    if st.sidebar.button('Import Data'):
        with st.spinner('Importing data...'):
            # Save uploaded files temporarily
            with open('temp_items.csv', 'wb') as f:
                f.write(items_file.getvalue())
            with open('temp_modifiers.csv', 'wb') as f:
                f.write(modifiers_file.getvalue())

            # Import to database
            last_update = import_csv_to_db('temp_items.csv', 'temp_modifiers.csv')
            st.session_state.last_update = last_update
            st.success('Data imported successfully!')

# Load data
items_df, modifiers_df, last_update = utils.load_data()

# Display last update time
st.sidebar.markdown('---')
st.sidebar.write('Last data update:', last_update.strftime('%Y-%m-%d %H:%M:%S'))

# Sidebar filters
st.sidebar.title('Filters')

# Location filter
locations = items_df['location'].unique()
selected_location = st.sidebar.selectbox('Location', locations)

# Date filter
dates = items_df['order_date'].dt.date.unique()
selected_date = st.sidebar.date_input(
    'Date',
    value=dates[0],
    min_value=dates.min(),
    max_value=dates.max()
)

# Time interval filter
interval = st.sidebar.radio(
    'Time Interval',
    options=['1 hour', '30 minutes'],
    horizontal=True
)

# Filter data
filtered_df = items_df[
    (items_df['location'] == selected_location) &
    (items_df['order_date'].dt.date == selected_date)
]

# Generate report
interval_minutes = 30 if interval == '30 minutes' else 60
report_df = utils.generate_report_data(filtered_df, interval_minutes)

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