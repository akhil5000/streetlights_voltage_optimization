import streamlit as st
import json
import matplotlib.pyplot as plt

# --- Load data ---
@st.cache_data
def load_data():
    with open('traffic_data.json', 'r') as f:
        traffic_data = json.load(f)
    with open('smoothed_voltage_schedule.json', 'r') as f:
        voltage_data = json.load(f)
    with open('city_grid.json', 'r') as f:
        city_grid = json.load(f)
    return traffic_data, voltage_data, city_grid

traffic_data, voltage_data, city_grid = load_data()

# --- Build mapping from intersection to zone ---
intersection_zone = {node["id"]: node["zone"] for node in city_grid["nodes"]}
zones = ["residential", "commercial", "industrial", "park"]

# --- Helper functions ---
def get_zone_roads(zone):
    """Return all roads whose source intersection is in `zone`."""
    return [
        road for road in traffic_data.keys()
        if intersection_zone.get(road.split("-")[0]) == zone
    ]

def aggregate_zone_traffic(zone):
    """Sum up hourly vehicles & pedestrians across all roads in the zone."""
    roads = get_zone_roads(zone)
    agg = {h: {"vehicles": 0, "pedestrians": 0} for h in range(24)}
    for road in roads:
        veh_list = traffic_data[road]["vehicles"]
        ped_list = traffic_data[road]["pedestrians"]
        for h in range(24):
            agg[h]["vehicles"] += veh_list[h]
            agg[h]["pedestrians"] += ped_list[h]
    return agg

def plot_traffic(hours, vehicles, pedestrians, title):
    plt.figure(figsize=(10, 5))
    plt.plot(hours, vehicles, marker='o', label="Vehicles")
    plt.plot(hours, pedestrians, marker='x', label="Pedestrians")
    plt.title(title)
    plt.xlabel("Hour of Day")
    plt.ylabel("Count")
    plt.grid(True)
    plt.legend()
    st.pyplot(plt.gcf())
    plt.close()

def plot_zone_traffic(zone):
    agg = aggregate_zone_traffic(zone)
    hours = list(range(24))
    veh = [agg[h]["vehicles"] for h in hours]
    ped = [agg[h]["pedestrians"] for h in hours]
    plot_traffic(hours, veh, ped, f"{zone.capitalize()} Zone: Hourly Traffic")

def plot_road_traffic(road):
    veh = traffic_data[road]["vehicles"]
    ped = traffic_data[road]["pedestrians"]
    # night hours 19–23, 0–6
    night = list(range(19,24)) + list(range(0,7))
    h_labels = [str(h) for h in night]
    v = [veh[h] for h in night]
    p = [ped[h] for h in night]
    plot_traffic(h_labels, v, p, f"{road}: Nightly Traffic (7 PM–6 AM)")

def plot_road_voltage(road):
    try:
        # Extract voltage values for the specified road
        source, destination = road.split("-")
        voltage_values = voltage_data.get(source, {}).get(destination, None)
        
        if not voltage_values:
            st.error(f"Voltage data for road '{road}' not found.")
            return
        
        # Define the hours range for plotting
        night_hours = list(range(19, 24)) + list(range(0, 7))
        hours = [str(h) for h in night_hours]
        voltages = [voltage_values.get(str(h), None) for h in night_hours]
        
        if None in voltages:
            st.warning(f"Some voltage data is missing for road '{road}'.")
        
        # Plot the voltage values
        plt.figure(figsize=(10, 5))
        plt.plot(hours, voltages, marker='o', label=f"Voltage for {road}")
        plt.xlabel('Time (hours)')
        plt.ylabel('Voltage (V)')
        plt.title(f"Voltage Profile for {road}")
        plt.legend()
        plt.grid(True)
        st.pyplot(plt.gcf())
        plt.close()
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# --- Streamlit layout ---
st.title("🚦 Smart City Traffic & Voltage Dashboard")

selected_zone = st.selectbox("1) Select Zone", zones)
if selected_zone:
    st.subheader(f"Zone-wide Traffic: {selected_zone.capitalize()}")
    plot_zone_traffic(selected_zone)

    roads = get_zone_roads(selected_zone)
    if roads:
        selected_road = st.selectbox("2) Select Road", roads)
        if selected_road:
            st.subheader(f"Traffic on {selected_road}")
            plot_road_traffic(selected_road)
            st.subheader(f"Voltage Schedule for {selected_road}")
            plot_road_voltage(selected_road)
    else:
        st.warning("No roads found for this zone.")
