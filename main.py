import pandas as pd
import numpy as np
import re
import random 
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

SYNONYMS = {
    "managed": ["headed", "led", "supervised", "directed", "oversaw"],
    "developed": ["created", "built", "architected", "implemented", "prototyped"],
    "led": ["guided", "mentored", "oversaw", "spearheaded"],
    "created": ["designed", "prototyped", "founded", "established"],
    "increased": ["grew", "boosted", "improved", "raised", "expanded"],
    "customer": ["client", "user", "consumer", "patient", "stakeholder"],
    "responsible for": ["accountable for", "in charge of", "tasked with"],
    "data analysis": ["quantitative analysis", "data mining", "data interpretation"],
    "sales": ["revenue generation", "business development", "client acquisition"]
}


def clean_text_aggressively(text, name_words):
    """A much more aggressive function to clean resume text."""
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

def augment_resume(resume_text, name_words):
    """
    Creates a new version of a resume by replacing
    one random keyword with a synonym.
    """
    if not isinstance(resume_text, str):
        return resume_text
    
    text_lower = resume_text.lower()
    replaceable_words = [w for w in SYNONYMS.keys() if w in text_lower]
    
    if not replaceable_words:
        return None 

    word_to_replace = random.choice(replaceable_words)
    new_word = random.choice(SYNONYMS[word_to_replace])
    new_resume = resume_text.replace(word_to_replace, new_word, 1)
    
    return new_resume

# --- 2. Load and Process Data ---
csv_file = 'Dataset/dataset.csv'

try:
    df = pd.read_csv(csv_file)
    print(f"Successfully loaded '{csv_file}'. Found {len(df)} total records.")
except FileNotFoundError:
    print(f"Error: Could not find '{csv_file}'.")
    exit()

# Map the 'decision' column
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

for role in unique_roles:
    print(f"\nProcessing Role: {role}...")
    
    # 4. Filter the DataFrame for the current role
    df_subset = df[df['role_lower'] == role].copy()
    
    # 5. Check if the subset is valid for training
    if len(df_subset) < 50:
        print(f"Skipping: Only found {len(df_subset)} applicants. (Min: 50)")
        continue
    
    if df_subset['decision'].nunique() < 2:
        print(f"Skipping: This role only has one outcome (e.g., all 'select' or all 'reject').")
        continue

    # --- 6. DATA AUGMENTATION BLOCK ---
    df_subset['name_words'] = df_subset['Name'].apply(lambda x: set(str(x).lower().split()) if pd.notna(x) else set())
    
    print(f"Augmenting data... (Original count: {len(df_subset)})")
    augmented_rows = []
    
    for _ in range(3): 
        for index, row in df_subset[df_subset['decision'] == 1].iterrows():
            new_resume_text = augment_resume(row['Resume'], row['name_words'])
            if new_resume_text:
                new_row = row.to_dict()
                new_row['Resume'] = new_resume_text 
                augmented_rows.append(new_row)

    if augmented_rows:
        df_augmented = pd.DataFrame(augmented_rows)
        df_subset = pd.concat([df_subset, df_augmented], ignore_index=True)
        print(f"Data augmented. New count: {len(df_subset)}")

    # --- 7. Feature Engineering (on the new, larger SUBSET) ---
    df_subset['has_portfolio_link'] = df_subset['Resume'].apply(has_portfolio_link)
    df_subset['has_honors_or_certs'] = df_subset['Resume'].apply(has_honors_or_certs)
    df_subset['name_words'] = df_subset['Name'].apply(lambda x: set(str(x).lower().split()) if pd.notna(x) else set())
    df_subset['cleaned_resume'] = df_subset.apply(lambda row: clean_text_aggressively(row['Resume'], row['name_words']), axis=1)

    # --- THIS IS THE FIX ---
    # Extract the engineered features into their own variable
    engineered_features = df_subset[['has_portfolio_link', 'has_honors_or_certs']]
    # --- END FIX ---

    # --- 8. Create TF-IDF features ---
    vectorizer = TfidfVectorizer(
        stop_words='english',
        max_features=3000,
        min_df=3, 
        max_df=0.85,
        ngram_range=(1, 2)
    )
    
    tfidf_matrix = vectorizer.fit_transform(df_subset['cleaned_resume'])
    
    # This line will now work
    features_combined = hstack([tfidf_matrix, engineered_features])

    # --- 9. Prepare Data for Model ---
    target = df_subset['decision']
    X_train, X_test, y_train, y_test = train_test_split(
        features_combined, target, test_size=0.3, random_state=42
    )

    # --- 10. Train a Logistic Regression Model ---
    ml_model = LogisticRegression(random_state=42, solver='liblinear', max_iter=1000)
    ml_model.fit(X_train, y_train)

    # --- 11. Evaluate the New Model ---
    predictions = ml_model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    
    print(f"Success! Accuracy: {accuracy * 100:.2f}%")
    results.append({'Role': role, 'Accuracy': accuracy, 'Applicant_Count': len(df_subset)})

# --- 12. Final Report ---
print("\n--- Final Accuracy Report (with Augmented Data) ---")
if results:
    results_df = pd.DataFrame(results).sort_values(by='Accuracy', ascending=False)
    print(results_df.to_string(index=False))
else:
    print("No roles had sufficient data to train a model.")