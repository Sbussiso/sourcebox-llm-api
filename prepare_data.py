import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer

def prepare_csv_for_embedding(file_path):
    """
    Cleans and prepares a CSV file for embedding by handling missing values,
    encoding categorical columns, and preparing text data for embedding.

    Args:
    file_path (str): Path to the CSV file.

    Returns:
    List[str]: List of cleaned CSV rows as strings, ready for embedding.
    """
    
    # Step 1: Load CSV file
    df = pd.read_csv(file_path)

    # Step 2: Handle missing values
    # For numerical columns, fill missing values with the median
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
    imputer_num = SimpleImputer(strategy='median')
    df[numerical_cols] = imputer_num.fit_transform(df[numerical_cols])

    # For categorical columns, fill missing values with the most frequent value
    categorical_cols = df.select_dtypes(include=['object']).columns
    imputer_cat = SimpleImputer(strategy='most_frequent')
    df[categorical_cols] = imputer_cat.fit_transform(df[categorical_cols])

    # Step 3: Encode categorical columns
    label_encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        label_encoders[col] = le  # Save the encoder for potential reverse mapping

    # Step 4: Convert each row of the DataFrame into a single string for embedding
    return df.astype(str).agg(' '.join, axis=1).tolist()
