import os
import streamlit as st
import hashlib
from datetime import datetime
from modules import database_manager

# --- Helper Functions for PIN ---

def _generate_salt() -> bytes:
    """Generates a random salt using os.urandom for cryptographic security."""
    return os.urandom(16)


def _hash_pin(pin: str, salt: bytes) -> str:
    """Hashes a PIN with the given salt and returns the hex digest."""
    # The pin is stored as a hex string in Firestore
    return hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 100000).hex()

def _verify_pin(pin: str, hashed_pin: str, salt: bytes) -> bool:
    """Verifies a PIN against the stored hex-encoded hash."""
    return _hash_pin(pin, salt) == hashed_pin

# --- Streamlit Views ---

def initialize_session_state():
    """Initializes all necessary keys in Streamlit's session state."""
    state_defaults = {
        "current_view": "home",
        "student_name": "",
        "selected_level": "level1",
        "selected_subject": None,
        "selected_chapter": None,
        "selected_story": None,
        "questions": [],
        "user_answers": {},
        "score": 0,
        "time_taken": 0,
        "start_time": None,
        "quiz_finished": False,
        "logged_in": False,
        "selected_attempt_file": None
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_register_view():
    """Displays the screen for new user registration using Firestore."""
    from modules.navigation import set_view

    st.header("Create a New Account")
    
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("register_form"):
            username = st.text_input("Username", help="Choose a unique username.")
            pin = st.text_input("4-Digit PIN", type="password", max_chars=4, help="Choose a 4-digit numeric PIN.")
            confirm_pin = st.text_input("Confirm PIN", type="password", max_chars=4)
            
            st.markdown("---")
            consent_parent = st.checkbox("I am a parent or guardian and I consent to my child using this application under my supervision.")
            consent_privacy = st.checkbox("I have read, understood, and accept the Privacy & Data Usage Notice.")
            st.markdown("---")

            submitted = st.form_submit_button("Create Account")

            if submitted:
                if not (username and pin and confirm_pin):
                    st.error("Please fill out all fields.")
                elif pin != confirm_pin:
                    st.error("PINs do not match.")
                elif len(pin) != 4 or not pin.isdigit():
                    st.error("PIN must be exactly 4 numeric digits.")
                elif not consent_parent:
                    st.error("Parental consent is required.")
                elif not consent_privacy:
                    st.error("You must accept the Privacy & Data Usage Notice.")
                elif database_manager.user_exists(username):
                    st.error("Username is already taken. Please choose another one.")
                else:
                    salt = _generate_salt()
                    hashed_pin = _hash_pin(pin, salt)
                    database_manager.create_user(username, salt.hex(), hashed_pin)
                    
                    st.session_state.student_name = username
                    st.session_state.logged_in = True
                    st.success("Account created successfully! You are now logged in.")
                    set_view("home")
        
        st.markdown("---")
        st.markdown("Already have an account?")
        if st.button("Login here", key="register_to_login_btn"):
            set_view("login")


def render_login_view():
    """Displays the entry screen for student login using Firestore."""
    from modules.navigation import set_view
    
    st.header("Login to Your Account")
    st.info("By logging in, you confirm your acceptance of our terms and consent to our privacy practices.")
    st.markdown("---")

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login_form"):
            username = st.text_input("Username")
            pin = st.text_input("4-Digit PIN", type="password", max_chars=4)
            submitted = st.form_submit_button("Login")

            if submitted:
                if not (username and pin):
                    st.error("Please enter both username and PIN.")
                elif len(pin) != 4 or not pin.isdigit():
                    st.error("PIN must be exactly 4 numeric digits.")
                elif not database_manager.user_exists(username):
                    st.error("Username not found. Please create a new account.")
                else:
                    credentials = database_manager.get_user_credentials(username)
                    if credentials:
                        salt = bytes.fromhex(credentials['salt'])
                        hashed_pin_from_db = credentials['hashed_pin']
                        if _verify_pin(pin, hashed_pin_from_db, salt):
                            st.session_state.student_name = username
                            st.session_state.logged_in = True
                            st.success("Login successful!")
                            set_view("home")
                        else:
                            st.error("Incorrect PIN. Please try again.")
                    else:
                        st.error("Could not retrieve user credentials.")

        st.markdown("---")
        st.markdown("New User?")
        if st.button("Create an account here", key="login_to_register_btn"):
            set_view("register")