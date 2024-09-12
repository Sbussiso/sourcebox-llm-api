import pandas as pd
from sklearn.impute import SimpleImputer

def prepare_csv_for_embedding(file_path):
    """
    Cleans and prepares a CSV file for embedding by handling missing values,
    and retains text columns like country names without encoding them.
    
    Args:
    file_path (str): Path to the CSV file.

    Returns:
    List[str]: List of cleaned CSV rows as strings, with headers and their values concatenated.
    """
    
    # Step 1: Load CSV file
    df = pd.read_csv(file_path)

    # Step 2: Handle missing values
    # For numerical columns, fill missing values with the median
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
    imputer_num = SimpleImputer(strategy='median')
    df[numerical_cols] = imputer_num.fit_transform(df[numerical_cols])

    # For categorical columns (e.g., 'Country'), fill missing values with the most frequent value
    # We treat any non-numerical columns as text and retain them without encoding
    categorical_cols = df.select_dtypes(include=['object']).columns
    imputer_cat = SimpleImputer(strategy='most_frequent')
    df[categorical_cols] = imputer_cat.fit_transform(df[categorical_cols])

    # Step 3: Concatenate headers and values for each row into a single string for embedding
    rows_as_text = []
    for _, row in df.iterrows():
        row_str = " ".join([f"{col}: {val}" for col, val in row.items()])
        rows_as_text.append(row_str)

    return rows_as_text


if __name__ == "__main__":
    import os
    cwd = os.getcwd()
    file_path = os.path.join(cwd, 'test', 'WorldPopulation2023.csv')
    cleaned_data = prepare_csv_for_embedding(file_path)
    print(cleaned_data)
