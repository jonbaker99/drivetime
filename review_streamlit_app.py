import streamlit as st
import requests

# Load API key from Streamlit secrets
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]

# ----------------------------
# Helper Functions
# ----------------------------

def perform_request(url, headers=None, params=None, data=None):
    """
    Perform an HTTP request and handle errors.
    """
    try:
        if data:
            response = requests.post(url, headers=headers, json=data)
        elif params:
            response = requests.get(url, params=params, headers=headers)
        else:
            response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"An error occurred during the API request: {e}")
        return None

def get_place_suggestions(original_input):
    """
    Fetch place suggestions based on the original input using Google's Text Search API.
    """
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": original_input,
        "key": API_KEY,
        "language": "en"
    }

    result = perform_request(search_url, params=params)
    if result and "results" in result:
        # Return list of dicts with 'display' and 'place_id'
        return [
            {
                "display": f"{place['name']} :: {place['formatted_address']}",
                "place_id": place["place_id"]
            }
            for place in result["results"]
        ]
    return []

def get_place_details(place_id):
    """
    Fetch detailed information about a specific place using Google's Place Details API.
    """
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,rating,user_ratings_total",
        "key": API_KEY,
        "language": "en"
    }

    result = perform_request(details_url, params=params)
    if result and "result" in result:
        place = result["result"]
        return {
            "name": place.get("name", "N/A"),
            "address": place.get("formatted_address", "N/A"),
            "rating": place.get("rating", "N/A"),
            "total_ratings": place.get("user_ratings_total", "N/A")
        }
    return None

def find_place(original_input):
    """
    Find place suggestions and limit to top 5 alternatives.
    """
    alternatives = get_place_suggestions(original_input)
    return alternatives[:5] if alternatives else []

def generate_table(places):
    """
    Generate and display the results table using Streamlit's native table display.
    """
    if places:
        table_data = {
            "Place Name": [place['details']['name'] for place in places],
            "Address": [place['details']['address'] for place in places],
            "Number of Reviews": [place['details']['total_ratings'] for place in places],
            "Score": [
                f"{place['details']['rating']:.1f}" if isinstance(place['details']['rating'], (int, float)) else place['details']['rating']
                for place in places
            ]
        }
        st.table(table_data)
    else:
        st.warning("No places added yet. Add some places to see results.")

# ----------------------------
# Session State Initialization
# ----------------------------

def init_session_state():
    """
    Initialize session state variables if they do not exist.
    """
    if 'places' not in st.session_state:
        st.session_state.places = []
    if 'places_input' not in st.session_state:
        st.session_state.places_input = ''

# ----------------------------
# Callback Functions
# ----------------------------

def clear_all():
    """
    Clear all session state data and reset the page.
    """
    st.session_state.places = []
    st.session_state.places_input = ''

# ----------------------------
# Main Application
# ----------------------------

def main():
    st.title("Google Places Search App")
    
    # Optional: Display Streamlit version for verification
    st.write(f"Streamlit version: {st.__version__}")

    # Initialize session state
    init_session_state()

    # ----------------------------
    # Clear All Button
    # ----------------------------
    st.button("Clear All", on_click=clear_all)

    # ----------------------------
    # Input Area for Place Names
    # ----------------------------
    # The value parameter ensures the text area reflects the current session state
    places_input = st.text_area(
        "Enter place names (one per line):",
        value=st.session_state.places_input,
        key="places_input"
    )

    # ----------------------------
    # Submit Places Button
    # ----------------------------
    if st.button("Submit Places"):
        place_names = [name.strip() for name in places_input.split('\n') if name.strip()]
        for place_name in place_names:
            alternatives = find_place(place_name)
            if alternatives:
                # Automatically select the best match (first alternative)
                best_match = alternatives[0]
                with st.spinner(f"Fetching details for '{best_match['display'].split(' :: ')[0]}'..."):
                    details = get_place_details(best_match['place_id'])
                if details:
                    # Check for duplicates based on name and address
                    if not any(
                        existing_place['details']['name'] == details['name'] and 
                        existing_place['details']['address'] == details['address'] 
                        for existing_place in st.session_state.places
                    ):
                        st.session_state.places.append({
                            'original_input': place_name,
                            'alternatives': alternatives,
                            'selected': best_match['place_id'],
                            'details': details
                        })
                        st.success(f"Added: {details['name']} - {details['address']}")
            else:
                st.error(f"No matches found for '{place_name}'. Try a different name.")

    # ----------------------------
    # Review and Modify Places
    # ----------------------------
    if st.session_state.places:
        st.subheader("Review and Modify Places")
        for i, place in enumerate(st.session_state.places):
            alternatives = place['alternatives']
            if alternatives:
                # Get list of display strings
                display_options = [alt['display'] for alt in alternatives]
                # Get mapping from display string to place_id
                display_to_id = {alt['display']: alt['place_id'] for alt in alternatives}
                # Get current selected place_id
                current_place_id = place['selected']
                # Get current display string
                current_display = next(
                    (alt['display'] for alt in alternatives if alt['place_id'] == current_place_id),
                    display_options[0]
                )
                # Find the index of current_display
                default_index = display_options.index(current_display) if current_display in display_options else 0
                # Unique key for each selectbox
                select_key = f"select_{i}"
                # Render the selectbox and remove button in the same row
                col1, col2 = st.columns([4, 1])
                with col1:
                    selected_display = st.selectbox(
                        f"Select alternative for '{place['original_input']}':",
                        options=display_options,
                        index=default_index,
                        key=select_key
                    )
                with col2:
                    remove_button = st.button("Remove", key=f"remove_button_{i}")
                    if remove_button:
                        del st.session_state.places[i]
                        st.success(f"Removed: {place['details']['name']} - {place['details']['address']}")
                        st.experimental_rerun()  # Rerun to update the UI immediately

                # Check if the selected option has changed
                if selected_display != current_display:
                    selected_place_id = display_to_id[selected_display]
                    with st.spinner(f"Fetching details for '{selected_display.split(' :: ')[0]}'..."):
                        new_details = get_place_details(selected_place_id)
                    if new_details:
                        # Update the place's 'selected' and 'details'
                        st.session_state.places[i]['selected'] = selected_place_id
                        st.session_state.places[i]['details'] = new_details
                        st.success(f"Updated to: {new_details['name']} - {new_details['address']}")

    # ----------------------------
    # Results Table
    # ----------------------------
    if len(st.session_state.places) > 1:
        generate_table(st.session_state.places)

    # ----------------------------
    # Prevent Displaying Code as Text
    # ----------------------------
    # Ensure no triple-quoted strings or improperly commented code are present.
    # All comments should use '#' for single-line comments.

    # Example of proper commenting:
    # st.subheader("Current Places")
    # for i, place in enumerate(st.session_state.places):
    #     st.write(f"{i+1}. {place['details']['name']} :: {place['details']['address']}")
    #     # Buttons to remove place
    #     col1, col2 = st.columns(2)
    #     with col1:
    #         if st.button(f"Remove {i}", key=f"remove_button_{i}"):
    #             del st.session_state.places[i]
    #             st.success(f"Removed: {place['details']['name']} - {place['details']['address']}")
    #             break  # Exit loop to avoid index errors
    #     st.write("---")

if __name__ == "__main__":
    main()
