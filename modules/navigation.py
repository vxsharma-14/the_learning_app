import streamlit as st

def reset_activity_state():
    """
    Resets all session state variables related to any active quiz, exercise, or view-specific state.
    This is a comprehensive cleanup function to be called when navigating between main app sections.
    """
    keys_to_pop = [
        # Generic quiz state
        'start_time', 'quiz_finished', 'questions', 'user_answers', 'score',
        'show_score_summary', 'show_reward', 'is_perfect_score', 'selected_attempt_file',

        # GK Quiz specific state
        'quiz_in_progress', 'selected_gk_topic_id', 'selected_gk_quiz_id', 'gk_title',
        'gk_background', 'gk_icon_legend', 'gk_reward_text',
        
        # Math Exercise specific state
        'exercise_in_progress', 'math_view', 'selected_chapter_id', 'selected_story_file',
        'selected_chapter_name', 'selected_story_name', 'math_reward_text'
    ]
    for key in keys_to_pop:
        st.session_state.pop(key, None)

def set_view(view_name: str):
    """Sets the current view of the application and reruns the script."""
    # Ensure any lingering activity state is cleared when changing main views
    # Note: reset_activity_state() should ideally be called *before* this function.
    st.session_state.current_view = view_name
    st.rerun()