import streamlit as st
import requests
from prettytable import PrettyTable

API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]

def get_place_suggestions(place_name):
    search_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
    }
    data = {
        "textQuery": place_name,
        "languageCode": "en"
    }
    
    try:
        search_response = requests.post(search_url, headers=headers, json=data)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        if "places" in search_data:
            return [f"{place['displayName']['text']} - {place['formattedAddress']}" for place in search_data["places"]]
        return []
    except requests.RequestException as e:
        st.error(f"An error occurred while fetching place suggestions: {str(e)}")
        return []

def get_place_details(place_name):
    search_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount"
    }
    data = {
        "textQuery": place_name,
        "languageCode": "en"
    }
    
    try:
        search_response = requests.post(search_url, headers=headers, json=data)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        if "places" in search_data and search_data["places"]:
            place = search_data["places"][0]
            return {
                "name": place["displayName"]["text"],
                "address": place["formattedAddress"],
                "rating": place.get("rating", "N/A"),
                "total_ratings": place.get("userRatingCount", "N/A")
            }
        return None
    except requests.RequestException as e:
        st.error(f"An error occurred while fetching place details: {str(e)}")
        return None

def find_place(place_name):
    details = get_place_details(place_name)
    if details:
        return details, None
    else:
        alternatives = get_place_suggestions(place_name)
        return None, alternatives

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
    if 'pending_alternatives' not in st.session_state:
        st.session_state.pending_alternatives = {}
    if 'original_inputs' not in st.session_state:
        st.session_state.original_inputs = {}
    if 'reviewing_alternatives' not in st.session_state:
        st.session_state.reviewing_alternatives = {}
    if 'place_alternatives' not in st.session_state:
        st.session_state.place_alternatives = {}
    if 'submit_clicked' not in st.session_state:
        st.session_state.submit_clicked = False

    def handle_submit():
        st.session_state.submit_clicked = True

    places_input = st.text_area("Enter place names (one per line):", key="places_input")
    
    if st.button("Submit Places") or st.session_state.submit_clicked:
        if st.session_state.submit_clicked:
            st.session_state.submit_clicked = False
            place_names = [name.strip() for name in places_input.split('\n') if name.strip()]
            
            for place_name in place_names:
                details, alternatives = find_place(place_name)
                if details:
                    st.session_state.places.append(details)
                    st.session_state.original_inputs[details['name']] = place_name
                    st.session_state.place_alternatives[details['name']] = get_place_suggestions(place_name)
                    st.success(f"Added: {details['name']} - {details['address']}")
                elif alternatives:
                    st.session_state.pending_alternatives[place_name] = alternatives
                    st.warning(f"Couldn't find an exact match for '{place_name}'. Please select from alternatives.")
                else:
                    st.error(f"No matches found for '{place_name}'. Try a different name.")
        else:
            handle_submit()
            st.rerun()

    for place_name, alternatives in list(st.session_state.pending_alternatives.items()):
        st.write(f"Select an alternative for '{place_name}':")
        selected_alternative = st.selectbox(
            f"Alternatives for {place_name}",
            alternatives,
            key=f"alt_{place_name}",
            format_func=lambda x: x[:100] + "..." if len(x) > 100 else x
        )
        if selected_alternative != alternatives[0]:
            details = get_place_details(selected_alternative.split(' - ')[0])
            if details:
                st.session_state.places.append(details)
                st.session_state.original_inputs[details['name']] = place_name
                st.session_state.place_alternatives[details['name']] = alternatives
                st.success(f"Added: {details['name']} - {details['address']}")
                del st.session_state.pending_alternatives[place_name]
                st.rerun()

    st.subheader("Current Places")
    for i, place in enumerate(st.session_state.places):
        st.write(f"{place['name']} - {place['address']}")
        col1, col2 = st.columns([1, 1])
        
        alternatives = st.session_state.place_alternatives.get(place['name'], [])
        if len(alternatives) > 1:
            with col1:
                if st.button(f"Review Alternatives {i}", key=f"review_button_{i}"):
                    st.session_state.reviewing_alternatives[i] = not st.session_state.reviewing_alternatives.get(i, False)
        
        with col2:
            if st.button(f"Remove {i}"):
                del st.session_state.places[i]
                if place['name'] in st.session_state.place_alternatives:
                    del st.session_state.place_alternatives[place['name']]
                if i in st.session_state.reviewing_alternatives:
                    del st.session_state.reviewing_alternatives[i]
                st.rerun()
        
        if st.session_state.reviewing_alternatives.get(i, False) and len(alternatives) > 1:
            original_input = st.session_state.original_inputs.get(place['name'], place['name'])
            current_place = f"{place['name']} - {place['address']}"
            alternatives = [current_place] + [alt for alt in alternatives if alt != current_place]
            selected_alternative = st.selectbox(
                f"Alternatives for {original_input}",
                alternatives,
                key=f"review_alt_{i}",
                format_func=lambda x: x[:100] + "..." if len(x) > 100 else x
            )
            if selected_alternative != current_place:
                new_details = get_place_details(selected_alternative.split(' - ')[0])
                if new_details:
                    st.session_state.places[i] = new_details
                    st.session_state.original_inputs[new_details['name']] = original_input
                    st.session_state.place_alternatives[new_details['name']] = alternatives
                    st.session_state.reviewing_alternatives[i] = False
                    if place['name'] in st.session_state.place_alternatives:
                        del st.session_state.place_alternatives[place['name']]
                    st.success(f"Replaced with: {new_details['name']} - {new_details['address']}")
                    st.rerun()
        
        st.write("---")

    if st.button("Generate Results Table"):
        generate_table(st.session_state.places)

    if st.button("Clear All"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("All data cleared!")
        st.rerun()

if __name__ == "__main__":
    main()