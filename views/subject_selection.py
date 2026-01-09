import streamlit as st
from modules import data_manager
from modules.navigation import set_view

def render():
    """Renders the subject selection screen."""
    st.header(f"Welcome, {st.session_state.student_name}! 👋")
    # st.subheader("Please select a subject to begin.")

    subjects_raw = data_manager.get_subjects()

    if not subjects_raw:
        st.warning("No subjects found. Please add subject data in the 'data' directory.")
        return

    # Custom ordering and categorization
    live_subject_keys = ["gk", "math"]
    live_subjects = []
    coming_soon_subjects = []

    for sub_name in subjects_raw:
        if sub_name.lower() in live_subject_keys:
            live_subjects.append(sub_name)
        else:
            coming_soon_subjects.append(sub_name)
    
    # Ensure live subjects are in a specific order
    live_subjects.sort(key=lambda x: live_subject_keys.index(x.lower()))
    # Sort coming soon subjects alphabetically
    coming_soon_subjects.sort()

    # --- Render Live Subjects ---
    st.markdown("#### Available Courses")
    num_columns = 2
    cols = st.columns(num_columns)

    for i, subject_key in enumerate(live_subjects):
        with cols[i % num_columns]:
            with st.container(border=True):
                display_name = subject_display_names.get(subject_key.lower(), subject_key)
                st.markdown(f"### {subject_icons.get(subject_key.lower(), '📚')} {display_name}")
                st.markdown(subject_descriptions.get(subject_key.lower(), "Explore exciting topics and practice your skills."))
                
                button_key = f"start_{subject_key.lower()}_button"
                if subject_key.lower() == "gk":
                    if st.button(f"Start {display_name} Quiz", key=button_key, width='stretch'):
                        set_view("gk_quiz")
                elif subject_key.lower() == "math":
                    if st.button(f"Start {display_name} Exercise", key=button_key, width='stretch'):
                        set_view("math_exercise")

# Helper dictionaries for icons and descriptions (can be moved to a config file later)
subject_display_names = {
    "gk": "General Knowledge",
    "math": "Math",
    "hindi": "Hindi",
    "english": "English",
    "environmental_science": "Environmental Science"
}

subject_icons = {
    "gk": "🧠",
    "math": "🔢",
    "hindi": "🇮🇳",
    "english": "📝",
    "environmental_science": "🌍"
}

subject_descriptions = {
    "gk": "Test your knowledge on a variety of general topics.",
    "math": "Practice your math skills with these interactive exercises.",
    "hindi": "Learn and practice the Hindi language with engaging activities.",
    "english": "Enhance your English reading, writing, and comprehension abilities.",
    "environmental_science": "Discover the world around us and learn about environmental concepts."
}
