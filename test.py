import pandas as pd

csv_file = 'Dataset/dataset.csv'

try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"Error: Could not find '{csv_file}'.")
    exit()

# Let's check the 'Role' column
if 'Role' in df.columns:
    print("--- Applicant Counts Per Role ---")
    print(df['Role'].value_counts())
    
    # Get the top 5 most common roles
    top_roles = df['Role'].value_counts().head(5).index.tolist()
    if top_roles:
        print(f"\nRecommendation: This approach will work well!")
        print(f"Try setting your TARGET_ROLE to one of these: {top_roles}")
    else:
        print("\nWarning: No 'Role' column found or it's empty.")

else:
    print("Warning: This dataset does not have a 'Role' column.")
    print("You may need to group by 'Job_Description' text, but this is less reliable.")