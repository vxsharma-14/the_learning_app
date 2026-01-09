import streamlit as st
import pandas as pd
import plotly.express as px
from modules import data_manager

def _render_analysis_view(selected_data: dict):
    """Displays a generic, unified analysis for any quiz attempt."""
    st.subheader(f"Analysis for Quiz on {selected_data['timestamp']}", divider="blue")

    topic_scores = {}
    questions = selected_data.get("questions", [])

    if not questions:
        st.warning("This quiz attempt has no question data to analyze.")
        return

    for q in questions:
        topic = q.get("topic", "General")
        if topic not in topic_scores:
            topic_scores[topic] = {"correct": 0, "total": 0}
        topic_scores[topic]["total"] += 1

        # --- Unified and Robust Correctness Check ---
        is_correct = False
        q_type = q.get("type")
        user_answer = q.get("user_answer")
        correct_answer_key = q.get("answer")

        if q_type == "single_choice":
            # First, check if the stored answer is the KEY (new, correct format)
            if user_answer == correct_answer_key:
                is_correct = True
            # Fallback: check if the stored answer is the TEXT (old, incorrect format)
            else:
                for opt in q.get("options", []):
                    if opt.get("key") == correct_answer_key and opt.get("text") == user_answer:
                        is_correct = True
                        break
        
        elif q_type == "multi_choice":
            # This logic should be safe as multi-choice has always stored a list of keys
            is_correct = sorted(user_answer or []) == sorted(correct_answer_key or [])

        elif q_type == "text":
            is_correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()

        if is_correct:
            topic_scores[topic]["correct"] += 1
    
    # --- Chart Generation ---
    chart_data = []
    for topic, scores in topic_scores.items():
        chart_data.append({
            "Topic": topic,
            "Correct": scores["correct"],
            "Total": scores["total"],
            "Percentage": (scores["correct"] / scores["total"]) * 100 if scores["total"] > 0 else 0
        })
    df_chart = pd.DataFrame(chart_data)

    if not df_chart.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Performance per Topic")
            df_chart['ScoreText'] = df_chart['Correct'].astype(str) + '/' + df_chart['Total'].astype(str)
            fig_bar = px.bar(df_chart, x='Topic', y='Correct', text='ScoreText', color='Percentage',
                                color_continuous_scale=px.colors.diverging.RdYlGn, range_color=[0, 100],
                                title='Topic-wise Score')
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(yaxis_title="Correct Answers", xaxis_title="Topic")
            st.plotly_chart(fig_bar, use_container_width=True)
        with col2:
            st.markdown("#### Correct Answers Distribution")
            df_pie = df_chart[df_chart['Correct'] > 0]
            if not df_pie.empty:
                fig_pie = px.pie(df_pie, names='Topic', values='Correct', title='Distribution of Correct Answers', hole=.3)
                fig_pie.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No questions were answered correctly to show distribution.")
    else:
        st.info("No topic data available to generate analysis charts for this attempt.")

    if st.button("Close Analysis", key="close_analysis"):
        st.session_state.selected_attempt_file = None
        st.rerun()

def render():
    """Displays the historical quiz data and analysis for the logged-in student."""
    st.header("Student Dashboard 📊", divider="rainbow")
    st.info(f"Reviewing past attempts for **{st.session_state.student_name}**.")

    if 'selected_attempt_file' not in st.session_state:
        st.session_state.selected_attempt_file = None

    student_attempts = data_manager.get_student_attempts(st.session_state.student_name)

    if not student_attempts:
        st.success("You have no previous attempts. Start a new quiz!")
        return

    # Group attempts by subject
    attempts_by_subject = {}
    for attempt in student_attempts:
        subject = attempt.get("subject", "N/A")
        if subject not in attempts_by_subject:
            attempts_by_subject[subject] = []
        attempts_by_subject[subject].append(attempt)

    tab_keys = sorted(attempts_by_subject.keys())
    display_tab_names = [k.capitalize() for k in tab_keys]
    subject_tabs = st.tabs(display_tab_names)

    for i, subject_id in enumerate(tab_keys):
        with subject_tabs[i]:
            st.subheader(f"Your Past {subject_id.capitalize()} Quizzes")
            
            # --- Render Table Header ---
            if subject_id == "GK":
                cols = st.columns([2, 3, 2, 2])
                cols[0].write("**Date**"); cols[1].write("**Level**"); cols[2].write("**Score**"); cols[3].write("**Action**")
            elif subject_id == "Math":
                cols = st.columns([2, 3, 3, 2, 2])
                cols[0].write("**Date**"); cols[1].write("**Chapter**"); cols[2].write("**Story**"); cols[3].write("**Score**"); cols[4].write("**Action**")

            # --- Render Table Rows ---
            for attempt in attempts_by_subject[subject_id]:
                if subject_id == "GK":
                    cols = st.columns([2, 3, 2, 2])
                    cols[0].write(attempt["timestamp"].split(" ")[0])
                    cols[1].write(attempt.get("level", "N/A"))
                    cols[2].write(f"{attempt['score']}/{attempt['total_questions']}")
                    if cols[3].button("Analyze", key=f"analyze_{attempt['filename']}"):
                        st.session_state.selected_attempt_file = attempt['filename']
                        st.rerun()
                elif subject_id == "Math":
                    cols = st.columns([2, 3, 3, 2, 2])
                    cols[0].write(attempt["timestamp"].split(" ")[0])
                    cols[1].write(attempt.get("level", "N/A")) # Chapter
                    cols[2].write(attempt.get("story", "N/A"))
                    cols[3].write(f"{attempt['score']}/{attempt['total_questions']}")
                    if cols[4].button("Analyze", key=f"analyze_{attempt['filename']}"):
                        st.session_state.selected_attempt_file = attempt['filename']
                        st.rerun()
    
    st.markdown("---")

    # --- Analysis Section (using st.expander) ---
    if st.session_state.get("selected_attempt_file"):
        selected_attempt = next((att for att in student_attempts if att["filename"] == st.session_state.selected_attempt_file), None)
        if selected_attempt:
            with st.expander("Quiz Analysis", expanded=True):
                _render_analysis_view(selected_attempt)
