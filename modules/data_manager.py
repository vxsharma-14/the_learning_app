import streamlit as st
from modules import database_manager

# --- Subject & Index Loading ---
@st.cache_data
def get_subjects():
    """Fetches available subjects from the 'subject_indices' collection in Firestore."""
    db = database_manager.initialize_firestore()
    docs = db.collection('subject_indices').stream()
    return [doc.id for doc in docs]

@st.cache_data
def load_gk_index() -> dict:
    """Loads the GK index data from Firestore."""
    return database_manager.get_subject_index("GK") or {}

@st.cache_data
def load_math_index() -> dict:
    """Loads the Math index data from Firestore."""
    return database_manager.get_subject_index("Math") or {}

# --- Quiz Content Loading ---
@st.cache_data
def get_gk_levels_for_topic(topic_id: str) -> list:
    """Retrieves quiz IDs for a given GK topic from the subject index."""
    gk_index = load_gk_index()
    topic_info = gk_index.get('topics_data', {}).get(topic_id, {})
    quizzes = topic_info.get('quizzes', {})
    return sorted(list(quizzes.keys()))

@st.cache_data
def load_gk_questions(quiz_id: str) -> list:
    """Loads questions for a GK quiz and associated metadata into session_state."""
    quiz_data = database_manager.get_quiz(quiz_id)
    if not quiz_data:
        return []
    
    # Store metadata in session state for the quiz view to use
    st.session_state.gk_background = quiz_data.get("background", "")
    st.session_state.gk_icon_legend = quiz_data.get("icon_legend", {})
    st.session_state.gk_reward_text = quiz_data.get("reward", "")
    st.session_state.gk_title = quiz_data.get("title", "GK Quiz") # Top-level title from quiz data
    
    return quiz_data.get("questions", [])

@st.cache_data
def load_math_story(quiz_id: str) -> list: # Changed return type hint as it now returns questions list
    """Loads the content of a math story quiz from Firestore and stores metadata in session_state."""
    quiz_data = database_manager.get_quiz(quiz_id)
    if not quiz_data:
        return []
    
    # Store metadata in session state for the quiz view to use
    st.session_state.math_story_title = quiz_data.get("story_name", "Math Exercise") # Use story_name from new structure
    st.session_state.math_background = quiz_data.get("background", "")
    st.session_state.math_icon_legend = quiz_data.get("icon_legend", {})
    st.session_state.math_reward_text = quiz_data.get("reward", "")
    
    return quiz_data.get("questions", []) # Now returns the questions list directly

# --- Quiz Attempt Management ---
def save_attempt(attempt_data: dict):
    """Saves a detailed quiz attempt to Firestore."""
    username = attempt_data.get("student_name")
    if not username:
        st.error("Cannot save attempt: student_name is missing.")
        return
    database_manager.save_attempt(username, attempt_data)

def get_student_attempts(student_name: str) -> list:
    """Loads all attempt summaries for a given student from Firestore."""
    return database_manager.get_student_attempts(student_name)