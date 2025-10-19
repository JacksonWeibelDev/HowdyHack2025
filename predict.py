import os
import re
import joblib
import numpy as np
# Import your GenAI client (Gemini in this case)
from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import hstack

# --- 1. Initialize Clients ---
MODEL_DIR = "saved_models"

# Initialize Google Gemini client (using API_KEY environment variable)
try:
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("Error: API_KEY environment variable not found.")
        client = None
    else:
        
        client = genai.Client(api_key=api_key)

        print("Google Gemini client initialized.")
except Exception as e:
    print(f"Error initializing Google Gemini client: {e}")
    gemini_model = None

# --- 2. Define Constants and Helpers ---
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
    if not isinstance(text, str): return ""
    text = text.lower()
    for name_word in name_words:
        text = re.sub(r'\b' + re.escape(name_word) + r'\b', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    words = text.split()
    cleaned_words = [word for word in words if word not in CUSTOM_STOP_WORDS and len(word) > 2]
    return " ".join(cleaned_words)

def _has_portfolio_link(text):
    if not isinstance(text, str): return 0
    return 1 if re.search(r'(https?://|www\.)', text, re.IGNORECASE) else 0

def _has_honors_or_certs(text):
    if not isinstance(text, str): return 0
    return 1 if re.search(r'\b(award|honor|certification|certificate|publication|patent|distinction|fellowship)\b', text, re.IGNORECASE) else 0

# --- 3. Gen AI Assessment Function ---
def get_gen_ai_assessment(resume_text, job_role):

    prompt = f"""
    Analyze the following resume for the job role of '{job_role}'.
    Provide a brief, 2-sentence assessment:
    1. State your recommendation: "This candidate appears to be a [Strong/Good/Weak/Poor] match."
    2. Provide a single sentence of justification for your reasoning.
    
    Resume Text:
    ---
    {resume_text}
    ---
    
    Respond *only* with your 2-sentence assessment.
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash-lite",contents=prompt)
        assessment = response.text.lower() # Convert to lowercase for easier checking

        # Determine sentiment
        sentiment = "Neutral"
        if "strong" in assessment or "good" in assessment:
            sentiment = "Positive"
        elif "weak" in assessment or "poor" in assessment:
            sentiment = "Negative"
            
        return {"gen_ai_assessment": response.text, "gen_ai_sentiment": sentiment} # Return original case text

    except Exception as e:
        print(f"Error calling Google Gemini API: {e}")
        error_details = ""
        try:
           error_details = response.prompt_feedback
        except:
           pass
        return {"gen_ai_assessment": f"Error calling Google Gemini API: {e}. Feedback: {error_details}", "gen_ai_sentiment": "Error"}

# --- 4. Main Public Function ---
def classify_resume(resume_text, job_role):
    """
    Classifies a new resume using the ML model, GenAI assessment,
    and pre-generated competitive analysis, adjusting confidence.
    """
    
    # --- Part 1: ML Model (Fast Classification) ---
    print(f"Attempting to classify for role: '{job_role}'")
    role_lower = job_role.lower()
    safe_role_name = re.sub(r'[^a-z0-9_]+', '', role_lower.replace(' ', '_'))
    model_path = os.path.join(MODEL_DIR, f"{safe_role_name}_model.joblib")
    vectorizer_path = os.path.join(MODEL_DIR, f"{safe_role_name}_vectorizer.joblib")

    ml_result = {}
    ml_prediction_label = "Error" # Initialize
    ml_confidence_float = 0.0     # Initialize

    if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
        ml_result = { "error": f"No ML model found for role '{job_role}'. (Checked for: {model_path})" }
    else:
        try:
            model = joblib.load(model_path)
            vectorizer = joblib.load(vectorizer_path)
            
            cleaned_resume = _clean_text_aggressively(resume_text, set()) 
            portfolio = _has_portfolio_link(resume_text)
            honors = _has_honors_or_certs(resume_text)
            engineered_features = np.array([[portfolio, honors]]) 
            
            tfidf_matrix = vectorizer.transform([cleaned_resume])
            features_combined = hstack([tfidf_matrix, engineered_features])
            
            prediction = model.predict(features_combined)[0]
            probability = model.predict_proba(features_combined)[0]
            
            ml_prediction_label = 'Select' if prediction == 1 else 'Reject'
            ml_confidence_float = probability[prediction] * 100 # Store as float for adjustment

        except Exception as e:
            ml_result = {"error": f"ML model error: {e}"}
            
    # --- Part 2: Gen AI Model (Slow Reasoning) ---
    print("Getting Gen AI assessment using Gemini...")
    gen_ai_result = get_gen_ai_assessment(resume_text, job_role) # Contains assessment text and sentiment

    # --- Part 3: (NEW) Adjust Confidence ---
    adjusted_confidence_float = ml_confidence_float
    adjustment_factor = 10.0 # Add/subtract 10 percentage points

    if "error" not in ml_result and gen_ai_result["gen_ai_sentiment"] != "Error" and gen_ai_result["gen_ai_sentiment"] != "Neutral":
        gen_ai_positive = gen_ai_result["gen_ai_sentiment"] == "Positive"
        ml_is_select = ml_prediction_label == "Select"

        if gen_ai_positive == ml_is_select: # They agree
            print(f"GenAI agrees with ML ({ml_prediction_label}). Boosting confidence.")
            adjusted_confidence_float = min(100.0, ml_confidence_float + adjustment_factor)
        else: # They disagree
            print(f"GenAI disagrees with ML ({ml_prediction_label}). Reducing confidence.")
            adjusted_confidence_float = max(0.0, ml_confidence_float - adjustment_factor)
    else:
        print("Skipping confidence adjustment due to ML error or neutral/error GenAI sentiment.")

    # Update ml_result with potentially adjusted confidence
    if "error" not in ml_result:
        ml_result = {
            "ml_prediction": ml_prediction_label,
            "ml_confidence": f"{adjusted_confidence_float:.2f}%" # Format back to string
        }

    # --- Part 4: Load Pre-Generated Analysis ---
    print("Loading competitive analysis...")
    analysis_path = os.path.join(MODEL_DIR, f"{safe_role_name}_analysis.txt")
    analysis_result = {}
    if os.path.exists(analysis_path):
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                analysis_text = f.read()
            analysis_result = {"competitive_analysis": analysis_text}
        except Exception as e:
            analysis_result = {"competitive_analysis": f"Error reading analysis file: {e}"}
    else:
        analysis_result = {"competitive_analysis": "No competitive analysis available for this role."}

    # --- Part 5: Combine All Results ---
    final_result = {
        "role": job_role,
        **ml_result,
        "gen_ai_assessment": gen_ai_result.get("gen_ai_assessment", "N/A"), # Keep only text
        **analysis_result
    }
    
    return final_result