
from vnstock import Vnstock, Quote, Finance

print("Classes imported.")

try:
    print("\n--- Testing Quote ---")
    quote = Quote(symbol='HPG', source='VCI')
    # Try calling history if it exists, or look for methods
    print(f"Quote methods: {[m for m in dir(quote) if not m.startswith('_')]}")
    # df = quote.history(start='2023-01-01', end='2023-01-10')
    # print(df.head())
except Exception as e:
    print(f"Quote Error: {e}")

try:
    print("\n--- Testing Finance ---")
    fin = Finance(symbol='HPG', source='VCI')
    print(f"Finance methods: {[m for m in dir(fin) if not m.startswith('_')]}")
    # df = fin.ratio()
    # print(df.head())
except Exception as e:
    print(f"Finance Error: {e}")
