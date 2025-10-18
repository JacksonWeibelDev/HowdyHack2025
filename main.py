import pandas as pd
import numpy as np
import re
import os
import joblib
import shutil
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import hstack

# --- 1. Create Helper Functions ---
CUSTOM_STOP_WORDS = set([
    'resume', 'profile', 'summary', 'objective', 'experience', 'education', 'skills',
    'projects', 'references', 'company', 'organization', 'location', 'city', 'state',
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september',
    'october', 'november', 'december', 'present', 'current', 'llc', 'inc', 'corp',
    'gpa', 'university', 'college', 'degree', 'linkedin', 'github', 'email', 'phone',
    'address', 'date', 'birth', 'street', 'com', 'www', 'http', 'httpss'
])

def clean_text_aggressively(text, name_words):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    for name_word in name_words:
        text = re.sub(r'\b' + re.escape(name_word) + r'\b', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    words = text.split()
    cleaned_words = [word for word in words if word not in CUSTOM_STOP_WORDS and len(word) > 2]
    return " ".join(cleaned_words)

def has_portfolio_link(text):
    if not isinstance(text, str): return 0
    return 1 if re.search(r'(https?://|www\.)', text, re.IGNORECASE) else 0

def has_honors_or_certs(text):
    if not isinstance(text, str): return 0
    return 1 if re.search(r'\b(award|honor|certification|certificate|publication|patent|distinction|fellowship)\b', text, re.IGNORECASE) else 0

# --- 2. Load and Process Data ---
csv_file = 'Dataset/dataset.csv'
try:
    df = pd.read_csv(csv_file)
    print(f"Successfully loaded '{csv_file}'. Found {len(df)} total records.")
except FileNotFoundError:
    print(f"Error: Could not find '{csv_file}'.")
    exit()

if 'decision' in df.columns and df['decision'].dtype == 'object':
    df['decision'] = df['decision'].map({'select': 1, 'reject': 0}) 
    df.dropna(subset=['decision'], inplace=True)
    df['decision'] = df['decision'].astype(int)
else:
    print("Error: Could not find a valid 'decision' column to map.")
    exit()

# --- 3. Iterate Through All Roles ---
print("\n--- Starting Model Training for All Roles ---")
    
df['role_lower'] = df['Role'].str.lower()
unique_roles = df['role_lower'].dropna().unique()
results = [] 

MODEL_DIR = "saved_models"

if os.path.exists(MODEL_DIR):
    shutil.rmtree(MODEL_DIR)
    print(f"Removed old '{MODEL_DIR}' directory.")
os.makedirs(MODEL_DIR, exist_ok=True)
print(f"Models will be saved in new '{MODEL_DIR}' directory.")

for role in unique_roles:
    print(f"\nProcessing Role: {role}...")
    
    # 4. Filter
    df_subset = df[df['role_lower'] == role].copy()
    
    # 5. Check
    if len(df_subset) < 50:
        print(f"Skipping: Only found {len(df_subset)} applicants. (Min: 50)")
        continue
    
    # --- NEW: Get counts *before* skipping ---
    value_counts = df_subset['decision'].value_counts()
    select_count = value_counts.get(1, 0)
    reject_count = value_counts.get(0, 0)
    
    if df_subset['decision'].nunique() < 2:
        print(f"Skipping: This role only has one outcome ({select_count} Select / {reject_count} Reject).")
        continue
        
    print(f"Found {len(df_subset)} applicants.")
    # --- NEW: Print the balance ---
    print(f"Decision Balance: {select_count} Select / {reject_count} Reject")

    # 6. (DELETED) Augmentation is gone

    # 7. Feature Engineering
    df_subset['has_portfolio_link'] = df_subset['Resume'].apply(has_portfolio_link)
    df_subset['has_honors_or_certs'] = df_subset['Resume'].apply(has_honors_or_certs)
    df_subset['name_words'] = df_subset['Name'].apply(lambda x: set(str(x).lower().split()) if pd.notna(x) else set())
    df_subset['cleaned_resume'] = df_subset.apply(lambda row: clean_text_aggressively(row['Resume'], row['name_words']), axis=1)
    engineered_features = df_subset[['has_portfolio_link', 'has_honors_or_certs']]

    # 8. Create TF-IDF
    vectorizer = TfidfVectorizer(
        stop_words='english', max_features=3000, min_df=3, max_df=0.85, ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform(df_subset['cleaned_resume'])
    features_combined = hstack([tfidf_matrix, engineered_features])

    # 9. Prepare Data
    target = df_subset['decision']
    X_train, X_test, y_train, y_test = train_test_split(
        features_combined, target, test_size=0.3, random_state=42
    )

    # 10. Train
    print("Training model with class_weight='balanced'...")
    ml_model = LogisticRegression(
        random_state=42, 
        solver='liblinear', 
        max_iter=1000,
        class_weight='balanced'
    )
    ml_model.fit(X_train, y_train)

    # 11. Evaluate
    predictions = ml_model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Success! Accuracy: {accuracy * 100:.2f}%")
    
    # --- NEW: Add counts to results ---
    results.append({
        'Role': role, 
        'Accuracy': accuracy, 
        'Select_Count': select_count, 
        'Reject_Count': reject_count, 
        'Total_Applicants': len(df_subset)
    })

    # 12. SAVE THE MODEL AND VECTORIZER
    safe_role_name = re.sub(r'[^a-z0-9_]+', '', role.replace(' ', '_'))
    model_path = os.path.join(MODEL_DIR, f"{safe_role_name}_model.joblib")
    vectorizer_path = os.path.join(MODEL_DIR, f"{safe_role_name}_vectorizer.joblib")
    
    joblib.dump(ml_model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    print(f"Saved balanced model to {model_path}")

# --- 13. Final Report ---
print("\n--- Final Accuracy Report (Balanced Models) ---")
if results:
    results_df = pd.DataFrame(results)
    # --- NEW: Reorder columns ---
    results_df = results_df[[
        'Role', 
        'Accuracy', 
        'Select_Count', 
        'Reject_Count', 
        'Total_Applicants'
    ]]
    results_df = results_df.sort_values(by='Accuracy', ascending=False)
    print(results_df.to_string(index=False))
else:
    print("No roles had sufficient data to train a model.")