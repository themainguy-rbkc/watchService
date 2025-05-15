import streamlit as st
import pandas as pd
import plotly.express as px

def load_data():
    # Replace with your data loading method
    return pd.read_csv('report_logs.csv')

def main():
    st.title('SSRS Report Performance Dashboard')
    
    # Load data
    df = load_data()
    
    # Sidebar filters
    st.sidebar.header('Filters')
    selected_report = st.sidebar.multiselect(
        'Select Reports', 
        df['ReportName'].unique()
    )
    
    # Filtered dataframe
    if selected_report:
        df_filtered = df[df['ReportName'].isin(selected_report)]
    else:
        df_filtered = df
    
    # Performance Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric('Avg Processing Time', f"{df_filtered['TimeProcessing'].mean():.2f} ms")
    col2.metric('Avg Rendering Time', f"{df_filtered['TimeRendering'].mean():.2f} ms")
    col3.metric('Avg Data Retrieval', f"{df_filtered['TimeDataRetrieval'].mean():.2f} ms")
    
    # Report Execution Time Series
    st.subheader('Report Execution Over Time')
    fig = px.line(df_filtered, x='TimeStart', y='TimeProcessing', color='ReportName')
    st.plotly_chart(fig)
    
    # Detailed Data Table
    st.subheader('Detailed Report Log')
    st.dataframe(df_filtered)

if __name__ == '__main__':
    main()