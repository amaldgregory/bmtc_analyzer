import streamlit as st
import pandas as pd
import sqlite3
from streamlit_folium import st_folium
import folium

st.set_page_config(layout="wide", page_title="BMTC Routes Analyzer")
st.title("BMTC Route and Network Analysis")
st.write("~By Amal Gregory")

DB_FILE = "bmtc.db"

st.subheader("Quick Summary")
col1, col2, col3 = st.columns(3)

@st.cache_data #Cache the data so you don't have to keep running it
#To get query and return the result
def get_sql_metric(query):
    conn = sqlite3.connect(DB_FILE)
    result = pd.read_sql_query(query, conn).iloc[0, 0]
    conn.close()
    return result

#SQL queries for quick summary metrics
total_routes = get_sql_metric("SELECT COUNT(DISTINCT route_id) FROM routes;")
total_stops = get_sql_metric("SELECT COUNT(DISTINCT stop_id) FROM stops;")
total_trips = get_sql_metric("SELECT COUNT(DISTINCT trip_id) FROM trips;")

col1.metric("Total Unique Routes", f"{total_routes:,}")
col2.metric("Total Bus Stops", f"{total_stops:,}")
col3.metric("Total Daily Trips", f"{total_trips:,}")

st.divider()


def load_data_from_db():
    conn = sqlite3.connect(DB_FILE)
    
    #Master SQL Query to join all tables
    query = """
    SELECT
        r.route_long_name,
        r.route_short_name,
        t.trip_id,  -- Include trip_id to handle route variations
        s.stop_name,
        st.stop_sequence,
        s.stop_lat,
        s.stop_lon
    FROM routes r
    JOIN trips t ON r.route_id = t.route_id
    JOIN stop_times st ON t.trip_id = st.trip_id
    JOIN stops s ON st.stop_id = s.stop_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

master_df = load_data_from_db()

#Sidebar
st.sidebar.header("Route Selection")
unique_routes = master_df['route_long_name'].unique()
selected_route = st.sidebar.selectbox("Choose a Route to Visualize", unique_routes)

st.sidebar.header("Network Analysis")
show_top_stops = st.sidebar.toggle("Show Busiest Stops")

st.sidebar.header("Route Finder")
stop_search_term = st.sidebar.text_input("Enter a bus stop name")

st.sidebar.divider()

with st.sidebar.expander("About Me"):
    st.markdown(
        """
        This app was built by **Amal Gregory**.
        
        Connect with me:
        - [LinkedIn](https://www.linkedin.com/in/amal-gregory/) 
        - [GitHub](https://github.com/amaldgregory)  
        - amalgregory123@gmail.com 
        """
    )


#Filter data for the selected route
route_data = master_df[master_df['route_long_name'] == selected_route]

#Visualize longest trip as a route can have multiple different trips with small differences
longest_trip_id = route_data.groupby('trip_id')['stop_sequence'].max().idxmax()
trip_data = route_data[route_data['trip_id'] == longest_trip_id].sort_values('stop_sequence')


#Main Panel
st.header(f"Displaying: {selected_route}")
st.write(f"Showing the path for Trip ID: `{longest_trip_id}`")

#Map Visualization
if not trip_data.empty:
    mid_lat, mid_lon = trip_data['stop_lat'].mean(), trip_data['stop_lon'].mean()
    
    # Create a Folium map centered on the route
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=12)

    # Add the bus route path to the map
    points = trip_data[['stop_lat', 'stop_lon']].values.tolist()
    folium.PolyLine(points, color='red', weight=4, opacity=0.8).add_to(m)

    # Add each bus stop as a circle marker
    for idx, row in trip_data.iterrows():
        folium.CircleMarker(
            location=[row['stop_lat'], row['stop_lon']],
            radius=4,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.7,
            popup=f"<b>{row['stop_name']}</b><br>Sequence: {row['stop_sequence']}"
        ).add_to(m)

    # Display map in Streamlit
    st_folium(m, width=1200, height=600)
else:
    st.warning("No data available for the selected route.")

#Display Raw Data
if st.checkbox("Show raw stop data for this trip"):
    st.dataframe(trip_data[['stop_sequence', 'stop_name', 'stop_lat', 'stop_lon']])


st.divider()

if show_top_stops:
    st.header("Top 10 Busiest Bus Stops")
    st.write("Based on the total number of scheduled trips per day.")
    
    #SQL query to find the top 10 busiest stops
    top_stops_query = """
    SELECT
        s.stop_name,
        COUNT(st.stop_id) AS trip_count
    FROM stop_times st
    JOIN stops s ON st.stop_id = s.stop_id
    GROUP BY s.stop_name
    ORDER BY trip_count DESC
    LIMIT 10
    """
    conn = sqlite3.connect(DB_FILE)
    top_stops_df = pd.read_sql_query(top_stops_query, conn)
    conn.close()

    #Set the stop name as the index
    top_stops_df.set_index('stop_name', inplace=True)
    
    st.bar_chart(top_stops_df, color="#FF4B4B")
    
    with st.expander("View Raw Data"):
        st.dataframe(top_stops_df)

st.divider()

if stop_search_term:
    st.header(f"Routes passing through '{stop_search_term}'")
    
    # Using a parameterized query to prevent SQL injection
    find_routes_query = """
    SELECT DISTINCT
        r.route_long_name,
        r.route_short_name
    FROM routes r
    JOIN trips t ON r.route_id = t.route_id
    JOIN stop_times st ON t.trip_id = st.trip_id
    JOIN stops s ON st.stop_id = s.stop_id
    WHERE s.stop_name LIKE ?
    """
    
    conn = sqlite3.connect(DB_FILE)
    search_pattern = f'%{stop_search_term}%'
    found_routes_df = pd.read_sql_query(find_routes_query, conn, params=(search_pattern,))
    conn.close()

    if not found_routes_df.empty:
        st.dataframe(
            found_routes_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No routes found for that stop name. Please try another search.")