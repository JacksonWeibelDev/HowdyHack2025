import os
import re
import joblib
import numpy as np
import random
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

        # Estimate a simple confidence score from wording to give Gemini a variable weight
        gen_confidence = 0.60
        if re.search(r'\b(strong|strongly|excellent|outstanding|exceptional|highly)\b', assessment):
            gen_confidence = 0.92
        elif re.search(r'\b(very|well|good|solid|suitable|competent)\b', assessment):
            gen_confidence = 0.78
        elif re.search(r'\b(somewhat|possibly|maybe|could|might)\b', assessment):
            gen_confidence = 0.55
        elif re.search(r'\b(weak|poor|limited|insufficient|not a good)\b', assessment):
            gen_confidence = 0.22

        return {
            "gen_ai_assessment": response.text,
            "gen_ai_sentiment": sentiment,
            "gen_ai_confidence": gen_confidence
        } # Return original case text + confidence

    except Exception as e:
        print(f"Error calling Google Gemini API: {e}")
        error_details = ""
        try:
           error_details = response.prompt_feedback
        except:
           pass
        return {"gen_ai_assessment": f"Error calling Google Gemini API: {e}. Feedback: {error_details}", "gen_ai_sentiment": "Error", "gen_ai_confidence": 0.5}
# --- 4. (NEW) Gen AI Resume-JD Comparison Function ---
def get_resume_jd_comparison(resume_text, job_description, job_role):
    if not job_description or not job_description.strip():
         return {"resume_jd_comparison": "No job description provided for comparison."}

    prompt = f"""
    You are an expert HR analyst comparing a candidate's resume against a specific job description for the role of '{job_role}'.
    Provide a concise paragraph (3-4 sentences) summarizing how well the resume aligns with the key requirements mentioned in the job description.
    Highlight 1-2 key strengths and 1-2 potential gaps or areas lacking detail in the resume compared to the job description.

    Resume Text:
    ---
    {resume_text}
    ---

    Job Description:
    ---
    {job_description}
    ---

    Provide only the comparison paragraph.
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash-lite",contents=prompt)
        comparison = response.text
        return {"resume_jd_comparison": comparison}
    except Exception as e:
        print(f"Error calling Google Gemini API (comparison): {e}")
        error_details = ""
        try: error_details = response.prompt_feedback
        except: pass
        return {"resume_jd_comparison": f"Error calling Google Gemini API: {e}. Feedback: {error_details}"}


# --- 5. Gen AI Improvement Suggestions Function ---
# (Keep get_resume_improvement_suggestions as before)
def get_resume_improvement_suggestions(resume_text, job_role):
    
    prompt = f"""
    You are an expert career coach reviewing a resume for the specific job role of '{job_role}'.
    Analyze the provided resume and give 2-3 specific, actionable suggestions on how the candidate
    could improve their resume *to better match this particular role*.
    Focus on highlighting relevant skills, quantifying achievements, or adding specific keywords. Keep suggestions concise (bullet points or short paragraph).
    Resume Text: --- {resume_text} ---
    Provide only the improvement suggestions.
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash-lite",contents=prompt)
        suggestions = response.text
        return {"improvement_suggestions": suggestions}
    except Exception as e:
        print(f"Error calling Google Gemini API (suggestions): {e}")
        error_details = ""
        try: error_details = response.prompt_feedback
        except: pass
        return {"improvement_suggestions": f"Error: {e}. Feedback: {error_details}"}




# --- 6. (MODIFIED) Main Public Function ---
def classify_resume(resume_text, job_role, job_description=None): # Added job_description argument
    """
    Classifies a resume using ML, GenAI assessment, confidence adjustment,
    JD comparison (if JD provided), and improvement suggestions.
    """

    # --- Part 1: ML Model ---
    # (ML logic remains the same)
    print(f"Attempting to classify for role: '{job_role}'")
    role_lower = job_role.lower()
    safe_role_name = re.sub(r'[^a-z0-9_]+', '', role_lower.replace(' ', '_'))
    model_path = os.path.join(MODEL_DIR, f"{safe_role_name}_model.joblib")
    vectorizer_path = os.path.join(MODEL_DIR, f"{safe_role_name}_vectorizer.joblib")
    ml_result = {}
    ml_prediction_label = "Error"
    ml_confidence_float = 0.0
    if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
        ml_result = { "error": f"No ML model found for role '{job_role}'." }
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
            ml_confidence_float = probability[prediction] * 100
        except Exception as e:
            ml_result = {"error": f"ML model error: {e}"}

    # --- Part 2: Gen AI Assessment ---
    print("Getting Gen AI assessment using Gemini...")
    gen_ai_result = get_gen_ai_assessment(resume_text, job_role)

    # --- Part 3: Adjust Confidence ---
    # (Confidence adjustment logic remains the same)
    adjusted_confidence_float = ml_confidence_float
    MAX_ADJUSTMENT = 70.0
    MIN_ADJUSTMENT = 5.0
    if "error" not in ml_result and gen_ai_result.get("gen_ai_sentiment") != "Error" and gen_ai_result.get("gen_ai_sentiment") != "Neutral":
        gen_ai_positive = gen_ai_result["gen_ai_sentiment"] == "Positive"
        ml_is_select = ml_prediction_label == "Select"

        adjustment_range = MAX_ADJUSTMENT - MIN_ADJUSTMENT
        confidence_diff_scale = (100.0 - ml_confidence_float) / 100.0
        base_adjustment = MIN_ADJUSTMENT + (adjustment_range * confidence_diff_scale)

        # Use the GenAI confidence estimate to scale the adjustment (more confident => stronger influence)
        gen_conf = float(gen_ai_result.get("gen_ai_confidence", 0.6))
        # scale factor centered around ~0.8 and clamped so adjustments don't explode
        scale = max(0.6, min(1.4, 0.8 + (gen_conf - 0.5)))
        dynamic_adjustment = base_adjustment * scale

        # Add a small random jitter so the adjustment isn't identical every time (±10%)
        jitter = random.uniform(-0.10, 0.10) * dynamic_adjustment
        dynamic_adjustment = max(MIN_ADJUSTMENT, min(MAX_ADJUSTMENT, dynamic_adjustment + jitter))

        if gen_ai_positive == ml_is_select:
            print(f"GenAI agrees with ML ({ml_prediction_label}). Boosting confidence by {dynamic_adjustment:.2f}.")
            adjusted_confidence_float = min(100.0, ml_confidence_float + dynamic_adjustment)
        else:
            print(f"GenAI disagrees with ML ({ml_prediction_label}). Reducing confidence by {dynamic_adjustment:.2f}.")
            adjusted_confidence_float = max(0.0, ml_confidence_float - dynamic_adjustment)
    else:
        print("Skipping confidence adjustment.")
    if "error" not in ml_result:
        ml_result = {
            "ml_prediction": ml_prediction_label,
            "ml_confidence": f"{adjusted_confidence_float:.2f}%"
        }

    # --- Part 4: (NEW) Get Resume-JD Comparison ---
    print("Getting Resume-JD comparison using Gemini...")
    jd_comparison_result = get_resume_jd_comparison(resume_text, job_description, job_role)

    # --- Part 5: Get Improvement Suggestions ---
    print("Getting improvement suggestions using Gemini...")
    improvement_result = get_resume_improvement_suggestions(resume_text, job_role)

    # --- Part 6: Combine All Results ---
    final_result = {
        "role": job_role,
        **ml_result,
        "gen_ai_assessment": gen_ai_result.get("gen_ai_assessment", "N/A"),
        **jd_comparison_result, # Add the comparison dictionary
        **improvement_result
    }

    return final_result