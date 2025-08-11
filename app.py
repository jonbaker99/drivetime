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

    # Initialize session state
    if 'start_points' not in st.session_state:
        st.session_state.start_points = {}
    if 'destinations' not in st.session_state:
        st.session_state.destinations = {}
    if 'num_start_inputs' not in st.session_state:
        st.session_state.num_start_inputs = 1
    if 'num_dest_inputs' not in st.session_state:
        st.session_state.num_dest_inputs = 1

    # Add travel mode selection
    travel_mode = st.radio(
        "Select travel mode:", 
        ("driving", "walking"),
        format_func=lambda x: x.capitalize()
    )
    
    trip_type = st.radio("Select trip type:", ("Return", "One-way"))

    # Start Points Section
    st.header("Start Points")
    
    # Use columns for better layout
    col1, col2 = st.columns([4, 1])
    
    with col1:
        for i in range(st.session_state.num_start_inputs):
            start_point = st.text_input(
                f"Enter start point {i + 1}", 
                key=f"start_input_{i}",
                placeholder="e.g., 123 Main St, City, State"
            )
            
            if start_point and start_point not in st.session_state.start_points:
                valid_address, suggestions = validate_address(start_point)
                if valid_address:
                    st.session_state.start_points[start_point] = valid_address
                    st.success(f"✅ Validated: {valid_address}")
                elif suggestions:
                    choice = st.selectbox(
                        f"Address not found. Did you mean:", 
                        ["Select one..."] + suggestions, 
                        key=f"suggest_start_{i}"
                    )
                    if choice != "Select one...":
                        valid_address, _ = validate_address(choice)
                        if valid_address:
                            st.session_state.start_points[start_point] = valid_address
                            st.success(f"✅ Validated: {valid_address}")
                else:
                    st.error(f"❌ Invalid address: {start_point}")
    
    with col2:
        st.write("")  # Spacing
        if st.button("Add Start Point", key="add_start"):
            st.session_state.num_start_inputs += 1
            st.experimental_rerun()
        
        if st.session_state.num_start_inputs > 1:
            if st.button("Remove Start Point", key="remove_start"):
                st.session_state.num_start_inputs -= 1
                st.experimental_rerun()

    # Show validated start points
    if st.session_state.start_points:
        st.subheader("Validated Start Points:")
        for original, validated in st.session_state.start_points.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• {original} → {validated}")
            with col2:
                if st.button("Remove", key=f"remove_start_{original}"):
                    del st.session_state.start_points[original]
                    st.experimental_rerun()

    # Destinations Section
    st.header("Destinations")
    
    # Option to use start points as destinations
    if trip_type == "One-way" and st.session_state.start_points:
        st.subheader("Use start points as destinations?")
        for start_name, start_address in st.session_state.start_points.items():
            if st.checkbox(f"Use '{start_name}' as destination", key=f"start_as_dest_{start_name}"):
                st.session_state.destinations[start_name] = start_address
            elif start_name in st.session_state.destinations:
                del st.session_state.destinations[start_name]

    # Destination inputs
    col1, col2 = st.columns([4, 1])
    
    with col1:
        for i in range(st.session_state.num_dest_inputs):
            destination = st.text_input(
                f"Enter destination {i + 1}", 
                key=f"dest_input_{i}",
                placeholder="e.g., 456 Oak Ave, City, State"
            )
            
            if destination and destination not in st.session_state.destinations:
                valid_address, suggestions = validate_address(destination)
                if valid_address:
                    st.session_state.destinations[destination] = valid_address
                    st.success(f"✅ Validated: {valid_address}")
                elif suggestions:
                    choice = st.selectbox(
                        f"Address not found. Did you mean:", 
                        ["Select one..."] + suggestions, 
                        key=f"suggest_dest_{i}"
                    )
                    if choice != "Select one...":
                        valid_address, _ = validate_address(choice)
                        if valid_address:
                            st.session_state.destinations[destination] = valid_address
                            st.success(f"✅ Validated: {valid_address}")
                else:
                    st.error(f"❌ Invalid address: {destination}")
    
    with col2:
        st.write("")  # Spacing
        if st.button("Add Destination", key="add_dest"):
            st.session_state.num_dest_inputs += 1
            st.experimental_rerun()
        
        if st.session_state.num_dest_inputs > 1:
            if st.button("Remove Destination", key="remove_dest"):
                st.session_state.num_dest_inputs -= 1
                st.experimental_rerun()

    # Show validated destinations
    if st.session_state.destinations:
        st.subheader("Validated Destinations:")
        for original, validated in st.session_state.destinations.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• {original} → {validated}")
            with col2:
                if st.button("Remove", key=f"remove_dest_{original}"):
                    del st.session_state.destinations[original]
                    st.experimental_rerun()

    # Clear all button
    if st.button("Clear All", type="secondary"):
        st.session_state.start_points = {}
        st.session_state.destinations = {}
        st.session_state.num_start_inputs = 1
        st.session_state.num_dest_inputs = 1
        st.experimental_rerun()

    # Calculate button and results
    if st.session_state.start_points and st.session_state.destinations:
        if st.button(f"Calculate {travel_mode.capitalize()} Times", type="primary"):
            st.header("Results")
            
            with st.spinner("Calculating travel times..."):
                for start_name, start_address in st.session_state.start_points.items():
                    for end_name, end_address in st.session_state.destinations.items():
                        if start_address != end_address:
                            outbound_duration = get_travel_time(start_address, end_address, travel_mode)
                            # Choose emoji based on travel mode
                            mode_emoji = "🚗" if travel_mode == "driving" else "🚶‍♂️"
                            
                            if outbound_duration:
                                if trip_type == "Return":
                                    inbound_duration = get_travel_time(end_address, start_address, travel_mode)
                                    if inbound_duration:
                                        total_duration = outbound_duration + inbound_duration
                                        st.success(f"{mode_emoji} {start_name} → {end_name} → {start_name}: **{total_duration} minutes** [{outbound_duration} min out, {inbound_duration} min back]")
                                    else:
                                        st.warning(f"⚠️ Could not calculate return time for {start_name} → {end_name}")
                                else:
                                    st.success(f"{mode_emoji} {start_name} → {end_name}: **{outbound_duration} minutes**")
                            else:
                                st.error(f"❌ Could not calculate time for {start_name} → {end_name}")
    else:
        if not st.session_state.start_points:
            st.info("👆 Please add at least one start point")
        if not st.session_state.destinations:
            st.info("👆 Please add at least one destination")

if __name__ == "__main__":
    main()
