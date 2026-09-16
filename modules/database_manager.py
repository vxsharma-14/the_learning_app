import os
import streamlit as st
from streamlit.errors import StreamlitAPIException, StreamlitSecretNotFoundError
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.firestore import transactional
from modules.exceptions import FirebaseCredentialsError

def _get_credentials():
    """
    Gets Firebase credentials from various sources in a specific order of priority.
    1. Streamlit Secrets (for Streamlit Community Cloud)
    2. Environment Variables (for Cloudflare Pages, Heroku, etc.)
    3. Local JSON file (for local development)
    Returns a credential object or raises FirebaseCredentialsError.
    """
    # Method 1: Try Streamlit Secrets
    try:
        if "firebase" in st.secrets:
            creds_dict = st.secrets.firebase.to_dict()
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            return credentials.Certificate(creds_dict)
    except (StreamlitAPIException, StreamlitSecretNotFoundError):
        # This means no secrets.toml was found, which is normal for local dev.
        # We'll just pass and try the next method.
        pass
    except Exception as e:
        # This means secrets were found, but there was an error parsing them.
        raise FirebaseCredentialsError(f"Error processing Streamlit secrets: {e}")

    # Method 2: Try Environment Variables
    if "FIREBASE_PROJECT_ID" in os.environ:
        try:
            creds_dict = {
                "type": "service_account",
                "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
                "auth_uri": os.environ.get("FIREBASE_AUTH_URI"),
                "token_uri": os.environ.get("FIREBASE_TOKEN_URI"),
                "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
                "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_X509_CERT_URL"),
                "universe_domain": "googleapis.com"
            }
            if not all([creds_dict["project_id"], creds_dict["private_key"], creds_dict["client_email"]]):
                raise FirebaseCredentialsError("Missing one or more required Firebase environment variables.")
            return credentials.Certificate(creds_dict)
        except Exception as e:
            raise FirebaseCredentialsError(f"Error loading credentials from environment variables: {e}")

    # Method 3: Try Local File
    cred_file_path = "firebase_credentials_dev.json"
    if os.path.exists(cred_file_path):
        return credentials.Certificate(cred_file_path)

    # If all methods fail, raise an error.
    raise FirebaseCredentialsError(
        "Firebase credentials not found. Please configure them in your hosting provider's secrets "
        "or provide a 'firebase_credentials_dev.json' file for local development."
    )


@st.cache_resource
def initialize_firestore():
    """
    Initializes the Firebase Admin SDK using credentials from _get_credentials
    and returns a Firestore client. This function is cached as a resource.
    It has no UI side effects.
    """
    if not firebase_admin._apps:
        try:
            cred = _get_credentials()
            firebase_admin.initialize_app(cred)
        except FirebaseCredentialsError as e:
            # Re-raise the specific error to be caught by the main app
            raise e
            
    return firestore.client()

# --- Generic Document/Collection Functions ---
def get_all_documents(collection_name: str) -> list:
    db = initialize_firestore()
    return [doc for doc in db.collection(collection_name).stream()]

def set_document(collection_name: str, doc_id: str, data: dict):
    db = initialize_firestore()
    db.collection(collection_name).document(doc_id).set(data)

def delete_document(collection_name: str, doc_id: str):
    db = initialize_firestore()
    db.collection(collection_name).document(doc_id).delete()

# --- User Specific Functions ---
def user_exists(username: str) -> bool:
    db = initialize_firestore()
    return db.collection('users').document(username).get().exists

def create_user(username: str, salt: str, hashed_pin: str):
    set_document('users', username, {'salt': salt, 'hashed_pin': hashed_pin})

def get_user_credentials(username: str) -> dict:
    db = initialize_firestore()
    doc = db.collection('users').document(username).get()
    return doc.to_dict() if doc.exists else None

def delete_user_and_subcollections(username: str):
    db = initialize_firestore()
    user_ref = db.collection('users').document(username)
    _delete_collection(user_ref.collection('attempts'), 100)
    user_ref.delete()

def _delete_collection(coll_ref, batch_size):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    if deleted >= batch_size:
        return _delete_collection(coll_ref, batch_size)

# --- Quiz Content Functions ---
def get_subject_index(subject_id: str) -> dict:
    db = initialize_firestore()
    doc = db.collection('subject_indices').document(subject_id).get()
    return doc.to_dict() if doc.exists else None

def get_quiz(quiz_id: str) -> dict:
    db = initialize_firestore()
    doc = db.collection('quizzes').document(quiz_id).get()
    return doc.to_dict() if doc.exists else None

@transactional
def _update_gk_index_transaction(transaction, index_ref, topic_id, topic_name, quiz_id, level_name, level_file):
    index_snapshot = index_ref.get(transaction=transaction)
    index_data = index_snapshot.to_dict() if index_snapshot.exists else {'topics_data': {}}

    if 'topics_data' not in index_data:
        index_data['topics_data'] = {}
        
    # Get or create the topic entry
    topic_entry = index_data['topics_data'].get(topic_id, {})
    topic_entry['name'] = topic_name # Update name in case it changes
    
    # Get or create the quizzes map for the topic
    if 'quizzes' not in topic_entry:
        topic_entry['quizzes'] = {}
        
    # Add or update the quiz level info
    topic_entry['quizzes'][quiz_id] = {
        'name': level_name,
        'filename': level_file
    }
    
    # Update the main index data
    index_data['topics_data'][topic_id] = topic_entry
    transaction.set(index_ref, index_data)

def upload_gk_quiz(quiz_id, quiz_data, topic_id, topic_name, level_file, level_name):
    db = initialize_firestore()
    quiz_ref = db.collection('quizzes').document(quiz_id)
    index_ref = db.collection('subject_indices').document('GK')

    quiz_data['topic_id'] = topic_id
    
    transaction = db.transaction()
    _update_gk_index_transaction(transaction, index_ref, topic_id, topic_name, quiz_id, level_name, level_file)
    transaction.set(quiz_ref, quiz_data)
    
    transaction.commit()

# (The math upload functions can be updated similarly if needed)
@transactional
def _update_math_index_transaction(transaction, index_ref, chapter_id, chapter_name, story_file, story_name, topics):
    index_snapshot = index_ref.get(transaction=transaction)
    index_data = index_snapshot.to_dict() if index_snapshot.exists else {'chapters': []}
    
    new_story_data = {'file': story_file, 'name': story_name, 'topics': topics}

    chapter_found = False
    for chap in index_data['chapters']:
        if chap['id'] == chapter_id:
            chapter_found = True
            story_found = False
            # Also update chapter title in case it has changed
            chap['title'] = chapter_name
            for story in chap['stories']:
                if story['file'] == story_file:
                    # Update existing story with new name and topics
                    story['name'] = story_name
                    story['topics'] = topics
                    story_found = True
                    break
            if not story_found:
                chap['stories'].append(new_story_data)
            break
    
    if not chapter_found:
        index_data['chapters'].append({
            'id': chapter_id,
            'title': chapter_name,
            'stories': [new_story_data]
        })
    transaction.set(index_ref, index_data)

def upload_math_quiz(quiz_id, quiz_data, chapter_id, chapter_name, story_file, story_name):
    db = initialize_firestore()
    quiz_ref = db.collection('quizzes').document(quiz_id)
    index_ref = db.collection('subject_indices').document('Math')
    
    # Extract topics from the quiz data and parse if it's a string
    topics_raw = quiz_data.get('topics')
    if isinstance(topics_raw, str):
        # Split the string by " and " and strip leading/trailing whitespace from each topic
        topics = [topic.strip() for topic in topics_raw.split(' and ')]
    elif isinstance(topics_raw, list):
        # If it's already a list, use it as is
        topics = topics_raw
    else:
        # Default to an empty list if it's missing or another type
        topics = []
        
    quiz_data['chapter_id'] = chapter_id

    transaction = db.transaction()
    _update_math_index_transaction(transaction, index_ref, chapter_id, chapter_name, story_file, story_name, topics)
    transaction.set(quiz_ref, quiz_data)
    transaction.commit()

# --- Quiz Attempt Functions ---
def save_attempt(username: str, attempt_data: dict):
    db = initialize_firestore()
    user_ref = db.collection('users').document(username)
    user_ref.collection('attempts').add(attempt_data)
    st.toast("Saved attempt successfully!")

def get_student_attempts(username: str) -> list:
    db = initialize_firestore()
    attempts_ref = db.collection('users').document(username).collection('attempts')
    query = attempts_ref.order_by("timestamp", direction=firestore.Query.DESCENDING)
    
    attempts = []
    for doc in query.stream():
        attempt_data = doc.to_dict()
        attempt_data['filename'] = doc.id
        attempts.append(attempt_data)
    return attempts

def get_all_users() -> list:
    """Gets all user documents, implicitly excluding the 'admin' user."""
    db = initialize_firestore()
    users_docs = db.collection('users').stream()
    # Implicitly filter out the admin user as requested.
    return [doc for doc in users_docs if doc.id != "admin"]

@st.cache_data(ttl=300) # Cache for 5 minutes for performance
def get_all_attempts() -> list:
    """Fetches all attempts from all non-admin users."""
    db = initialize_firestore()
    all_attempts = []
    users = get_all_users() # Use the new function

    for user_doc in users:
        attempts_ref = db.collection('users').document(user_doc.id).collection('attempts')
        for attempt_doc in attempts_ref.stream():
            attempt_data = attempt_doc.to_dict()
            attempt_data['attempt_id'] = attempt_doc.id
            attempt_data['student_name'] = user_doc.id
            all_attempts.append(attempt_data)
    return all_attempts

# --- User Progress and Gamification Functions ---

def get_user_progress(username: str) -> dict:
    """
    Fetches the 'progress' map from a user's document.
    
    Args:
        username: The username of the user.
        
    Returns:
        The user's progress data, or an empty dict if not found.
    """
    db = initialize_firestore()
    user_doc = db.collection('users').document(username).get()
    if user_doc.exists:
        return user_doc.to_dict().get("progress", {})
    return {}

def update_user_progress(username: str, subject: str, chapter_id: str, story_id: str, score_percent: int, stars: int):
    """
    Updates a user's progress after a quiz attempt.
    It updates the best score and stars for a story, and awards badges for chapter completion.
    
    Args:
        username: The user's username.
        subject: The subject of the quiz (e.g., "Math").
        chapter_id: The ID of the chapter.
        story_id: The ID of the story/quiz.
        score_percent: The user's score as a percentage.
        stars: The number of stars earned (0-3).
    """
    db = initialize_firestore()
    user_ref = db.collection('users').document(username)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return # Should not happen for a logged-in user

    progress = user_doc.to_dict().get("progress", {})
    
    # Safely navigate and create nested dictionaries if they don't exist
    subject_progress = progress.setdefault(subject.lower(), {})
    chapter_progress = subject_progress.setdefault(chapter_id, {"stories": {}, "badge_earned": False})
    story_progress = chapter_progress["stories"].setdefault(story_id, {"best_score_percent": -1, "stars": 0})
    
    # Update only if the new score is better
    if score_percent > story_progress["best_score_percent"]:
        story_progress["best_score_percent"] = score_percent
        story_progress["stars"] = stars

        # After updating, check if a badge should be awarded
        _check_and_award_badge(progress, subject, chapter_id)
        
        # Write the entire updated progress map back to Firestore
        user_ref.set({"progress": progress}, merge=True)

def _check_and_award_badge(progress: dict, subject: str, chapter_id: str):
    """
    Checks if all stories in a chapter are passed and awards a badge.
    
    A story is considered "passed" if its score is >= 60%.
    """
    # Get the subject index to know which stories are in the chapter
    subject_index = get_subject_index(subject)
    if not subject_index or "chapters" not in subject_index:
        return

    # Find the current chapter from the index
    current_chapter_from_index = next((chap for chap in subject_index["chapters"] if chap["id"] == chapter_id), None)
    if not current_chapter_from_index or "stories" not in current_chapter_from_index:
        return
        
    required_stories = current_chapter_from_index["stories"]
    user_chapter_progress = progress.get(subject.lower(), {}).get(chapter_id, {})
    user_stories = user_chapter_progress.get("stories", {})

    all_passed = True
    if not required_stories: # If a chapter has no stories, no badge
        all_passed = False
    else:
        for story in required_stories:
            story_id = story["file"].replace(".json", "") # Normalize story_id
            if story_id not in user_stories or user_stories[story_id].get("best_score_percent", 0) < 60:
                all_passed = False
                break
    
    if all_passed:
        user_chapter_progress["badge_earned"] = True

