import streamlit as st
from modules import authentication, navigation, database_manager
from modules.exceptions import FirebaseCredentialsError
from views import subject_selection, home_dashboard, home, admin_dashboard
from modules.subjects import gk_quiz, math_exercise

def render_sidebar():
    """Renders the main navigation sidebar and handles its logic."""
    with st.sidebar:
        st.title("👨‍🏫 Learning App")
        st.markdown("---")

        # The Home button should always be available
        if st.button("🏠 Home", use_container_width=True):
            navigation.reset_activity_state()
            navigation.set_view("home")

        if st.session_state.get("logged_in", False):
            # These buttons are available only when logged in
            if st.button("📚 Subjects", use_container_width=True):
                navigation.reset_activity_state()
                navigation.set_view("subject_selection")

            if st.button("📊 Scores Dashboard", use_container_width=True):
                navigation.reset_activity_state()
                navigation.set_view("home_dashboard")

            # Admin-only button
            if st.session_state.student_name == "admin":
                if st.button("⚙️ Admin Dashboard", use_container_width=True):
                    navigation.reset_activity_state()
                    navigation.set_view("admin_dashboard")
            
            # Logout button
            if st.button("👋 Logout", use_container_width=True):
                # A full reset for logout
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                navigation.set_view("login") # Go to login after logout

        else:
            # Show login button only if not logged in
            if st.button("🔒 Login", use_container_width=True):
                navigation.set_view("login")

        st.markdown("---")
        if st.session_state.get("logged_in", False):
            st.caption(f"Logged in as:\n**{st.session_state.student_name}**")

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="centered")
    
    # Initialize Firestore and handle potential credential errors
    try:
        database_manager.initialize_firestore()
    except FirebaseCredentialsError as e:
        st.error(f"Database Initialization Failed: {e}")
        st.stop()
    
    authentication.initialize_session_state()
    render_sidebar()

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