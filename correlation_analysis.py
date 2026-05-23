import pandas as pd

# Path to the CSV file (adjust if necessary)
csv_path = r"C:\\Users\\zerou\\Downloads\\COINBASE_LTCUSDC.P, 30.csv"

# Load the CSV into a DataFrame
try:
    df = pd.read_csv(csv_path)
except Exception as e:
    print(f"Failed to read CSV: {e}")
    raise

# Ensure 'close' column exists
if 'close' not in df.columns:
    print("'close' column not found in the CSV.")
    raise KeyError('close')

# Compute correlation of 'close' with all other numeric columns, excluding open, high, low, and time
numeric_df = df.select_dtypes(include=['number'])
# Drop unwanted columns if they exist
cols_to_drop = ['open', 'high', 'low', 'time']
numeric_df = numeric_df.drop(columns=[c for c in cols_to_drop if c in numeric_df.columns])
# Compute overall correlations
correlations = numeric_df.corr()['close'].drop('close')
# Compute correlations for metrics starting with 'ucs_rh_irb'
ucs_columns = [col for col in numeric_df.columns if col.startswith('ucs_rh_irb')]
ucs_correlations = numeric_df[ucs_columns].corr()['close'].drop('close') if ucs_columns else pd.Series(dtype=float)
# Determine highest correlation
max_corr_value = correlations.max()
max_corr_column = correlations.idxmax()
# Print results
print("Correlation of 'close' price with other numeric columns (excluding open, high, low, time):")
print(correlations)
print(f"\nHighest correlation: {max_corr_column} = {max_corr_value}")
if not ucs_correlations.empty:
    print("\nCorrelation of 'close' with ucs_rh_irb metrics:")
    print(ucs_correlations)


print("Correlation of 'close' price with other numeric columns:")
print(correlations)
