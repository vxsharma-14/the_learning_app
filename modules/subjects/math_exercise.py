import streamlit as st
from datetime import datetime
from modules import data_manager
from modules.navigation import set_view, reset_activity_state

# --- Helper function for multi-choice callback ---
def _handle_multichoice_selection(q_id, option_key):
    """Adds or removes an option from the user's answer list for a multi-choice question."""
    if q_id not in st.session_state.user_answers or st.session_state.user_answers[q_id] is None:
        st.session_state.user_answers[q_id] = []
    
    if option_key in st.session_state.user_answers[q_id]:
        st.session_state.user_answers[q_id].remove(option_key)
    else:
        st.session_state.user_answers[q_id].append(option_key)

def render():
    """Entry point for the Math Exercise module."""
    if 'start_time' not in st.session_state or st.session_state.start_time is None:
        _render_selection()
    else:
        _render_activity()

def _render_selection():
    """Displays UI for selecting a math chapter and story from Firestore."""
    st.header("Math Exercises 🧮")
    st.info("Select a chapter and a story to begin.")

    math_index = data_manager.load_math_index()
    if not math_index or not math_index.get("chapters"):
        st.error("No Math content found in the database. Please use the Admin dashboard to upload content.")
        if st.button("⬅️ Back to Subjects"):
            reset_activity_state(); set_view("subject_selection")
        return

    chapter_map = {chap["id"]: chap["title"] for chap in math_index["chapters"]}
    selected_chapter_id = st.selectbox("Select Chapter", options=list(chapter_map.keys()), format_func=lambda x: chapter_map.get(x, x))

    if selected_chapter_id:
        chapter_data = next((chap for chap in math_index["chapters"] if chap["id"] == selected_chapter_id), None)
        
        if chapter_data and chapter_data.get("stories"):
            story_map = {story["file"]: story["name"] for story in chapter_data["stories"]}
            selected_story_file = st.selectbox("Select Story", options=list(story_map.keys()), format_func=lambda x: story_map.get(x, x))

            if st.button("Start Exercise", use_container_width=True):
                quiz_id = f"math_{selected_chapter_id}_{selected_story_file.replace('.json', '')}"
                # load_math_story now returns the questions list and sets metadata in session state
                questions = data_manager.load_math_story(quiz_id)

                if questions:
                    st.session_state.questions = questions
                    # Store names for display in other views
                    st.session_state.selected_chapter_name = chapter_map[selected_chapter_id]
                    st.session_state.selected_story_name = story_map[selected_story_file]

                    # Initialize quiz state
                    user_answers_init = {}
                    for q in st.session_state.questions:
                        user_answers_init[q["id"]] = [] if q.get("type") == "multi_choice" else None
                    st.session_state.user_answers = user_answers_init
                    
                    st.session_state.score = 0
                    st.session_state.time_taken = 0
                    st.session_state.start_time = datetime.now()
                    st.session_state.quiz_finished = False
                    st.session_state.show_score_summary = False
                    st.session_state.show_reward = False
                    st.session_state.is_perfect_score = False
                    st.rerun()
                else:
                    st.error("Could not load story from database. The document might be empty or missing.")
    
    st.markdown("---")
    if st.button("⬅️ Back to Subjects", key="math_back_to_subjects"):
        reset_activity_state(); set_view("subject_selection")

def _render_activity():
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
            selected_display_text = None
            if selected_key_from_state:
                for opt in q["options"]:
                    if opt["key"] == selected_key_from_state:
                        selected_display_text = f"{opt['key']}. {opt['text']}"
                        break
            selected_index = display_options.index(selected_display_text) if selected_display_text in display_options else None
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
        st.session_state.time_taken = (datetime.now() - st.session_state.start_time).total_seconds()
        _calculate_score_and_save()
        if st.session_state.get("is_perfect_score"): st.session_state.show_reward = True
        else: st.session_state.show_score_summary = True
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
    st.write(f"Time Taken: {int(st.session_state.time_taken)} seconds")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Review Answers", use_container_width=True):
            st.session_state.show_score_summary = False; st.session_state.quiz_finished = True; st.rerun()
    with col2:
        if st.button("⬅️ Back to Subjects", use_container_width=True, key="summary_back_to_subjects_math"):
            reset_activity_state(); set_view("subject_selection")

def _render_results_view():
    st.header("Exercise Results", divider="blue")
    st.write(f"**Score:** {st.session_state.score}/{len(st.session_state.questions)}")
    st.write(f"**Time Taken:** {int(st.session_state.time_taken)} seconds")
    st.subheader("Question Review:", divider="grey")
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1})** {q['prompt']}")
        user_answer_key = st.session_state.user_answers.get(q['id'])
        correct_answer_key = q['answer']
        
        q_type = q.get('type', 'text')
        is_correct = False
        if q_type == "text": is_correct = str(user_answer_key).strip().lower() == str(correct_answer_key).strip().lower()
        elif q_type == "single_choice": is_correct = user_answer_key == correct_answer_key
        elif q_type == "multi_choice": is_correct = sorted(user_answer_key) == sorted(correct_answer_key) if isinstance(user_answer_key, list) else False
        
        if q_type in ["single_choice", "multi_choice"]:
            user_choices_text = []
            if isinstance(user_answer_key, list):
                for opt in q['options']:
                    if opt['key'] in user_answer_key: user_choices_text.append(f"{opt['key']}. {opt['text']}")
            elif user_answer_key:
                 for opt in q['options']:
                    if opt['key'] == user_answer_key: user_choices_text.append(f"{opt['key']}. {opt['text']}"); break
            
            correct_choices_text = []
            correct_keys = correct_answer_key if isinstance(correct_answer_key, list) else [correct_answer_key]
            for opt in q['options']:
                if opt['key'] in correct_keys: correct_choices_text.append(f"{opt['key']}. {opt['text']}")

            if is_correct: st.markdown(f"<span style='color: green;'>Your answer: **{' | '.join(user_choices_text)}** ✅</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: red;'>Your answer: **{' | '.join(user_choices_text) if user_choices_text else 'No Answer'}** ❌</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color: green;'>Correct answer: **{' | '.join(correct_choices_text)}**</span>", unsafe_allow_html=True)
        else: # Text input
            user_answer_display = user_answer_key if user_answer_key is not None else "No Answer"
            if is_correct: st.markdown(f"<span style='color: green;'>Your answer: **{user_answer_display}** ✅</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: red;'>Your answer: **{user_answer_display}** ❌</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color: green;'>Correct answer: **{correct_answer_key}**</span>", unsafe_allow_html=True)
        st.markdown("---")
    
    st.markdown("---")
    if st.button("⬅️ Back to Subjects", key="back_to_subjects_results_math"):
        reset_activity_state(); set_view("subject_selection")

def _calculate_score_and_save():
    correct_answers = 0; questions_with_answers = []
    for q_data in st.session_state.questions:
        q_id = q_data["id"]; q_type = q_data.get("type", "text"); user_answer_key = st.session_state.user_answers.get(q_id); correct_answer_key = q_data["answer"]; is_correct = False
        if q_type == "text": is_correct = str(user_answer_key).strip().lower() == str(correct_answer_key).strip().lower()
        elif q_type == "single_choice": is_correct = user_answer_key == correct_answer_key
        elif q_type == "multi_choice": is_correct = sorted(user_answer_key) == sorted(correct_answer_key) if isinstance(user_answer_key, list) else False
        if is_correct: correct_answers += 1
        
        q_copy = q_data.copy()
        q_copy["user_answer"] = user_answer_key
        questions_with_answers.append(q_copy)

    st.session_state.score = correct_answers
    st.session_state.is_perfect_score = (correct_answers == len(st.session_state.questions))
    
    attempt_data = {
        "student_name": st.session_state.student_name,
        "subject": "Math",
        "level": st.session_state.get("selected_chapter_name", "N/A"),
        "story": st.session_state.get("selected_story_name", "N/A"),
        "score": st.session_state.score,
        "total_questions": len(st.session_state.questions),
        "time_taken": int(st.session_state.time_taken),
        "timestamp": st.session_state.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "questions": questions_with_answers
    }
    data_manager.save_attempt(attempt_data)