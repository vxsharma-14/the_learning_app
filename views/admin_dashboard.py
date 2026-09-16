import streamlit as st
import json
import pandas as pd
from modules import database_manager

def _render_smart_quiz_uploader():
    """Renders a user-friendly UI to upload quiz content and update indices."""
    st.subheader("Smart Quiz Uploader")

    with st.expander("Upload a New Quiz", expanded=True):
        
        uploaded_file = st.file_uploader("Upload Quiz JSON File", type="json", key="smart_upload")
        
        if uploaded_file is not None:
            try:
                quiz_content = json.loads(uploaded_file.getvalue().decode("utf-8"))
                st.success("File loaded successfully. Please verify the details below and upload.")

                subject = quiz_content.get("subject", "N/A").upper()

                if subject == "GK":
                    st.markdown("---")
                    st.write("**Review GK Quiz Details:**")
                    topic_id = quiz_content.get("topic_id", "")
                    title = quiz_content.get("title", "")
                    level = quiz_content.get("level", "")
                    level_file = f"{level.lower().replace(' ', '_')}.json" if level else ""

                    st.text_input("Subject", value=subject, disabled=True)
                    st.text_input("Topic ID", value=topic_id, disabled=True)
                    st.text_input("Topic Display Name", value=title, disabled=True)
                    st.text_input("Level Filename", value=level_file, disabled=True)
                    st.text_input("Level Display Name", value=level, disabled=True)
                    
                    if st.button("Confirm and Upload GK Quiz"):
                        if all([topic_id, title, level_file, level, uploaded_file]): # Added uploaded_file to check
                            quiz_id = f"gk_{topic_id}_{level_file.replace('.json', '')}"
                            database_manager.upload_gk_quiz(
                                quiz_id=quiz_id, quiz_data=quiz_content, topic_id=topic_id,
                                topic_name=title, level_file=level_file, level_name=level
                            )
                            st.success(f"Successfully uploaded and indexed quiz '{quiz_id}'!")
                            st.cache_data.clear()
                            st.toast("Upload successful! Cache cleared.")
                        else:
                            st.error("The uploaded JSON is missing required fields: 'topic_id', 'title', 'level', or no file uploaded.")

                elif subject == "MATH":
                    st.markdown("---")
                    st.write("**Review Math Story Details:**")
                    # Get IDs from JSON
                    chapter_id_num = quiz_content.get("chapter_id")
                    story_id_num = quiz_content.get("story_id")
                    
                    # Get display names from JSON
                    chapter_name = quiz_content.get("title", "")
                    story_name = quiz_content.get("story_name", "")
                    story_file_from_json = quiz_content.get("story_file", "") # Get directly from JSON

                    # Construct stable string IDs for use in quiz_id
                    chapter_id_str = f"chapter{chapter_id_num}" if chapter_id_num is not None else ""
                    story_id_str = f"story{story_id_num}" if story_id_num is not None else ""

                    st.text_input("Subject", value=subject, disabled=True)
                    st.text_input("Chapter ID (from JSON)", value=chapter_id_str, disabled=True)
                    st.text_input("Chapter Display Name (from JSON)", value=chapter_name, disabled=True)
                    st.text_input("Story Filename (from JSON)", value=story_file_from_json, disabled=True)
                    st.text_input("Story Display Name (from JSON)", value=story_name, disabled=True)

                    if st.button("Confirm and Upload Math Story"):
                        if all([chapter_id_str, chapter_name, story_file_from_json, story_name, uploaded_file]): # All required fields
                            quiz_id = f"math_{chapter_id_str}_{story_id_str}"
                            database_manager.upload_math_quiz(
                                quiz_id=quiz_id, quiz_data=quiz_content, chapter_id=chapter_id_str,
                                chapter_name=chapter_name, story_file=story_file_from_json, story_name=story_name
                            )
                            st.success(f"Successfully uploaded and indexed story '{quiz_id}'!")
                            st.cache_data.clear()
                            st.toast("Upload successful! Cache cleared.")
                        else:
                            st.error("The uploaded JSON is missing required fields: 'chapter_id', 'story_id', 'title', 'story_name', 'story_file', or no file uploaded.")
                else:
                    st.error(f"Unknown subject '{subject}' found in JSON file. Please specify 'GK' or 'Math'.")

            except json.JSONDecodeError:
                st.error("Invalid JSON file. Could not parse the content.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

def _render_quiz_management():
    _render_smart_quiz_uploader()
    st.markdown("---")

    with st.expander("Delete a Quiz"):
        st.write("Select a quiz document to permanently delete it. Note: This does not automatically remove it from the index. Manual cleanup may be required.")
        
        try:
            all_quizzes = database_manager.get_all_documents("quizzes")
            quiz_ids = [quiz.id for quiz in all_quizzes]
            if not quiz_ids:
                st.info("No quizzes found in the database.")
            else:
                selected_quiz_id_to_delete = st.selectbox("Select Quiz ID to Delete", options=quiz_ids)
                if st.button("Delete Quiz", type="primary"):
                    if selected_quiz_id_to_delete:
                        database_manager.delete_document("quizzes", selected_quiz_id_to_delete)
                        st.success(f"Successfully deleted quiz: {selected_quiz_id_to_delete}")
                        st.cache_data.clear()
                        st.toast("Quiz deleted! Cache cleared.", icon="🗑️")
                        st.rerun()
                    else:
                        st.warning("Please select a quiz to delete.")
        except Exception as e:
            st.error(f"Failed to load quizzes: {e}")

def _render_user_management():
    st.subheader("User Management")
    st.write("Here you can view and delete user accounts. Deleting a user is permanent and will also remove all their quiz attempts.")
    try:
        all_users = database_manager.get_all_documents("users")
        usernames = [user.id for user in all_users]
        if not usernames:
            st.info("No users found in the database.")
        else:
            for username in sorted(usernames):
                if username == "admin": continue
                col1, col2 = st.columns([4, 1])
                with col1: st.write(username)
                with col2:
                    if st.button("Delete", key=f"delete_user_{username}", type="primary"):
                        database_manager.delete_user_and_subcollections(username)
                        st.success(f"Successfully deleted user: {username}")
                        st.toast(f"User {username} deleted!", icon="🗑️")
                        st.rerun()
                st.markdown("---")
    except Exception as e:
        st.error(f"Failed to load users: {e}")

def _render_analytics_dashboard():
    st.subheader("Usage Analytics")

    with st.spinner("Fetching usage data..."):
        all_users_docs = database_manager.get_all_users() # Already excludes admin
        all_attempts = database_manager.get_all_attempts()

    num_users = len(all_users_docs)
    num_attempts = len(all_attempts)

    st.markdown("### Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Active Users (excl. admin)", num_users)
    col2.metric("Total Quizzes Attempted", num_attempts)
    if num_users > 0:
        col3.metric("Avg. Attempts per User", f"{num_attempts / num_users:.2f}")
    else:
        col3.metric("Avg. Attempts per User", "N/A")

    if not all_attempts:
        st.info("No quiz attempts recorded yet for active users.")
        return

    attempts_df = pd.DataFrame(all_attempts)
    # Ensure correct data types for easier analysis
    attempts_df['timestamp'] = pd.to_datetime(attempts_df['timestamp'])
    
    st.markdown("---")
    st.markdown("### Quizzes Attempted per User")
    attempts_per_user = attempts_df.groupby('student_name').size().sort_values(ascending=False)
    st.dataframe(attempts_per_user.reset_index(name='Attempts'))
    st.bar_chart(attempts_per_user)

    st.markdown("---")
    st.markdown("### Quizzes Attempted by Subject")
    attempts_by_subject = attempts_df.groupby('subject').size().sort_values(ascending=False)
    st.dataframe(attempts_by_subject.reset_index(name='Attempts'))
    st.bar_chart(attempts_by_subject)

    st.markdown("---")
    st.markdown("### Attempts by GK Topic and Level")
    gk_attempts = attempts_df[attempts_df['subject'] == 'GK']
    if not gk_attempts.empty:
        attempts_by_gk_level = gk_attempts.groupby(['level']).size().sort_values(ascending=False)
        st.dataframe(attempts_by_gk_level.reset_index(name='Attempts'))
        st.bar_chart(attempts_by_gk_level)
    else:
        st.info("No GK quiz attempts recorded yet.")

    st.markdown("---")
    st.markdown("### Attempts by Math Chapter and Story")
    math_attempts = attempts_df[attempts_df['subject'] == 'Math']
    if not math_attempts.empty:
        # Group by both, then reset index to make 'level' and 'story' regular columns
        attempts_by_math_story_df = math_attempts.groupby(['level', 'story']).size().reset_index(name='Attempts')
        # Sort the results for better visualization
        attempts_by_math_story_df = attempts_by_math_story_df.sort_values('Attempts', ascending=False)
        
        st.dataframe(attempts_by_math_story_df) # Display the detailed data

        # Create a new column for a combined X-axis label
        attempts_by_math_story_df['Story'] = attempts_by_math_story_df['level'] + " - " + attempts_by_math_story_df['story']
        
        # Plot the chart using the new simplified DataFrame structure
        st.bar_chart(attempts_by_math_story_df, x='Story', y='Attempts')
    else:
        st.info("No Math exercise attempts recorded yet.")


def render():
    """Renders the Admin Dashboard page."""
    st.title("Admin Dashboard ⚙️")
    st.info("Welcome, Admin! Use the tools below to manage the application's content and users.")
    tab1, tab2, tab3 = st.tabs(["Quiz Management", "User Management", "Usage Analytics"])
    with tab1:
        _render_quiz_management()
    with tab2:
        _render_user_management()
    with tab3:
        _render_analytics_dashboard()
