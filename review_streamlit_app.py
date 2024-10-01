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

def main():
    st.title("Google Places Search App")
    
    if 'places' not in st.session_state:
        st.session_state.places = []
    
    # Input for place name
    place_name = st.text_input("Enter the name of a place or business:")
    
    if place_name:
        details = get_place_details(place_name)
        
        if details:
            st.session_state.places.append(details)
            st.success(f"Added: {details['name']}")
            st.info(f"Address: {details['address']}")
        else:
            st.warning("Couldn't find an exact match. Here are some suggestions:")
            suggestions = get_place_suggestions(place_name)
            selected_suggestion = st.selectbox("Select a suggestion:", suggestions)
            
            if st.button("Add selected suggestion"):
                details = get_place_details(selected_suggestion)
                if details:
                    st.session_state.places.append(details)
                    st.success(f"Added: {details['name']}")
    
    # Display the results
    if st.session_state.places:
        st.subheader("Results")
        table = PrettyTable()
        table.field_names = ["Place Name", "Number of Reviews", "Score"]
        table.align["Place Name"] = "l"
        table.align["Number of Reviews"] = "r"
        table.align["Score"] = "r"
        
        for place in st.session_state.places:
            table.add_row([
                place['name'],
                place['total_ratings'],
                f"{place['rating']:.1f}" if isinstance(place['rating'], (int, float)) else place['rating']
            ])
        
        st.text(table)
    
    # Clear all button
    if st.button("Clear All"):
        st.session_state.places = []
        st.success("All places cleared!")
        st.experimental_rerun()

if __name__ == "__main__":
    main()