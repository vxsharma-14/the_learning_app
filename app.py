import streamlit as st
from modules import authentication, navigation, database_manager
from modules.exceptions import FirebaseCredentialsError
from views import subject_selection, home_dashboard, home, admin_dashboard
from modules.subjects import gk_quiz, math_exercise

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide")
    
    # Initialize Firestore and handle potential credential errors
    try:
        database_manager.initialize_firestore()
        # Add a toast for successful initialization, which is now safe to do here
        if 'db_initialized_once' not in st.session_state:
            if hasattr(st, 'secrets') and "firebase" in st.secrets:
                st.toast("Firebase initialized from Streamlit secrets.", icon="🚀")
            else:
                st.toast("Firebase initialized from local file.", icon="💻")
            st.session_state.db_initialized_once = True
            
    except FirebaseCredentialsError as e:
        st.error(f"Database Initialization Failed: {e}")
        st.stop()
    
    authentication.initialize_session_state()
    navigation.render_sidebar()

    # Main content routing
    view = st.session_state.get("current_view", "home")

    if view in ["home", "login", "register"]:
        if view == "home":
            home.render()
        elif view == "login":
            authentication.render_login_view()
        elif view == "register":
            authentication.render_register_view()
    else:
        # Protected views
        if st.session_state.get("logged_in"):
            if view == "subject_selection":
                subject_selection.render()
            elif view == "home_dashboard":
                home_dashboard.render()
            elif view == "gk_quiz":
                gk_quiz.render()
            elif view == "math_exercise":
                math_exercise.render()
            elif view == "admin_dashboard":
                if st.session_state.student_name == "admin":
                    admin_dashboard.render()
                else:
                    st.error("You do not have permission to access this page.")
                    home.render()
            else:
                # Fallback to home if view is unknown
                st.error("Invalid view selected.")
                home.render()
        else:
            st.warning("Please log in to access this page.")
            authentication.render_login_view()

if __name__ == "__main__":
    main()