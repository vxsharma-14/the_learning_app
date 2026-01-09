import streamlit as st
from modules.navigation import set_view

def render():
    """Renders the Home page."""
    st.title("A Father's Gift, A Learning Adventure")
    st.markdown(
        """
        It all started with my daughter, a bright and curious 2nd grader. I wanted to find a way to make her practice time more engaging and fun. I noticed that while she loved learning new things, the repetitive nature of traditional practice worksheets was not very exciting for her.

        So, I decided to create something special for her - a simple app where she could practice her school subjects in a more interactive and playful way. I started with Math, creating exercises that were aligned with her **CBSE coursebooks and workbooks**. The goal was to build her confidence and help her master the concepts she was learning in school.

        To my delight, she loved it! She was excited to practice and was genuinely enjoying the experience. Seeing her progress and how much fun she was having, I realized that this little project could benefit other children as well.

        That's when I decided to share this app with a wider audience. My hope is that other students, just like my daughter, can find joy in learning and build a strong foundation for their future. This app is a labor of love, and I am continuously working to add more subjects and features to make it an even better learning companion for your child.
        """
    )

    st.markdown("---")

    # --- Privacy Notice ---
    @st.dialog("Privacy & Data Usage Notice")
    def privacy_dialog():
        st.markdown(
            """
            We are committed to protecting your child's privacy. Here’s what you need to know:
            - Minimal Data: We require a parent/guardian's consent, an anonymous username, and a 4-digit PIN to create a profile. We do not collect or store any personally identifiable information (PII) like real names, dates of birth, or contact details.
            - Purpose: This minimal data is used exclusively to save your child's quiz progress and achievements and allow them to log back in to their profile.
            - Secure Storage: This anonymous data is stored securely on our servers.
            - Account Recovery: Please note, because we don't store any contact information, a forgotten PIN is not recoverable.
            """
        )
    
    st.markdown("Read about our Privacy & Data Usage policies:")
    col_notice_btn, _, _ = st.columns([0.4, 0.4, 0.2])
    with col_notice_btn:
        if st.button("View Notice", key="privacy_notice_btn"):
            privacy_dialog()

    # --- Action Buttons ---
    col_start_left, col_start_btn, col_start_right = st.columns([1, 2, 1])

    if not st.session_state.get("logged_in"):
        with col_start_btn:
            if st.button("Get Started", width='stretch'):
                set_view("login")
    else:
        with col_start_btn:
            st.info("You are logged in! Use the sidebar to navigate.")

