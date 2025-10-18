import os
import re
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import hstack

# --- 1. Define Constants and Helpers ---

MODEL_DIR = "saved_models"

CUSTOM_STOP_WORDS = set([
    'resume', 'profile', 'summary', 'objective', 'experience', 'education', 'skills',
    'projects', 'references', 'company', 'organization', 'location', 'city', 'state',
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september',
    'october', 'november', 'december', 'present', 'current', 'llc', 'inc', 'corp',
    'gpa', 'university', 'college', 'degree', 'linkedin', 'github', 'email', 'phone',
    'address', 'date', 'birth', 'street', 'com', 'www', 'http', 'httpss'
])

def _clean_text_aggressively(text, name_words):
    """(Private) Aggressive cleaning function."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    for name_word in name_words:
        text = re.sub(r'\b' + re.escape(name_word) + r'\b', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    words = text.split()
    cleaned_words = [word for word in words if word not in CUSTOM_STOP_WORDS and len(word) > 2]
    return " ".join(cleaned_words)

def _has_portfolio_link(text):
    """(Private) Checks for external links."""
    if not isinstance(text, str): return 0
    return 1 if re.search(r'(https?://|www\.)', text, re.IGNORECASE) else 0

def _has_honors_or_certs(text):
    """(Private) Checks for honors, awards, etc."""
    if not isinstance(text, str): return 0
    return 1 if re.search(r'\b(award|honor|certification|certificate|publication|patent|distinction|fellowship)\b', text, re.IGNORECASE) else 0


# --- 2. Main Public Function ---

def classify_resume(resume_text, job_role):
    """
    Classifies a new resume for a specific job role.
    This is the only function app.py will import.
    """
    print(f"Attempting to classify for role: '{job_role}'")
    
    # 1. Sanitize role name to find file
    role_lower = job_role.lower()
    safe_role_name = re.sub(r'[^a-z0-9_]+', '', role_lower.replace(' ', '_'))
    
    model_path = os.path.join(MODEL_DIR, f"{safe_role_name}_model.joblib")
    vectorizer_path = os.path.join(MODEL_DIR, f"{safe_role_name}_vectorizer.joblib")

    # 2. Check if model files exist
    if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
        return {
            "error": f"No model found for role '{job_role}'. (Checked for: {model_path})"
        }

    try:
        # 3. Load the saved model and vectorizer
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
        
        # 4. Process the new resume
        cleaned_resume = _clean_text_aggressively(resume_text, set()) 
        portfolio = _has_portfolio_link(resume_text)
        honors = _has_honors_or_certs(resume_text)
        engineered_features = np.array([[portfolio, honors]]) 
        
        # 5. Transform and combine features
        tfidf_matrix = vectorizer.transform([cleaned_resume])
        features_combined = hstack([tfidf_matrix, engineered_features])
        
        # 6. Make prediction
        prediction = model.predict(features_combined)[0]
        probability = model.predict_proba(features_combined)[0]
        
        # 7. Format output
        decision = 'Select' if prediction == 1 else 'Reject'
        confidence = probability[prediction] * 100
        
        return {
            "prediction": decision,
            "confidence": f"{confidence:.2f}%",
            "role": job_role
        }

    except Exception as e:
        return {"error": f"An error occurred: {e}"}