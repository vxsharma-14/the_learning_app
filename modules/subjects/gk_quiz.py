import streamlit as st
from datetime import datetime
from modules import data_manager
from modules.navigation import set_view, reset_activity_state

def render():
    """Entry point for the GK Quiz module."""
    if 'selected_gk_topic_id' not in st.session_state:
        st.session_state.selected_gk_topic_id = None
    if 'selected_gk_quiz_id' not in st.session_state:
        st.session_state.selected_gk_quiz_id = None


    if st.session_state.get("quiz_in_progress"): # Use a simpler flag for quiz activity
        _render_activity()
    else:
        _render_selection()

def _render_selection():
    """Displays a dynamic UI for selecting a quiz topic and level from Firestore."""
    st.header("General Knowledge Quiz")
    st.info("Select a topic and a level to start the quiz.")
    
    gk_index = data_manager.load_gk_index()
    if not gk_index or not gk_index.get("topics_data"):
        st.warning("No GK quizzes have been uploaded yet. Please use the Admin dashboard to upload content.")
        if st.button("⬅️ Back to Subjects"):
            reset_activity_state(); set_view("subject_selection")
        return

    available_topics_data = {
        tid: tinfo for tid, tinfo in gk_index['topics_data'].items() if tinfo.get('quizzes')
    }

    if not available_topics_data:
        st.warning("No GK quizzes have been uploaded yet.")
        if st.button("⬅️ Back to Subjects"):
            reset_activity_state(); set_view("subject_selection")
        return

    topic_map = {tid: info['name'] for tid, info in available_topics_data.items()}
    
    current_selected_topic_id = st.session_state.get('selected_gk_topic_id', list(available_topics_data.keys())[0])
    selected_topic_id = st.selectbox(
        "Select Topic", 
        options=list(topic_map.keys()), 
        format_func=lambda x: topic_map.get(x, x),
        key="gk_topic_select",
        index=list(available_topics_data.keys()).index(current_selected_topic_id) if current_selected_topic_id in available_topics_data else 0
    )
    st.session_state.selected_gk_topic_id = selected_topic_id

    if selected_topic_id:
        topic_info = available_topics_data[selected_topic_id]
        quizzes_in_topic = topic_info.get('quizzes', {})

        if not quizzes_in_topic:
            st.warning("No quizzes found for this topic.")
        else:
            # --- Logical Sorting of Levels ---
            level_sort_order = {"Foundation": 0, "Intermediate": 1, "Advanced": 2, "Expert": 3, "Grandmaster": 4}
            
            # Sort the quiz IDs based on the display name's order
            sorted_quiz_ids = sorted(
                quizzes_in_topic.keys(),
                key=lambda qid: level_sort_order.get(quizzes_in_topic[qid]['name'], 99) # Default to 99 for unknown levels
            )
            
            quiz_options_display = {quiz_id: quiz_info['name'] for quiz_id, quiz_info in quizzes_in_topic.items()}
            
            current_selected_quiz_id = st.session_state.get('selected_gk_quiz_id', sorted_quiz_ids[0])
            
            selected_quiz_id = st.selectbox(
                "Select Level", 
                options=sorted_quiz_ids, # Use the sorted list of IDs
                format_func=lambda x: quiz_options_display.get(x, x),
                key="gk_quiz_select",
                index=sorted_quiz_ids.index(current_selected_quiz_id) if current_selected_quiz_id in sorted_quiz_ids else 0
            )
            st.session_state.selected_gk_quiz_id = selected_quiz_id

            if st.button("Start GK Quiz", use_container_width=True):
                st.session_state.questions = data_manager.load_gk_questions(selected_quiz_id)
                if st.session_state.questions:
                    st.session_state.user_answers = {i: None for i in range(len(st.session_state.questions))}
                    st.session_state.score = 0
                    st.session_state.quiz_finished = False
                    st.session_state.show_score_summary = False
                    st.session_state.show_reward = False
                    st.session_state.is_perfect_score = False
                    st.session_state.quiz_in_progress = True # Set flag to indicate quiz is active
                    st.session_state.show_score_summary = False
                    st.session_state.show_reward = False
                    st.session_state.is_perfect_score = False
                    st.rerun()
                else:
                    st.warning("No questions loaded for this quiz.")
    
    st.markdown("---")
    if st.button("⬅️ Back to Subjects", key="back_to_subjects_selection"):
        reset_activity_state(); set_view("subject_selection")

def _render_activity():
    if st.session_state.get("show_reward"):
        _render_reward_view()
    elif st.session_state.get("show_score_summary"):
        _render_score_summary_view()
    elif not st.session_state.get("quiz_finished"):
        _render_quiz_view()
    else:
        _render_results_view()

def _render_quiz_view():
    st.header(st.session_state.get("gk_title", "GK Quiz"), divider="rainbow")

    if st.session_state.get("gk_background"):
        st.info(st.session_state.gk_background)
    if st.session_state.get("gk_icon_legend"):
        legend_text = "  |  ".join([f"{icon}: {value}" for icon, value in st.session_state.gk_icon_legend.items()])
        st.markdown(f"**Legend:** {legend_text}")
    
    st.subheader(f"Answer all {len(st.session_state.questions)} questions and submit:")
    
    for i, q_data in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}: {q_data['prompt']}**")
        
        if i not in st.session_state.user_answers:
            st.session_state.user_answers[i] = None 

        display_options = [f"{opt['key']}. {opt['text']}" for opt in q_data["options"]]
        
        selected_key_from_state = st.session_state.user_answers.get(i)
        selected_display_text = None
        if selected_key_from_state:
            for opt in q_data["options"]:
                if opt["key"] == selected_key_from_state:
                    selected_display_text = f"{opt['key']}. {opt['text']}"
                    break
        
        selected_index = None
        if selected_display_text and selected_display_text in display_options:
            selected_index = display_options.index(selected_display_text)

        selected_radio_text = st.radio(f"Options for Q{i+1}", display_options, index=selected_index, key=f"gk_q_{i}")
        
        if selected_radio_text:
            selected_key = selected_radio_text.split('.')[0]
            st.session_state.user_answers[i] = selected_key 
        st.markdown("---")
    
    if st.button("Submit Quiz ✅", use_container_width=True):
        _calculate_score_and_save()
        if st.session_state.get("is_perfect_score"):
            st.session_state.show_reward = True
        else:
            st.session_state.show_score_summary = True
        st.session_state.quiz_in_progress = False # Reset flag
        st.rerun()

def _render_reward_view():
    st.balloons()
    st.header("Congratulations! 🎉", divider="rainbow")
    st.markdown(f"> {st.session_state.get('gk_reward_text', 'You got a perfect score!')}")
    if st.button("See my Score!"):
        st.session_state.show_reward = False
        st.session_state.show_score_summary = True
        st.rerun()

def _render_score_summary_view():
    st.header("Quiz Completed! 🏆", divider="rainbow")
    st.subheader(f"Your Score: {st.session_state.score}/{len(st.session_state.questions)}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Review Answers", use_container_width=True):
            st.session_state.show_score_summary = False
            st.session_state.quiz_finished = True
            st.rerun()
    with col2:
        if st.button("⬅️ Back to Subjects", use_container_width=True, key="summary_back_to_subjects"):
            reset_activity_state(); set_view("subject_selection")

def _render_results_view():
    st.header("Quiz Results 🏆", divider="rainbow")
    st.write(f"**Score:** {st.session_state.score}/{len(st.session_state.questions)}")

    st.subheader("Question Review:", divider="grey")
    for i, q_data in enumerate(st.session_state.questions):
        st.markdown(f"**Q{i+1}: {q_data['prompt']}**")
        user_choice_key = st.session_state.user_answers.get(i)
        correct_answer_key = q_data["answer"]
        
        for opt in q_data["options"]:
            option_text = f"{opt['key']}. {opt['text']}"
            if opt["key"] == correct_answer_key:
                st.markdown(f"<span style='color: green;'>**✅ {option_text}**</span>", unsafe_allow_html=True)
            elif opt["key"] == user_choice_key:
                st.markdown(f"<span style='color: red;'>**❌ {option_text}**</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; {option_text}", unsafe_allow_html=True)
        st.markdown("---")
    
    st.markdown("---")
    if st.button("⬅️ Back to Subjects", key="back_to_subjects_results"):
        reset_activity_state(); set_view("subject_selection")

def _calculate_score_and_save():
    correct_answers = 0
    questions_with_answers = []
    
    for i, q_data in enumerate(st.session_state.questions):
        user_answer_key = st.session_state.user_answers.get(i)
        correct_answer_key = q_data["answer"]
        
        q_copy = q_data.copy()
        q_copy["user_answer"] = user_answer_key
        questions_with_answers.append(q_copy)

        if user_answer_key == correct_answer_key:
            correct_answers += 1

    st.session_state.score = correct_answers
    st.session_state.is_perfect_score = (correct_answers == len(st.session_state.questions))
    
    gk_index = data_manager.load_gk_index()
    topic_info = gk_index.get("topics_data", {}).get(st.session_state.selected_gk_topic_id, {})
    topic_name = topic_info.get('name', st.session_state.selected_gk_topic_id)
    quiz_info = topic_info.get('quizzes', {}).get(st.session_state.selected_gk_quiz_id, {})
    level_name = quiz_info.get('name', st.session_state.selected_gk_quiz_id)
    
    attempt_data = {
        "student_name": st.session_state.student_name,
        "subject": "GK",
        "level": f"{topic_name} - {level_name}",
        "score": st.session_state.score,
        "total_questions": len(st.session_state.questions),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "questions": questions_with_answers
    }
    data_manager.save_attempt(attempt_data)