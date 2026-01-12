import os
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.firestore import transactional

@st.cache_resource
def initialize_firestore():
    """Initializes the Firebase Admin SDK and returns a Firestore client.
    Prioritizes credentials from environment variable 'FIREBASE_SERVICE_ACCOUNT_KEY',
    falling back to 'firebase_credentials_dev.json' for local development."""
    if not firebase_admin._apps:
        # Try loading credentials from environment variable first
        if "FIREBASE_SERVICE_ACCOUNT_KEY" in os.environ:
            try:
                # The environment variable should contain the JSON string of the service account key
                cred_json_string = os.environ["FIREBASE_SERVICE_ACCOUNT_KEY"]
                cred_json = json.loads(cred_json_string)
                cred = credentials.Certificate(cred_json)
                st.success("Firebase credentials loaded from environment variables.")
            except json.JSONDecodeError:
                st.error("FIREBASE_SERVICE_ACCOUNT_KEY environment variable is not a valid JSON string.")
                st.stop() # Stop the app if credentials cannot be loaded
            except Exception as e:
                st.error(f"Error loading Firebase credentials from environment variable: {e}")
                st.stop()
        else:
            # Fallback to local file for development
            cred_file_path = "firebase_credentials_dev.json"
            if os.path.exists(cred_file_path):
                cred = credentials.Certificate(cred_file_path)
                st.warning("Firebase credentials loaded from local file. Use environment variables for deployment.")
            else:
                st.error("Firebase credentials file not found and environment variable not set. Please configure Firebase credentials.")
                st.stop() # Stop the app if credentials cannot be loaded
        
        firebase_admin.initialize_app(cred)
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
def _update_math_index_transaction(transaction, index_ref, chapter_id, chapter_name, story_file, story_name):
    index_snapshot = index_ref.get(transaction=transaction)
    index_data = index_snapshot.to_dict() if index_snapshot.exists else {'chapters': []}
    
    chapter_found = False
    for chap in index_data['chapters']:
        if chap['id'] == chapter_id:
            chapter_found = True
            story_found = False
            for story in chap['stories']:
                if story['file'] == story_file:
                    story['name'] = story_name
                    story_found = True
                    break
            if not story_found:
                chap['stories'].append({'file': story_file, 'name': story_name})
            break
    
    if not chapter_found:
        index_data['chapters'].append({
            'id': chapter_id,
            'title': chapter_name,
            'stories': [{'file': story_file, 'name': story_name}]
        })
    transaction.set(index_ref, index_data)

def upload_math_quiz(quiz_id, quiz_data, chapter_id, chapter_name, story_file, story_name):
    db = initialize_firestore()
    quiz_ref = db.collection('quizzes').document(quiz_id)
    index_ref = db.collection('subject_indices').document('Math')
    # quiz_data['topic_id'] = topic_id
    quiz_data['chapter_id'] = chapter_id
    transaction = db.transaction()
    _update_math_index_transaction(transaction, index_ref, chapter_id, chapter_name, story_file, story_name)
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
