import streamlit as st
from datetime import datetime

def reset_activity_state():
    """Resets all session state variables related to an active quiz or exercise."""
    st.session_state.start_time = None
    st.session_state.quiz_finished = False
    st.session_state.questions = []
    st.session_state.user_answers = {}
    st.session_state.score = 0
    st.session_state.selected_level = None
    st.session_state.selected_chapter = None
    st.session_state.selected_story = None
    st.session_state.show_score_summary = False
    st.session_state.show_reward = False
    st.session_state.is_perfect_score = False

def set_view(view_name: str):
    """Sets the current view of the application and reruns the script."""
    st.session_state.current_view = view_name
    st.session_state.selected_attempt_file = None
    st.rerun()

def render_sidebar():
    """Renders the main navigation sidebar and handles its logic."""
    with st.sidebar:
        st.title("👨‍🏫 Learning App")
        st.markdown("---")

        if st.button("🏠 Home", use_container_width=True):
            reset_activity_state()
            set_view("home")

        if st.session_state.get("logged_in", False):

            if st.button("📚 Subjects", use_container_width=True):
                reset_activity_state()
                set_view("subject_selection")

            if st.button("📊 Scores Dashboard", use_container_width=True):
                reset_activity_state()
                set_view("home_dashboard")

            # --- Admin Button ---
            if st.session_state.student_name == "admin":
                if st.button("⚙️ Admin Dashboard", use_container_width=True):
                    reset_activity_state()
                    set_view("admin_dashboard")
            
            if st.button("👋 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


        else:
            if st.button("🔒 Login", use_container_width=True):
                set_view("login")

        st.markdown("---")

        if st.session_state.get("logged_in", False):
            st.caption(f"Logged in as:\n**{st.session_state.student_name}**")
        
        is_in_activity = st.session_state.get("current_view") in ["gk_quiz", "math_exercise"]
        if is_in_activity and not st.session_state.get("quiz_finished", True) and not st.session_state.get("show_score_summary", False):
            if st.session_state.get("start_time"):
                st.header("Time Elapsed")
                timer_placeholder = st.empty()
                elapsed_time = datetime.now() - st.session_state.start_time
                minutes, seconds = divmod(int(elapsed_time.total_seconds()), 60)
                timer_placeholder.markdown(f"## {minutes:02d}:{seconds:02d}")
            
            if st.session_state.get("questions") and st.session_state.get("user_answers"):
                total_questions = len(st.session_state.questions)
                answered_questions = sum(1 for answer in st.session_state.user_answers.values() if answer is not None and answer != [])
                st.subheader("Quiz Progress")
                st.progress(answered_questions / total_questions if total_questions > 0 else 0)
                st.write(f"{answered_questions} / {total_questions} Answered")