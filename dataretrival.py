"""
    NEED SEPERATION OF DATASETS FRO RAG BUT IT ISNT USING THE RIGHT ONE SO SEPERATE INTO DIFF CLASSES(MAYBE EXTREME)
    OR SEPERATE FUNCTIONS RATHER THAN IF STATEMENTS

- EMAILS
- WHAT REPORTS ARENT WORKING 
- TIME IN MINUTES/ SECONDS
- LINKS EMBEDDED INTO THE NAME TO BE CLICKED ON A
-  BETTER VISIUALISATION


"""


import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
import schedule
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pyodbc
import os
from sqlalchemy import create_engine,text
from sqlalchemy.exc import SQLAlchemyError
import plotly.express as px



load_dotenv()

server = os.getenv("SERVER")
database = os.getenv("DATABASE")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

# Creating connection string
conn_str = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes"

if 'night_mode' not in st.session_state:
    st.session_state.night_mode = False

def toggle_night_mode():
    st.session_state.night_mode = not st.session_state.night_mode

class SSRSReportMonitor:
    def __init__(self, conn_str):
        try:
            self.engine = create_engine(conn_str, pool_pre_ping=True)
            self.run_times = []
            print("Connection Successful")
        except SQLAlchemyError as e:
            print(f"Connection failed: {e}")
            exit(1)

    def setup_ui_theme(self):
        """Set up the UI theme based on night mode setting"""
        st.button("Toggle Mode", on_click=toggle_night_mode)
        
        if st.session_state.night_mode:
            st.markdown("""
                <style>
                .st-emotion-cache-1r4qj8v {
                    background-color: #1e1e1e;
                    color: white;
                }
                </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <style>
                .st-emotion-cache-1r4qj8v {
                    background-color: white;
                    color: black;
                }
                </style>
            """, unsafe_allow_html=True)
        
        st.write("Current mode: Night" if st.session_state.night_mode else "Current mode: Day")


    def run_query(self):
        query = text("""
        SELECT 
            el.TimeStart,
            el.TimeEnd,
            el.UserName,
            el.Status,
            el.Format,
            el.TimeProcessing,
            el.TimeRendering,
            el.TimeDataRetrieval,
            el.ItemPath AS ReportPath,
            c.Name AS ReportName,
            el.Parameters
        FROM 
            ExecutionLog3 el
        LEFT JOIN 
            Catalog c ON el.ItemPath = c.Path
        WHERE 
            el.TimeStart >= :start_time AND el.TimeStart < :end_time
        ORDER BY 
            el.TimeStart DESC
        """)
        
        current_run = datetime.now()
        self.run_times.append(current_run)
        
        end_time = current_run
        start_time = end_time - timedelta(minutes=480)
        
        with self.engine.connect() as connection:
            df = pd.read_sql(query, connection, params={
                'start_time': start_time, 
                'end_time': end_time
            })
        
        if not df.empty:
            performance_summary = {
                'run_time': current_run,
                'avg_processing_time': df['TimeProcessing'].mean(),
                'avg_rendering_time': df['TimeRendering'].mean(),
                'avg_data_retrieval_time': df['TimeDataRetrieval'].mean(),
                'condition':df['Status'],
                'total_reports': len(df)
            }
            
            return df, performance_summary
        

        return None 

    def get_distinct_report_execution(self):
        query = text("""
        WITH LatestExecutions AS (
    SELECT 
        el.ItemPath,
        el.UserName,
        el.TimeStart,
        el.Status,
        ROW_NUMBER() OVER (PARTITION BY el.ItemPath ORDER BY el.TimeStart DESC) as rn
    FROM 
        ReportServer.dbo.ExecutionLog3 el
)
-- Main query joining catalog with latest executions
SELECT 
    c.Name AS ReportName,
    c.Path,
    c.ParentID,
    c.Type,
    CASE c.Type
        WHEN 1 THEN 'Folder'
        WHEN 2 THEN 'Report'
        WHEN 3 THEN 'Resource'
        WHEN 4 THEN 'Linked Report'
        WHEN 5 THEN 'Data Source'
        WHEN 6 THEN 'Model'
        WHEN 7 THEN 'Report Part'
        WHEN 8 THEN 'Shared Dataset'
        ELSE 'Other' 
    END AS ItemType,
    c.Description,
    c.Hidden,
    c.CreatedByID,
    c.CreationDate,
    c.ModifiedByID,
    c.ModifiedDate,
    le.UserName AS LastExecutedBy,
    le.TimeStart AS LastExecutionTime,
    le.Status AS LastExecutionStatus,
    ex_count.ExecutionCount
FROM 
    ReportServer.dbo.Catalog c
LEFT JOIN 
    LatestExecutions le ON c.Path = le.ItemPath AND le.rn = 1
LEFT JOIN 
    (SELECT ItemPath, COUNT(*) AS ExecutionCount 
     FROM ReportServer.dbo.ExecutionLog3 
     GROUP BY ItemPath) ex_count ON c.Path = ex_count.ItemPath
WHERE 
    c.Type = 2  -- Type 2 means Report
ORDER BY 
    c.Name
    """)

        try:
            with self.engine.connect() as connection:
                df = pd.read_sql(query, connection)
                print(f"Retreieved {len(df)} records from distinct execution query")
                return df
        except Exception as e:
            print(f"Error in gte_dustinct_report_executiion: {e}")
            return pd.DataFrame()

    

    def save_results(self, dataframe, summary):
        # Implement your result saving logic
        # Example: save to CSV or database
        filename = f"report_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        dataframe.to_csv(filename, index=False)
        print(f"Performance Summary: {summary}")

    def schedule_runs(self):
        # Schedule runs from 4 AM to 8 AM every 30 minutes
        schedule_times = [
            "04:00", "04:30", 
            "05:00", "05:30", 
            "06:00", "06:30", 
            "07:00", "07:30"
        ]
        
        for run_time in schedule_times:
            schedule.every().day.at(run_time).do(self.run_query)

    def run_now(self):
        print("Running query immediately...")
        self.run_query()

    def start(self):
        self.schedule_runs()
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def display_overiew_section(self, dataframe, performance_summary):
                """Display the overview section"""

                st.markdown(
                        """
                        <style>
                        div[data-testid="stMetricValue"] {
                        border-left: 4px solid blue; /* Blue border on the left */
                        border: 1px solid #DDD; /* Light gray border */
                        border-radius: 5px;
                        padding: 5px 10px;
                        background-color: #f9f9f9;
                        margin: 5px 0;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                
                #Showing the summary detais
                st.subheader("Current Status")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Reports Processed", performance_summary['total_reports'])
                col2.metric("Average processing Time (s)", round(performance_summary['avg_processing_time']/1000, 2))
                col3.metric("Average Data Retrival Time (s)", round(performance_summary['avg_data_retrieval_time']/1000, 2))

                #Status counts
                status_counts = dataframe['Status'].value_counts()
                st.metric("Successful Reports", status_counts.get('rsSuccess',0))

                #Status Metrics
                status_list = [
                'rsInternalError',
                'rsInvalidDataSourceCredentialSetting',
                'rsProcessingAborted',
                'rsAccessDenied',
                'rrRenderingError',
                'rsHttpRuntimeInternalError'
                ]

                for status in status_list:
                    count = status_counts.get(status,0)
                    if count > 0:
                        st.metric(f"{status}",count)
                
                
                st.subheader("⚠️ Failed Reports")

                failed_reports = dataframe[dataframe['Status'] != 'rsSuccess']

                if not failed_reports.empty:
                    failed_reports['ReportLink'] = failed_reports['ReportPath'].apply(
                    lambda path: f"[View Report](http://rbkcprodhmrpt02/reports/report{path.replace(' ','%20')})"
                )

                    st.dataframe(failed_reports[['ReportPath', 'ReportName', 'Status', 'TimeStart']])
                    st.write("Click the report to open it:")
                    st.markdown(failed_reports[['ReportName', 'Status', 'ReportLink']].to_markdown(index=False), unsafe_allow_html=True)
                else:
                    st.success("No failed Reports")
                

                
                # st.write("Click the report to open it:")
                # st.markdown(failed_reports[['ReportName', 'Status', 'ReportLink']].to_markdown(index=False), unsafe_allow_html=True)


                
    
    # def display_detailed_section(self):
    #             st.subheader("Detailed Report Data")
    #             distinct_df = self.get_distinct_report_execution()


    #             enable_filters = st.checkbox("Enable Filtering")
    #             filtered_df = distinct_df.copy()



    #             if enable_filters:
    #                 with st.expander("Set filters"):
    #                     report_names = distinct_df['ReportName'].unique()
    #                     statuses = distinct_df['ExecutionStatus'].unique()

    #                     selected_names = st.multiselect("Select Report Name(s):", report_names, default=report_names[:5] if len(report_names) > 5 else report_names)
    #                     selected_statuses = st.multiselect("Select Status(es)", statuses, default=statuses)

    #                     try:
    #                         date_min = pd.to_datetime(distinct_df['ExecutionTime']).min().date()
    #                         date_max = pd.to_datetime(distinct_df['ExecutionTime']).max().date()
    #                         selected_dates = st.date_input("Select Start Date Range:", [date_min, date_max])

    #                         if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    #                             filtered_df = distinct_df[
    #                                 distinct_df['ReportName'].isin(selected_names) &
    #                                 distinct_df['ExecutionStatus'].isin(selected_statuses) &
    #                                 (pd.to_datetime(distinct_df['ExecutionTime']).dt.date.between(selected_dates[0], selected_dates[1]))
    #                             ]
    #                         else:
    #                              filtered_df = distinct_df[
    #                                   distinct_df['ReportName'].isin(selected_names) &
    #                                   distinct_df['ExecutionStatus'].isin(selected_statuses)
    #                              ] 
    #                     except Exception as e:
    #                          st.error(f"Error setting date fillers; {e}")
    #                          filtered_df = distinct_df[
    #                               distinct_df['ReportName'].isin(selected_names) &
    #                               distinct_df['ExecutionStatus'].isin(selected_statuses)
    #                          ]
                             
    #             st.dataframe(filtered_df)

    #             csv = filtered_df.to_csv(index=False).encode('utf-8')
    #             st.download_button(
    #                  "Download Filtered Data as CSV",
    #                  csv,
    #                  "filtered_report_data.csv",
    #                  "test/csv",
    #                  key='download-csv'
    #             )

    #             # st.dataframe(dataframe)

    #             # #Visulisation
    #             # st.subheader("Reports Processed Over Time")
    #             # dataframe['TimeGroup'] = pd.to_datetime(dataframe['TimeStart']).dt.floor('T')
    #             # counts = dataframe.groupby('TimeGroup').size().reset_index(name='Reports')
    #             # st.area_chart(counts.set_index('TimeGroup'))

    def display_detailed_section(self):
        st.subheader("Detailed Report Data")
        distinct_df = self.get_distinct_report_execution()

        # Check if distinct_df is empty
        if distinct_df.empty:
            st.error("No data available from distinct report execution query")
            return

        # Check if user status preferences exist in session state
        if 'user_status_overrides' not in st.session_state:
            st.session_state.user_status_overrides = {}

        # Function to handle status update
        def update_status(report_id, new_status):
            st.session_state.user_status_overrides[report_id] = new_status
            st.success("Status updated successfully!")

        # Function to reset all overrides
        def reset_all_overrides():
            st.session_state.user_status_overrides = {}
            st.success("All status overrides have been reset")

        # Define status colors with HTML that renders reliably in Streamlit
        GREEN_STATUS = '<span style="color:green; font-size:20px; font-weight:bold;">●</span>'
        AMBER_STATUS = '<span style="color:orange; font-size:20px; font-weight:bold;">●</span>'
        RED_STATUS = '<span style="color:red; font-size:20px; font-weight:bold;">●</span>'

        # Display status legend at the top for clarity
        st.markdown("### Status Legend")
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <div style="margin-right: 20px;">{GREEN_STATUS} <strong>Green</strong>: Success</div>
            <div style="margin-right: 20px;">{AMBER_STATUS} <strong>Amber</strong>: Warning</div>
            <div style="margin-right: 20px;">{RED_STATUS} <strong>Red</strong>: Error</div>
        </div>
        """, unsafe_allow_html=True)

        # Add initial status color column based on ExecutionStatus
        distinct_df['RAG_Status'] = distinct_df.apply(
            lambda row: 
                GREEN_STATUS if row['LastExecutionStatus'] == "rsSuccess" else 
                AMBER_STATUS,  # Amber for no info or any other status
            axis=1
        )

        # For filtering and data manipulation, use simple text codes
        distinct_df['StatusCode'] = distinct_df.apply(
            lambda row: 
                "green" if row['LastExecutionStatus'] == "rsSuccess" else 
                "amber",  # Amber for no info or any other status
            axis=1
        )

        # Add a unique ID for each report (for tracking user overrides)
        distinct_df['ReportID'] = distinct_df['Path'].apply(
            lambda x: x.replace('/', '_').replace(' ', '_') if isinstance(x, str) else f"report_{x}"
        )

        # Apply any user overrides that exist
        for report_id, status in st.session_state.user_status_overrides.items():
            if report_id in distinct_df['ReportID'].values:
                status_html = {
                    "green": GREEN_STATUS,
                    "amber": AMBER_STATUS,
                    "red": RED_STATUS
                }.get(status, AMBER_STATUS)
                
                distinct_df.loc[distinct_df['ReportID'] == report_id, 'RAG_Status'] = status_html
                distinct_df.loc[distinct_df['ReportID'] == report_id, 'StatusCode'] = status

        # Create a clickable report link column
        distinct_df['ReportLink'] = distinct_df.apply(
            lambda row: f"<a href='http://rbkcprodhmrpt02/reports/report{row['Path'].replace(' ','%20')}' target='_blank'>{row['ReportName']}</a>" 
            if isinstance(row['Path'], str) else "", 
            axis=1
        )

        enable_filters = st.checkbox("Enable Filtering")
        filtered_df = distinct_df.copy()

        if enable_filters:
            with st.expander("Set filters"):
                report_names = distinct_df['ReportName'].unique()
                statuses = [status for status in distinct_df['LastExecutionStatus'].unique() if status is not None]
                
                status_colors = {
                    "rsSuccess": "Success",
                    "rsProcessingAborted": "Processing Aborted",
                    "rsServerNotFound": "Server Not Found",
                    "rsInternalError": "Internal Error",
                    "rsInvalidDataSourceCredentialSetting": "Invalid Credentials",
                    "rsAccessDenied": "Access Denied",
                    "rrRenderingError": "Rendering Error",
                    "rsHttpRuntimeInternalError": "HTTP Runtime Error"
                }
                
                # Create simpler status filter labels
                status_display = [status_colors.get(s, s) for s in statuses]
                status_mapping = dict(zip(status_display, statuses))
                
                selected_names = st.multiselect(
                    "Select Report Name(s):", 
                    report_names, 
                    default=report_names[:5] if len(report_names) > 5 else report_names
                )
                
                selected_status_display = st.multiselect(
                    "Select Status(es)", 
                    status_display, 
                    default=status_display
                )
                
                selected_statuses = [status_mapping[s] for s in selected_status_display]

                # Add filter for visual status colors
                visual_status_options = ["Green (Success)", "Amber (Warning)", "Red (Error)"]
                visual_status_mapping = {
                    "Green (Success)": "green",
                    "Amber (Warning)": "amber",
                    "Red (Error)": "red"
                }
                
                selected_visual_statuses = st.multiselect(
                    "Filter by Visual Status:", 
                    visual_status_options,
                    default=visual_status_options
                )
                
                selected_visual_status_values = [visual_status_mapping[s] for s in selected_visual_statuses]

                try:
                    date_min = pd.to_datetime(distinct_df['LastExecutionTime']).min().date()
                    date_max = pd.to_datetime(distinct_df['LastExecutionTime']).max().date()
                    selected_dates = st.date_input("Select Date Range:", [date_min, date_max])
                    
                    # Filter by execution status, visual status, and date
                    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                        filtered_df = distinct_df[
                            distinct_df['ReportName'].isin(selected_names) &
                            distinct_df['LastExecutionStatus'].isin(selected_statuses) &
                            distinct_df['StatusCode'].isin(selected_visual_status_values) &
                            (pd.to_datetime(distinct_df['LastExecutionTime']).dt.date.between(selected_dates[0], selected_dates[1]))
                        ]
                    else:
                        filtered_df = distinct_df[
                            distinct_df['ReportName'].isin(selected_names) &
                            distinct_df['LastExecutionStatus'].isin(selected_statuses) &
                            distinct_df['StatusCode'].isin(selected_visual_status_values)
                        ]
                except Exception as e:
                    st.error(f"Error setting date filters: {e}")
                    filtered_df = distinct_df[
                        distinct_df['ReportName'].isin(selected_names) &
                        distinct_df['LastExecutionStatus'].isin(selected_statuses) &
                        distinct_df['StatusCode'].isin(selected_visual_status_values)
                    ]

        # Add status summary metrics
        total_reports = len(filtered_df)
        green_reports = filtered_df[filtered_df['StatusCode'] == 'green'].shape[0]
        amber_reports = filtered_df[filtered_df['StatusCode'] == 'amber'].shape[0]
        red_reports = filtered_df[filtered_df['StatusCode'] == 'red'].shape[0]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Reports", total_reports)
        col2.metric("Green (Success)", green_reports, f"{green_reports/total_reports:.0%}" if total_reports > 0 else "0%")
        col3.metric("Amber (Warning)", amber_reports, f"{amber_reports/total_reports:.0%}" if total_reports > 0 else "0%")
        col4.metric("Red (Error)", red_reports, f"{red_reports/total_reports:.0%}" if total_reports > 0 else "0%")

        # Add manual status override controls
        st.subheader("Change Report Status")
        
        # Report selection for status change
        if not filtered_df.empty:
            # Get list of report names and IDs
            report_options = dict(zip(filtered_df['ReportName'], filtered_df['ReportID']))
            selected_report = st.selectbox("Select Report to Change Status:", 
                                        options=list(report_options.keys()))
            selected_report_id = report_options[selected_report]
            
            # Current status display
            current_status = "amber"  # Default
            if selected_report_id in st.session_state.user_status_overrides:
                current_status = st.session_state.user_status_overrides[selected_report_id]
            else:
                current_status = filtered_df.loc[filtered_df['ReportID'] == selected_report_id, 'StatusCode'].iloc[0]
                
            # Display current status with the colored circle
            current_status_html = {
                "green": GREEN_STATUS,
                "amber": AMBER_STATUS,
                "red": RED_STATUS
            }.get(current_status, AMBER_STATUS)
            
            st.markdown(f"Current Status: {current_status_html} ({current_status.title()})", unsafe_allow_html=True)
            
            # Status selection - simplified approach
            status_options = ["green", "amber", "red"]
            status_display = {
                "green": "Green (Success)",
                "amber": "Amber (Warning)",
                "red": "Red (Error)"
            }
            
            option_index = status_options.index(current_status) if current_status in status_options else 1
            
            new_status = st.radio(
                "Select New Status:",
                options=status_options,
                format_func=lambda x: status_display[x],
                index=option_index,
                horizontal=True
            )
            
            # Button to apply the change
            if st.button("Update Status"):
                update_status(selected_report_id, new_status)
                st.experimental_rerun()  # Force a rerun to update the UI
        
        # Add a button to save status overrides to CSV
        if st.button("Save Status Overrides to CSV"):
            if st.session_state.user_status_overrides:
                override_df = pd.DataFrame([
                    {'report_id': report_id, 'status': status} 
                    for report_id, status in st.session_state.user_status_overrides.items()
                ])
                csv = override_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download Status Overrides",
                    csv,
                    "report_status_overrides.csv",
                    "text/csv",
                    key='download-overrides'
                )
            else:
                st.warning("No status overrides to save")
        
        # Option to upload previous overrides
        st.subheader("Upload Status Overrides")
        uploaded_file = st.file_uploader("Upload previously saved status overrides", type="csv")
        if uploaded_file is not None:
            try:
                override_df = pd.read_csv(uploaded_file)
                if 'report_id' in override_df.columns and 'status' in override_df.columns:
                    for _, row in override_df.iterrows():
                        st.session_state.user_status_overrides[row['report_id']] = row['status']
                    st.success(f"Successfully loaded {len(override_df)} status overrides")
                    st.experimental_rerun()  # Force a rerun to update the UI
                else:
                    st.error("CSV file does not have the expected columns: report_id, status")
            except Exception as e:
                st.error(f"Error loading overrides: {e}")
        
        # Reset all status overrides button
        if st.button("Reset All Status Overrides"):
            reset_all_overrides()
            st.experimental_rerun()  # Force a rerun to update the UI
        
        # Add CSV download option for the data
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Filtered Data as CSV",
            csv,
            "filtered_report_data.csv",
            "text/csv",
            key='download-csv'
        )
        
        # Choose which columns to display and their order
        display_cols = [
            'RAG_Status', 'ReportName', 'LastExecutionStatus', 'LastExecutionTime', 
            'LastExecutedBy', 'ExecutionCount', 'ModifiedDate', 'Description'
        ]
        
        # Check if all columns exist
        valid_cols = [col for col in display_cols if col in filtered_df.columns]
        
        # Create a DataFrame for display with HTML rendering
        display_df = filtered_df[valid_cols].copy()
        
        # Format the displayed dataframe
        if 'LastExecutionTime' in display_df.columns:
            display_df['LastExecutionTime'] = pd.to_datetime(display_df['LastExecutionTime']).dt.strftime('%Y-%m-%d %H:%M')
        if 'ModifiedDate' in display_df.columns:
            display_df['ModifiedDate'] = pd.to_datetime(display_df['ModifiedDate']).dt.strftime('%Y-%m-%d')
        
        # Display the dataframe with enhanced styling
        st.write("### Reports Status")
        
        # Apply custom CSS for better table styling
        st.markdown("""
        <style>
        .dataframe {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }
        .dataframe th, .dataframe td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .dataframe th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .dataframe tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Convert dataframe to HTML and display
        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        def save_complete_state_to_file(df, overrides, filespath="complete_report_state.csv"):
            """This will save the whole dataset to a new file"""
            complete_df = df.copy()

            if 'ReportID' in complete_df.columns:
                for report_id, status in overrides.items():
                    if report_id in complete_df['ReportID'].values:
                        complete_df.loc[complete_df['ReportID'] == report_id, 'StatusCode'] = status
                
                complete_df.to_csv(filespath, index=False)
                return True
            return False
        
        if st.button("Update Status"):
            update_status(selected_report_id, new_status)
            save_complete_state_to_file(filtered_df)

                
    def run_streamlit_app(self, dataframe, performance_summary):
        """Run the Streamlit app with provided data"""
        # Set up the UI theme
        self.setup_ui_theme()

        # Main title
        st.title("SSRS Report Summary")

        # Navigation sidebar
        st.sidebar.header("Navigation")
        options = ["Overview", "Detailed Report", "Test Visualisation"]
        selected_option = st.sidebar.radio("Select View", options)

        if selected_option == "Overview":
            self.display_overiew_section(dataframe, performance_summary)
        elif selected_option == "Detailed Report":
            self.display_detailed_section()
        elif selected_option == "Test Visualisation":
            self.display_test_section(dataframe)

    def run_now_and_display(self):
        print("runing query and lauching...")
        dataframe, performance_summary = self.run_query()
        if dataframe is not None and performance_summary is not None:
            self.run_streamlit_app(dataframe, performance_summary)
        else:
            st.error("No data recceived or other erro")
            print("No data received or other error")
if __name__ == "__main__":
    monitor = SSRSReportMonitor(conn_str)
    #monitor.start() Runs the sheduler 
    monitor.run_now_and_display() # Runs now for testing

