import streamlit as st
import pandas as pd
import utils
from PIL import Image

# Initialize database
utils.init_db()

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

# Load available locations and dates from database
db_locations, db_dates = utils.get_available_locations_and_dates()

# Initialize locations and selected_location if not in session state
if 'locations' not in st.session_state:
    st.session_state.locations = db_locations
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = db_locations[0] if db_locations else None

# Sidebar filters section
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
    st.sidebar.error("No locations available")
    selected_location = None

# Date filter - Use dates from database if no uploaded data
dates = sorted(set(db_dates))
if st.session_state.items_df is not None:
    dates = sorted(set(dates + list(st.session_state.items_df['Order Date'].dt.date.unique())))

if dates:
    selected_date = st.sidebar.date_input(
        'Date',
        value=dates[-1],  # Default to most recent date
        min_value=dates[0],
        max_value=dates[-1]
    )
else:
    st.sidebar.error("No dates available")
    selected_date = None

# Time interval filter with default value
st.sidebar.radio(
    'Time Interval',
    options=['1 hour', '30 minutes'],
    horizontal=True,
    key='interval',
    index=0  # Default to '1 hour'
)

# Data upload section
st.sidebar.title('Data Upload')

# Clear data button at the top of sidebar
if st.sidebar.button('Clear Uploaded Data', type='primary', use_container_width=True):
    st.session_state.items_df = None
    st.session_state.modifiers_df = None
    st.rerun()

# File upload section
items_file = st.sidebar.file_uploader("Upload Items CSV", type=['csv'])
modifiers_file = st.sidebar.file_uploader("Upload Modifiers CSV", type=['csv'])

# Load data when files are uploaded
if items_file and modifiers_file:
    try:
        # Load new data
        new_items_df, new_modifiers_df = utils.load_data(items_file, modifiers_file)

        if new_items_df is not None and new_modifiers_df is not None:
            # Display data info
            st.sidebar.write(f"Items rows: {len(new_items_df)}")
            st.sidebar.write(f"Modifiers rows: {len(new_modifiers_df)}")

            # Store uploaded data
            st.session_state.items_df = new_items_df
            st.session_state.modifiers_df = new_modifiers_df

            # Get new locations from uploaded data
            new_locations = sorted(new_items_df['Location'].unique())

            # Update locations list while preserving historical locations
            st.session_state.locations = sorted(set(db_locations + new_locations))

            if st.session_state.selected_location not in st.session_state.locations:
                st.session_state.selected_location = st.session_state.locations[0] if st.session_state.locations else None

            # Generate and save report data for new dates
            interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60
            new_dates = set(new_items_df['Order Date'].dt.date)

            for date in new_dates:
                # Filter data for date and each location
                for location in new_locations:
                    date_items = new_items_df[
                        (new_items_df['Order Date'].dt.date == date) &
                        (new_items_df['Location'] == location)
                    ]
                    date_mods = new_modifiers_df[
                        (new_modifiers_df['Order Date'].dt.date == date) &
                        (new_modifiers_df['Location'] == location)
                    ]

                    # Generate and save report data
                    report_df = utils.generate_report_data(date_items, date_mods, interval_minutes)
                    if not report_df.empty:
                        utils.save_report_data(date, location, report_df)

            st.sidebar.success('Files uploaded and processed successfully!')
    except Exception as e:
        st.sidebar.error(f'Error processing files: {str(e)}')

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

# Get report data for selected date and location
if selected_date is not None and selected_location is not None:
    # Get report data with selected interval
    interval_minutes = 30 if st.session_state.interval == '30 minutes' else 60
    report_df = utils.get_report_data(selected_date, selected_location, interval_minutes)
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