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
if 'locations' not in st.session_state:
    st.session_state.locations = []
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None

# Sidebar
st.sidebar.title('Data Upload')

# File upload section
items_file = st.sidebar.file_uploader("Upload Items CSV", type=['csv'])
modifiers_file = st.sidebar.file_uploader("Upload Modifiers CSV", type=['csv'])

# Time interval filter
interval = st.sidebar.radio(
    'Time Interval',
    options=['1 hour', '30 minutes'],
    horizontal=True,
    key='interval'
)

# Load data when files are uploaded
if items_file and modifiers_file:
    try:
        new_items_df, new_modifiers_df = utils.load_data(items_file, modifiers_file)
        if new_items_df is not None and new_modifiers_df is not None:
            st.sidebar.write(f"Items rows: {len(new_items_df)}")
            st.sidebar.write(f"Modifiers rows: {len(new_modifiers_df)}")

            # Replace data for uploaded dates
            if st.session_state.items_df is not None:
                new_dates = set(new_items_df['Order Date'].dt.date)
                old_dates = set(st.session_state.items_df['Order Date'].dt.date) - new_dates

                # Keep old data for dates not in new upload
                old_items = st.session_state.items_df[st.session_state.items_df['Order Date'].dt.date.isin(old_dates)]
                old_modifiers = st.session_state.modifiers_df[st.session_state.modifiers_df['Order Date'].dt.date.isin(old_dates)]

                # Combine old and new data
                st.session_state.items_df = pd.concat([old_items, new_items_df])
                st.session_state.modifiers_df = pd.concat([old_modifiers, new_modifiers_df])
            else:
                st.session_state.items_df = new_items_df
                st.session_state.modifiers_df = new_modifiers_df

            # Update locations list
            st.session_state.locations = sorted(st.session_state.items_df['Location'].unique())
            if st.session_state.selected_location not in st.session_state.locations:
                st.session_state.selected_location = st.session_state.locations[0] if st.session_state.locations else None

            # Generate report data for new dates
            for date in new_items_df['Order Date'].dt.date.unique():
                date_items = new_items_df[new_items_df['Order Date'].dt.date == date]
                date_modifiers = new_modifiers_df[new_modifiers_df['Order Date'].dt.date == date]
                interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60
                st.session_state.report_data[date] = utils.generate_report_data(date_items, date_modifiers, interval_minutes)

            st.sidebar.success('Files uploaded and processed successfully!')
    except Exception as e:
        st.sidebar.error(f'Error processing files: {str(e)}')

# Load sample data if no data is loaded
if st.session_state.items_df is None:
    st.session_state.items_df, st.session_state.modifiers_df = utils.load_data(
        'attached_assets/ItemSelectionDetails.csv',
        'attached_assets/ModifiersSelectionDetails.csv'
    )
    # Update locations list
    st.session_state.locations = sorted(st.session_state.items_df['Location'].unique())
    st.session_state.selected_location = st.session_state.locations[0] if st.session_state.locations else None

    # Calculate initial report data
    for date in st.session_state.items_df['Order Date'].dt.date.unique():
        date_items = st.session_state.items_df[st.session_state.items_df['Order Date'].dt.date == date]
        date_modifiers = st.session_state.modifiers_df[st.session_state.modifiers_df['Order Date'].dt.date == date]
        interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60
        st.session_state.report_data[date] = utils.generate_report_data(date_items, date_modifiers, interval_minutes)

# Sidebar filters
st.sidebar.title('Filters')

# Location filter
if st.session_state.locations:
    selected_location = st.sidebar.selectbox(
        'Location',
        options=st.session_state.locations,
        index=st.session_state.locations.index(st.session_state.selected_location) if st.session_state.selected_location else 0
    )
    st.session_state.selected_location = selected_location
else:
    st.sidebar.error("No locations available in the data")
    selected_location = None

# Date filter
dates = sorted(st.session_state.items_df['Order Date'].dt.date.unique()) if st.session_state.items_df is not None else []
if dates:
    selected_date = st.sidebar.date_input(
        'Date',
        value=dates[0],
        min_value=dates[0],
        max_value=dates[-1]
    )
else:
    st.sidebar.error("No dates available in the data")
    selected_date = None

# Display logo
logo = Image.open('attached_assets/image_1740704103897.png')
st.image(logo, width=150)

# Display report header
if selected_location:
    st.markdown(f'<h1 class="report-title">{selected_location}</h1>', unsafe_allow_html=True)
else:
    st.markdown(f'<h1 class="report-title">No Location Selected</h1>', unsafe_allow_html=True)

if selected_date:
    st.markdown(f'<h2 class="report-title">{selected_date.strftime("%m/%d/%Y")}</h2>', unsafe_allow_html=True)
else:
    st.markdown(f'<h2 class="report-title">No Date Selected</h2>', unsafe_allow_html=True)


st.markdown('<h3 class="report-title">Category Sales Count Report</h3>', unsafe_allow_html=True)

# Generate report data for selected date
if selected_date is not None and selected_location is not None:
    # Filter data for selected date and location
    date_items = st.session_state.items_df[
        (st.session_state.items_df['Order Date'].dt.date == selected_date) &
        (st.session_state.items_df['Location'] == selected_location)
    ]
    date_modifiers = st.session_state.modifiers_df[
        (st.session_state.modifiers_df['Order Date'].dt.date == selected_date) &
        (st.session_state.modifiers_df['Location'] == selected_location)
    ]

    # Generate report data
    interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60
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
    height=600,
    column_config={
        'Service': st.column_config.TextColumn('Service', width='small'),
        'Interval': st.column_config.TextColumn('Time', width='small'),
        '1/2 Chix': st.column_config.NumberColumn('1/2 Chix', format='%d', width='small'),
        '1/2 Ribs': st.column_config.NumberColumn('1/2 Ribs', format='%d', width='small'),
        'Full Ribs': st.column_config.NumberColumn('Full Ribs', format='%d', width='small'),
        '6oz Mod': st.column_config.NumberColumn('6oz Mod', format='%d', width='small'),
        '8oz Mod': st.column_config.NumberColumn('8oz Mod', format='%d', width='small'),
        'Corn': st.column_config.NumberColumn('Corn', format='%d', width='small'),
        'Grits': st.column_config.NumberColumn('Grits', format='%d', width='small'),
        'Pots': st.column_config.NumberColumn('Pots', format='%d', width='small'),
        'Total': st.column_config.NumberColumn('Total', format='%d', width='small')
    }
)

# Clear data button
if st.sidebar.button('Clear Uploaded Data'):
    st.session_state.items_df = None
    st.session_state.modifiers_df = None
    st.session_state.report_data = {}
    st.session_state.locations = []
    st.session_state.selected_location = None
    st.rerun()