import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import os

# Try both absolute and relative imports for flexibility
try:
    from visualization.plot_style import apply_github_dark_theme, github_palette
except ImportError:
    from plot_style import apply_github_dark_theme, github_palette

# Apply the theme
apply_github_dark_theme()

# Find the correct path to the CSV file
current_dir = Path(__file__).parent
project_root = current_dir.parent if current_dir.name == 'visualization' else current_dir
csv_path = project_root / "assets" / "for_google_spreadsheet.csv"

# Load data
df = pd.read_csv(csv_path, sep="\t")

# Check required columns
required_columns = {"Ticker", "Net Dividend"}
if not required_columns.issubset(df.columns):
    raise ValueError(
        f"Missing required columns {required_columns} in the CSV file.")

# Extract currency
df["Currency"] = df["Net Dividend"].astype(str).apply(
    lambda x: "PLN" if "PLN" in x else "$" if "USD" in x else "")

# Convert "Net Dividend" to float
df["Net Dividend"] = df["Net Dividend"].astype(
    str).str.replace(r'[^0-9.]', '', regex=True).astype(float)

# Convert date
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"])

# Create ticker-currency mapping
ticker_currency_map = df.groupby("Ticker")["Currency"].first().to_dict()

# Ensure the palette matches the number of unique tickers
unique_tickers = df["Ticker"].unique()
palette = github_palette[:len(unique_tickers)]

# Plot
plt.figure(num="Net Dividend Chart", figsize=(7, 5))
ax = sns.barplot(data=df, x="Ticker", y="Net Dividend", estimator=sum,
                 errorbar=None, hue="Ticker", palette=palette, legend=False)

# Labels
plt.title("Net Dividend", fontsize=10, color='#61AFEF')
plt.xlabel("Ticker", fontsize=8, color='#61AFEF')
plt.ylabel("Total Net Dividend", fontsize=10, color='#61AFEF')
plt.xticks(rotation=10)

# Remove borders
sns.despine()

# Properly label each bar with the correct currency
for p, ticker in zip(ax.patches, unique_tickers):
    currency = ticker_currency_map.get(ticker, "")
    ax.annotate(f'{p.get_height():.2f} {currency}',
                (p.get_x() + p.get_width() / 2., p.get_height() / 2),
                ha='center', va='center', fontsize=8, color='white')

plt.show()
