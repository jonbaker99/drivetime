import streamlit as st
import googlemaps
from datetime import datetime
from itertools import product
import os


# Use Streamlit secrets for API key

try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
except (st.errors.StreamlitAPIException, KeyError):
    API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    st.error("No Google Maps API key found. Please set it in Railway variables or .streamlit/secrets.toml")


# Initialize the Google Maps client
gmaps = googlemaps.Client(key=API_KEY)

def validate_address(address):
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            return geocode_result[0]['formatted_address'], None
        else:
            autocomplete_result = gmaps.places_autocomplete(address)
            suggestions = [result['description'] for result in autocomplete_result[:3]]
            return None, suggestions
    except Exception as e:
        st.error(f"Error validating address: {e}")
        return None, None

def get_travel_time(origin, destination, mode="driving"):
    now = datetime.now()
    try:
        # For driving, we can use departure_time and get traffic data
        if mode == "driving":
            directions_result = gmaps.directions(origin,
                                                 destination,
                                                 mode=mode,
                                                 departure_time=now)
        else:
            # For walking, transit, bicycling - no departure_time needed
            directions_result = gmaps.directions(origin,
                                                 destination,
                                                 mode=mode)
        
        if directions_result:
            leg = directions_result[0]['legs'][0]
            
            # For driving, prefer duration_in_traffic if available
            if mode == "driving" and 'duration_in_traffic' in leg:
                duration = leg['duration_in_traffic']['value']
            else:
                duration = leg['duration']['value']
            
            return round(duration / 60)  # Convert seconds to minutes
        else:
            return None
    except Exception as e:
        st.error(f"Error getting travel time: {e}")
        return None

def main():
    st.title("Travel Time Calculator")

    # Add travel mode selection
    travel_mode = st.radio(
        "Select travel mode:", 
        ("driving", "walking"),
        format_func=lambda x: x.capitalize()
    )
    
    trip_type = st.radio("Select trip type:", ("Return", "One-way"))

    start_points = {}
    destinations = {}

    st.header("Start Points")
    while True:
        start_point = st.text_input(f"Enter start point {len(start_points) + 1}", key=f"start_{len(start_points)}")
        if start_point:
            valid_address, suggestions = validate_address(start_point)
            if valid_address:
                start_points[start_point] = valid_address
                st.success(f"Validated address: {valid_address}")
            elif suggestions:
                choice = st.selectbox(f"Address not found. Did you mean one of these?", suggestions, key=f"suggest_start_{len(start_points)}")
                if choice:
                    valid_address, _ = validate_address(choice)
                    if valid_address:
                        start_points[start_point] = valid_address
                        st.success(f"Validated address: {valid_address}")
            else:
                st.error(f"Invalid address: {start_point}. Please try again.")
        else:
            break

    st.header("Destinations")
    if trip_type == "One-way" or len(start_points) > 1:
        for start_name, start_address in start_points.items():
            if st.checkbox(f"Use '{start_name}' as a destination too?"):
                destinations[start_name] = start_address

    while True:
        destination = st.text_input(f"Enter destination {len(destinations) + 1}", key=f"dest_{len(destinations)}")
        if destination:
            valid_address, suggestions = validate_address(destination)
            if valid_address:
                destinations[destination] = valid_address
                st.success(f"Validated address: {valid_address}")
            elif suggestions:
                choice = st.selectbox(f"Address not found. Did you mean one of these?", suggestions, key=f"suggest_dest_{len(destinations)}")
                if choice:
                    valid_address, _ = validate_address(choice)
                    if valid_address:
                        destinations[destination] = valid_address
                        st.success(f"Validated address: {valid_address}")
            else:
                st.error(f"Invalid address: {destination}. Please try again.")
        else:
            break

    if st.button(f"Calculate {travel_mode.capitalize()} Times"):
        st.header("Results")
        for start_name, start_address in start_points.items():
            for end_name, end_address in destinations.items():
                if start_address != end_address:
                    outbound_duration = get_travel_time(start_address, end_address, travel_mode)
                    if outbound_duration:
                        if trip_type == "Return":
                            inbound_duration = get_travel_time(end_address, start_address, travel_mode)
                            if inbound_duration:
                                total_duration = outbound_duration + inbound_duration
                                st.write(f"{start_name} -> {end_name} -> {start_name}: {total_duration} mins [{outbound_duration} mins out, {inbound_duration} mins back]")
                            else:
                                st.warning(f"Could not calculate return time for {start_name} -> {end_name} -> {start_name}")
                        else:
                            st.write(f"{start_name} -> {end_name}: {outbound_duration} minutes")
                    else:
                        st.warning(f"Could not calculate time for {start_name} -> {end_name}")

if __name__ == "__main__":
    main()
