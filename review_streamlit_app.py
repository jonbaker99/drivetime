import streamlit as st
import requests
from prettytable import PrettyTable

# Get the API key from Streamlit secrets
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]

def get_place_suggestions(place_name):
    search_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    search_params = {
        "input": place_name,
        "types": "establishment",
        "key": API_KEY
    }
    
    search_response = requests.get(search_url, params=search_params)
    search_data = search_response.json()
    
    if search_data["status"] == "OK":
        return [prediction["description"] for prediction in search_data["predictions"]]
    return []

def get_place_details(place_name):
    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    search_params = {
        "input": place_name,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address",
        "key": API_KEY
    }
    
    search_response = requests.get(search_url, params=search_params)
    search_data = search_response.json()
    
    if search_data["status"] == "OK":
        place = search_data["candidates"][0]
        place_id = place["place_id"]
        
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,rating,user_ratings_total,formatted_address",
            "key": API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data["status"] == "OK":
            result = details_data["result"]
            return {
                "name": result["name"],
                "address": result["formatted_address"],
                "rating": result.get("rating", "N/A"),
                "total_ratings": result.get("user_ratings_total", "N/A")
            }
    
    return None

def generate_table(places):
    if places:
        table = PrettyTable()
        table.field_names = ["Place Name", "Address", "Number of Reviews", "Score"]
        table.align["Place Name"] = "l"
        table.align["Address"] = "l"
        table.align["Number of Reviews"] = "r"
        table.align["Score"] = "r"
        
        for place in places:
            table.add_row([
                place['name'],
                place['address'],
                place['total_ratings'],
                f"{place['rating']:.1f}" if isinstance(place['rating'], (int, float)) else place['rating']
            ])
        
        st.text(table)
    else:
        st.warning("No places added yet. Add some places to see results.")

def main():
    st.title("Google Places Search App")
    
    if 'places' not in st.session_state:
        st.session_state.places = []

    # Function to handle input submission
    def handle_submit():
        place_names = [name.strip() for name in st.session_state.places_input.split('\n') if name.strip()]
        
        for place_name in place_names:
            details = get_place_details(place_name)
            if details:
                st.session_state.places.append(details)
                st.success(f"Added: {details['name']} - {details['address']}")
            else:
                st.error(f"Couldn't find an exact match for '{place_name}'. Try a more specific name.")
        
        st.session_state.places_input = ""  # Clear the input

    # Input for place names
    st.text_area("Enter place names (one per line):", key="places_input", on_change=handle_submit)
    
    # Submit button (for users who prefer clicking)
    st.button("Submit Places", on_click=handle_submit)
    
    # Display current places with options
    st.subheader("Current Places")
    for i, place in enumerate(st.session_state.places):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"{place['name']} - {place['address']}")
        with col2:
            if st.button(f"Review Alternatives {i}"):
                alternatives = get_place_suggestions(place['name'])
                if alternatives:
                    selected_alternative = st.selectbox(
                        f"Alternatives for {place['name']}",
                        alternatives,
                        key=f"alt_{i}",
                        format_func=lambda x: x[:100] + "..." if len(x) > 100 else x
                    )
                    if st.button(f"Replace with Selected Alternative {i}"):
                        new_details = get_place_details(selected_alternative)
                        if new_details:
                            st.session_state.places[i] = new_details
                            st.rerun()
                else:
                    st.warning("No alternatives found.")
        with col3:
            if st.button(f"Remove {i}"):
                del st.session_state.places[i]
                st.rerun()

    # Button to generate table
    if st.button("Generate Results Table"):
        generate_table(st.session_state.places)

    # Clear all button
    if st.button("Clear All"):
        st.session_state.places = []
        st.success("All places cleared!")
        st.rerun()

if __name__ == "__main__":
    main()