import streamlit as st
import pandas as pd
import utils
from PIL import Image

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
if 'report_data' not in st.session_state:
    st.session_state.report_data = {}
if 'interval' not in st.session_state:
    st.session_state.interval = '1 hour'

# Sidebar
st.sidebar.title('Data Upload')

# File upload section
items_file = st.sidebar.file_uploader("Upload Items CSV", type=['csv'])
modifiers_file = st.sidebar.file_uploader("Upload Modifiers CSV", type=['csv'])

# Time interval filter - put this before data processing
interval = st.sidebar.radio(
    'Time Interval',
    options=['1 hour', '30 minutes'],
    horizontal=True,
    key='interval'
)

# Load data when files are uploaded
if items_file and modifiers_file:
    new_items_df, new_modifiers_df = utils.load_data(items_file, modifiers_file)
    if new_items_df is not None and new_modifiers_df is not None:
        # Merge new data with existing data
        if st.session_state.items_df is not None:
            existing_dates = set(st.session_state.items_df['Order Date'].dt.date)
            new_dates = set(new_items_df['Order Date'].dt.date)

            # For dates in new data, update or add to existing data
            for date in new_dates:
                date_items = new_items_df[new_items_df['Order Date'].dt.date == date]
                date_modifiers = new_modifiers_df[new_modifiers_df['Order Date'].dt.date == date]

                # Generate report data for this date
                interval_minutes = 30 if interval == '30 minutes' else 60
                date_report = utils.generate_report_data(date_items, date_modifiers, interval_minutes)
                st.session_state.report_data[date] = date_report

            # Update the main dataframes
            all_items = pd.concat([
                st.session_state.items_df[~st.session_state.items_df['Order Date'].dt.date.isin(new_dates)],
                new_items_df
            ])
            all_modifiers = pd.concat([
                st.session_state.modifiers_df[~st.session_state.modifiers_df['Order Date'].dt.date.isin(new_dates)],
                new_modifiers_df
            ])

            st.session_state.items_df = all_items
            st.session_state.modifiers_df = all_modifiers
        else:
            # First time loading data
            st.session_state.items_df = new_items_df
            st.session_state.modifiers_df = new_modifiers_df

            # Calculate initial report data for all dates
            for date in new_items_df['Order Date'].dt.date.unique():
                date_items = new_items_df[new_items_df['Order Date'].dt.date == date]
                date_modifiers = new_modifiers_df[new_modifiers_df['Order Date'].dt.date == date]
                interval_minutes = 30 if interval == '30 minutes' else 60
                date_report = utils.generate_report_data(date_items, date_modifiers, interval_minutes)
                st.session_state.report_data[date] = date_report

        st.sidebar.success('Files uploaded successfully!')

# Load sample data if no data is loaded
if st.session_state.items_df is None:
    st.session_state.items_df, st.session_state.modifiers_df = utils.load_data(
        'attached_assets/ItemSelectionDetails.csv',
        'attached_assets/ModifiersSelectionDetails.csv'
    )
    # Calculate initial report data
    for date in st.session_state.items_df['Order Date'].dt.date.unique():
        date_items = st.session_state.items_df[st.session_state.items_df['Order Date'].dt.date == date]
        date_modifiers = st.session_state.modifiers_df[st.session_state.modifiers_df['Order Date'].dt.date == date]
        interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60 # Use session state interval
        date_report = utils.generate_report_data(date_items, date_modifiers, interval_minutes)
        st.session_state.report_data[date] = date_report

# Sidebar filters
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


# Display logo
logo = Image.open('attached_assets/image_1740704103897.png')
st.image(logo, width=150)

# Display report header
st.markdown(f'<h1 class="report-title">{selected_location}</h1>', unsafe_allow_html=True)
st.markdown(f'<h2 class="report-title">{selected_date.strftime("%m/%d/%Y")}</h2>', unsafe_allow_html=True)
st.markdown('<h3 class="report-title">Category Sales Count Report</h3>', unsafe_allow_html=True)

# Generate report data with current interval setting
if selected_date is not None:
    date_items = st.session_state.items_df[st.session_state.items_df['Order Date'].dt.date == selected_date]
    date_modifiers = st.session_state.modifiers_df[st.session_state.modifiers_df['Order Date'].dt.date == selected_date]
    interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60 #Use session state interval
    report_df = utils.generate_report_data(date_items, date_modifiers, interval_minutes)
else:
    report_df = pd.DataFrame()

# Format data for display
if not report_df.empty:
    # Ensure all numeric columns are integers
    numeric_cols = ['1/2 Chix', '1/2 Ribs', 'Full Ribs', '6oz Mod', '8oz Mod', 'Corn', 'Grits', 'Pots', 'Total']
    report_df[numeric_cols] = report_df[numeric_cols].fillna(0).astype(int)

    # Add service totals
    service_totals = []
    for service in ['Lunch', 'Dinner']:
        service_data = report_df[report_df['Service'] == service]
        if not service_data.empty:
            service_total = service_data[numeric_cols].sum()
            service_total['Service'] = f'{service} Total'
            service_total['Interval'] = ''
            service_totals.append(service_total)

    # Add grand total
    grand_total = report_df[numeric_cols].sum()
    grand_total['Service'] = 'Grand Total'
    grand_total['Interval'] = ''

    # Combine all rows
    report_df = pd.concat([
        report_df,
        pd.DataFrame(service_totals),
        pd.DataFrame([grand_total])
    ]).fillna('')

# Display the report
st.dataframe(
    report_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        'Service': st.column_config.TextColumn('Service', width='medium'),
        'Interval': st.column_config.TextColumn('Time', width='medium'),
        '1/2 Chix': st.column_config.NumberColumn('1/2 Chix', format='%d'),
        '1/2 Ribs': st.column_config.NumberColumn('1/2 Ribs', format='%d'),
        'Full Ribs': st.column_config.NumberColumn('Full Ribs', format='%d'),
        '6oz Mod': st.column_config.NumberColumn('6oz Mod', format='%d'),
        '8oz Mod': st.column_config.NumberColumn('8oz Mod', format='%d'),
        'Corn': st.column_config.NumberColumn('Corn', format='%d'),
        'Grits': st.column_config.NumberColumn('Grits', format='%d'),
        'Pots': st.column_config.NumberColumn('Pots', format='%d'),
        'Total': st.column_config.NumberColumn('Total', format='%d')
    }
)

# Clear data button
if st.sidebar.button('Clear Uploaded Data'):
    st.session_state.items_df = None
    st.session_state.modifiers_df = None
    st.session_state.report_data = {}
    st.experimental_rerun()