import streamlit as st
from datetime import datetime
from modules import data_manager, database_manager
from modules.navigation import set_view, reset_activity_state

# --- Main Entry Point ---

def render():
    """
    Acts as a router, rendering the correct view for the Math module based on session state.
    - Renders the exercise if one is in progress.
    - Renders the story selection screen if a chapter has been chosen.
    - Defaults to the chapter selection screen.
    """
    view = st.session_state.get("math_view", "chapter_selection") # Default to chapter selection

    if st.session_state.get("exercise_in_progress"):
        _render_activity()
    elif view == "story_selection":
        _render_story_selection()
    else:
        _render_chapter_selection()

# --- View-specific Rendering Functions ---

def _render_chapter_selection():
    """Displays the first screen for Math: a dropdown and a button to select a chapter."""
    st.header("Math Exercises 🧮")
    st.info("Please select a chapter to begin.")

    math_index = data_manager.load_math_index()
    if not math_index or not math_index.get("chapters"):
        st.error("No Math content found. Please use the Admin dashboard to upload content.")
        if st.button("⬅️ Back to Subjects"):
            reset_activity_state()
            set_view("subject_selection")
        return

    chapter_map = {chap["id"]: chap["title"] for chap in math_index["chapters"]}
    
    # A simple selectbox to choose the chapter. The selection is stored in its key.
    selected_id = st.selectbox(
        "Select Chapter",
        options=[None] + list(chapter_map.keys()),
        format_func=lambda x: "--- Select a Chapter ---" if x is None else chapter_map.get(x, "Unknown"),
        key="math_chapter_selector" 
    )

    st.write("") # Adding a little space before the buttons

    # Explicit button to navigate to the story selection screen
    if st.button("Next", use_container_width=True):
        if selected_id:
            st.session_state.selected_chapter_id = selected_id
            st.session_state.math_view = "story_selection"
            st.rerun()
        else:
            st.warning("Please select a chapter before proceeding.")

    st.markdown("---")
    if st.button("⬅️ Back to Subjects"):
        reset_activity_state()
        set_view("subject_selection")

def _render_story_selection():
    """
    Displays the second screen: a grid of story cards for the selected chapter.
    This view is only shown after a chapter has been selected.
    """
    selected_chapter_id = st.session_state.get("selected_chapter_id")
    if not selected_chapter_id:
        st.warning("No chapter selected. Returning to chapter selection.")
        st.session_state.math_view = "chapter_selection"
        st.rerun()
        return

    math_index = data_manager.load_math_index()
    chapter_map = {chap["id"]: chap["title"] for chap in math_index["chapters"]}
    chapter_data = next((chap for chap in math_index["chapters"] if chap["id"] == selected_chapter_id), None)
    
    st.header(f"Chapter: {chapter_map.get(selected_chapter_id, 'N/A')}")
    st.info("Select a story to begin. Complete stories with a score of 60% or more to unlock the next one!")
    
    # Advanced CSS for vertical stretching and sticky-footer buttons
    st.markdown("""
        <style>
            /* Make the columns stretch to the height of the tallest one */
            div[data-testid="stHorizontalBlock"] {
                align-items: stretch;
            }
            /* Make the card's container fill the available vertical space */
            [data-testid="stVerticalBlock"] > div[data-testid="stAppViewContainer"] {
                height: 100%;
            }
            /* Make the card a flex column, allowing content to push the button down */
            [data-testid="stVerticalBlock"] > div[data-testid="stAppViewContainer"] > div[data-testid="stContainer"] {
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            /* Make the main content area of the card grow */
            [data-testid="stVerticalBlock"] > div[data-testid="stAppViewContainer"] > div[data-testid="stContainer"] > div[data-testid="stVerticalBlock"]:first-child {
                flex-grow: 1;
            }
            /* Add margin between rows */
             [data-testid="stHorizontalBlock"] {
                margin-bottom: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)

    if not chapter_data or not chapter_data.get("stories"):
        st.info("No stories available in this chapter yet.")
    else:
        # Fetch user progress
        user_progress = database_manager.get_user_progress(st.session_state.student_name)
        math_progress = user_progress.get("math", {})
        
        cols = st.columns(3)
        previous_story_passed = True

        for i, story in enumerate(chapter_data["stories"]):
            story_file = story["file"]
            story_id = story_file.replace(".json", "")
            story_name = story["name"]

            user_story_progress = math_progress.get(selected_chapter_id, {}).get("stories", {}).get(story_id, {})
            best_score_percent = user_story_progress.get("best_score_percent", -1)
            stars_earned = user_story_progress.get("stars", 0)
            
            is_locked = (i > 0) and not previous_story_passed

            with cols[i % 3]:
                with st.container(border=True):
                    # Top container that grows
                    with st.container():
                        st.subheader(story_name)
                        if story.get("topics"):
                            st.caption(f"Topics: {', '.join(story['topics'])}")
                        else:
                            st.caption("\u00A0") # Non-breaking space

                        star_display = '⭐' * stars_earned if stars_earned > 0 else '&nbsp;'
                        st.markdown(f"<div style='text-align: right; font-size: 1.5em; color: orange; min-height: 30px;'>{star_display}</div>", unsafe_allow_html=True)
                    
                    # Bottom container for the button
                    button_label = "Start"
                    if is_locked:
                        button_label = "Locked 🔒"
                    
                    start_button_key = f"start_math_{selected_chapter_id}_{story_id}"
                    if st.button(button_label, key=start_button_key, disabled=is_locked, use_container_width=True):
                        _start_exercise(selected_chapter_id, story)

            if best_score_percent < 60:
                previous_story_passed = False
    
    st.markdown("---")
    if st.button("⬅️ Back to Chapters"):
        st.session_state.math_view = "chapter_selection"
        st.session_state.selected_chapter_id = None
        st.rerun()

# --- Helper function to start an exercise ---

def _start_exercise(chapter_id: str, story_data: dict):
    """Initializes session state and starts a new math exercise."""
    math_index = data_manager.load_math_index()
    chapter_map = {chap["id"]: chap["title"] for chap in math_index["chapters"]}

    story_file = story_data["file"]
    story_id = story_file.replace(".json", "")
    story_name = story_data["name"]

    quiz_id = f"math_{chapter_id}_{story_id}"
    questions = data_manager.load_math_story(quiz_id)

    if questions:
        st.session_state.questions = questions
        st.session_state.selected_chapter_id = chapter_id
        st.session_state.selected_story_file = story_file
        st.session_state.selected_chapter_name = chapter_map.get(chapter_id, "N/A")
        st.session_state.selected_story_name = story_name
        
        # Initialize answers
        user_answers_init = {q["id"]: [] if q.get("type") == "multi_choice" else None for q in questions}
        st.session_state.user_answers = user_answers_init
        
        # Reset quiz state variables
        st.session_state.score = 0
        st.session_state.quiz_finished = False
        st.session_state.show_score_summary = False
        st.session_state.show_reward = False
        st.session_state.is_perfect_score = False
        
        # Set flag to start the activity on the next rerun
        st.session_state.exercise_in_progress = True
        st.rerun()
    else:
        st.error(f"Could not load story: {quiz_id}. The data might be missing.")

# --- Helper function for multi-choice callback ---
def _handle_multichoice_selection(q_id, option_key):
    """Adds or removes an option from the user's answer list for a multi-choice question."""
    if q_id not in st.session_state.user_answers or st.session_state.user_answers[q_id] is None:
        st.session_state.user_answers[q_id] = []
    
    if option_key in st.session_state.user_answers[q_id]:
        st.session_state.user_answers[q_id].remove(option_key)
    else:
        st.session_state.user_answers[q_id].append(option_key)

# --- Activity Rendering (Quiz in Progress) ---

def _render_activity():
    """Renders the main quiz/exercise UI, results, or rewards screens."""
    if st.session_state.get("show_reward"):
        _render_reward_view()
    elif st.session_state.get("show_score_summary"):
        _render_score_summary_view()
    elif not st.session_state.get("quiz_finished"):
        _render_exercise_view()
    else:
        _render_results_view()

def _render_exercise_view():
    st.header(f"Math: {st.session_state.get('selected_chapter_name', 'Chapter')}", divider="rainbow")
    st.subheader(f"Story: {st.session_state.get('selected_story_name', 'Story')}")

    if st.session_state.get("math_background"):
        st.info(st.session_state.math_background)
    if st.session_state.get("math_icon_legend"):
        legend_text = "  |  ".join([f"{icon}: {value}" for icon, value in st.session_state.math_icon_legend.items()])
        st.markdown(f"**Legend:** {legend_text}")
    
    st.subheader(f"Answer all {len(st.session_state.questions)} questions and submit:")
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1})** {q['prompt']}")
        q_id = q['id']; q_type = q.get('type', 'text')
        
        if q_id not in st.session_state.user_answers:
            st.session_state.user_answers[q_id] = [] if q_type == "multi_choice" else None

        if q_type == "single_choice":
            display_options = [f"{opt['key']}. {opt['text']}" for opt in q['options']]
            selected_key_from_state = st.session_state.user_answers.get(q_id)
            selected_display_text = next((opt for opt in display_options if opt.startswith(f"{selected_key_from_state}.")), None)
            selected_index = display_options.index(selected_display_text) if selected_display_text else None
            
            selected_radio_text = st.radio(f"Options for Q{i+1}", display_options, index=selected_index, key=f"math_q_{q_id}")
            if selected_radio_text:
                st.session_state.user_answers[q_id] = selected_radio_text.split('.')[0]
        
        elif q_type == "text":
            st.session_state.user_answers[q_id] = st.text_input("Your Answer:", value=st.session_state.user_answers.get(q_id, ""), key=f"math_q_{q_id}")
        
        elif q_type == "multi_choice":
            current_selections = st.session_state.user_answers.get(q_id) or []
            for opt in q['options']:
                st.checkbox(f"{opt['key']}. {opt['text']}", value=(opt['key'] in current_selections), key=f"math_q_{q_id}_{opt['key']}", on_change=_handle_multichoice_selection, args=(q_id, opt['key']))
        st.markdown("---")
    
    if st.button("Submit Exercise ✅", use_container_width=True):
        _calculate_score_and_save()
        if st.session_state.get("is_perfect_score"): st.session_state.show_reward = True
        else: st.session_state.show_score_summary = True
        st.session_state.exercise_in_progress = True # Keep this true to stay in activity view
        st.rerun()

def _render_reward_view():
    st.balloons()
    st.header("Congratulations! 🎉", divider="rainbow")
    st.markdown(f"> {st.session_state.get('math_reward_text', 'You got a perfect score!')}")
    if st.button("See my Score!"):
        st.session_state.show_reward = False; st.session_state.show_score_summary = True; st.rerun()

def _render_score_summary_view():
    st.header("Exercise Completed! 🏆", divider="rainbow")
    st.subheader(f"Your Score: {st.session_state.score}/{len(st.session_state.questions)}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Review Answers", use_container_width=True):
            st.session_state.show_score_summary = False; st.session_state.quiz_finished = True; st.rerun()
    with col2:
        if st.button("⬅️ Back to Stories", use_container_width=True, key="summary_back_to_stories_math"):
            # Go back to the story selection screen of the same chapter
            st.session_state.exercise_in_progress = False
            st.session_state.math_view = "story_selection"
            # Reset quiz-specific state
            st.session_state.pop('quiz_finished', None)
            st.session_state.pop('show_score_summary', None)
            st.rerun()

def _render_results_view():
    st.header("Exercise Results", divider="blue")
    st.write(f"**Score:** {st.session_state.score}/{len(st.session_state.questions)}")
    st.subheader("Question Review:", divider="grey")
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1})** {q['prompt']}")
        user_answer_key = st.session_state.user_answers.get(q['id'])
        correct_answer_key = q['answer']
        
        q_type = q.get('type', 'text')
        is_correct = False
        if q_type == "text": is_correct = str(user_answer_key).strip().lower() == str(correct_answer_key).strip().lower()
        elif q_type == "single_choice": is_correct = user_answer_key == correct_answer_key
        elif q_type == "multi_choice": is_correct = sorted(user_answer_key or []) == sorted(correct_answer_key or [])
        
        user_answer_display = ""
        correct_answer_display = ""

        if q_type in ["single_choice", "multi_choice"]:
            # Create a lookup map for option text
            options_map = {opt['key']: opt['text'] for opt in q.get('options', [])}
            
            # Format user's answer
            user_keys = user_answer_key if isinstance(user_answer_key, list) else [user_answer_key]
            user_choices_text = [f"{k}. {options_map.get(k, 'N/A')}" for k in user_keys if k]
            user_answer_display = ' | '.join(user_choices_text) if user_choices_text else "No Answer"

            # Format correct answer
            correct_keys = correct_answer_key if isinstance(correct_answer_key, list) else [correct_answer_key]
            correct_choices_text = [f"{k}. {options_map.get(k, 'N/A')}" for k in correct_keys if k]
            correct_answer_display = ' | '.join(correct_choices_text)
        else: # Text input
            user_answer_display = user_answer_key if user_answer_key is not None else "No Answer"
            correct_answer_display = correct_answer_key

        if is_correct: 
            st.markdown(f"<span style='color: green;'>Your answer: **{user_answer_display}** ✅</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color: red;'>Your answer: **{user_answer_display}** ❌</span>", unsafe_allow_html=True)
            st.markdown(f"<span style='color: green;'>Correct answer: **{correct_answer_display}**</span>", unsafe_allow_html=True)
        st.markdown("---")
    
    st.markdown("---")
    if st.button("⬅️ Back to Stories", key="results_back_to_stories_math"):
        st.session_state.exercise_in_progress = False
        st.session_state.math_view = "story_selection"
        # Reset quiz-specific state
        st.session_state.pop('quiz_finished', None)
        st.session_state.pop('show_score_summary', None)
        st.rerun()

def _calculate_score_and_save():
    correct_answers = 0; questions_with_answers = []
    for q_data in st.session_state.questions:
        q_id = q_data["id"]; q_type = q_data.get("type", "text"); user_answer_key = st.session_state.user_answers.get(q_id); correct_answer_key = q_data["answer"]; is_correct = False
        if q_type == "text": is_correct = str(user_answer_key).strip().lower() == str(correct_answer_key).strip().lower()
        elif q_type == "single_choice": is_correct = user_answer_key == correct_answer_key
        elif q_type == "multi_choice": is_correct = sorted(user_answer_key or []) == sorted(correct_answer_key or [])
        if is_correct: correct_answers += 1
        
        q_copy = q_data.copy()
        q_copy["user_answer"] = user_answer_key
        questions_with_answers.append(q_copy)

    st.session_state.score = correct_answers
    total_questions = len(st.session_state.questions)
    st.session_state.is_perfect_score = (correct_answers == total_questions)
    
    score_percent = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    stars_earned = 0
    if score_percent >= 90: stars_earned = 3
    elif score_percent >= 80: stars_earned = 2
    elif score_percent >= 70: stars_earned = 1

    # Get IDs needed for update_user_progress
    username = st.session_state.student_name
    subject = "Math"
    chapter_id = st.session_state.get("selected_chapter_id")
    story_id = st.session_state.get("selected_story_file", "").replace(".json", "")

    if chapter_id and story_id:
        database_manager.update_user_progress(username, subject, chapter_id, story_id, int(score_percent), stars_earned)
    
    attempt_data = {
        "student_name": st.session_state.student_name,
        "subject": "Math",
        "level": st.session_state.get("selected_chapter_name", "N/A"),
        "story": st.session_state.get("selected_story_name", "N/A"),
        "score": st.session_state.score,
        "total_questions": total_questions,
        "score_percent": int(score_percent),
        "stars_earned": stars_earned,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "questions": questions_with_answers
    }
    data_manager.save_attempt(attempt_data)