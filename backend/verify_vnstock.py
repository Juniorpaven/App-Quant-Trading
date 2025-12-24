
import vnstock
import inspect

print("Attempting to find stock_historical_data...")

if hasattr(vnstock, 'stock_historical_data'):
    print("Found at top level!")
else:
    print("Not at top level.")
    # Check submodules
    for name, obj in inspect.getmembers(vnstock):
        if inspect.ismodule(obj):
            print(f"Checking module: {name}")
            if hasattr(obj, 'stock_historical_data'):
                print(f"FOUND in {name}!")

# Try importing from 'vnstock.stock' if it exists in list
try:
    from vnstock import stock
    if hasattr(stock, 'stock_historical_data'):
        print("Found in vnstock.stock")
except ImportError:
    print("vnstock.stock import failed")

# Try to find 'stock_ls_analysis'
print("\nAttempting to find stock_ls_analysis...")
if hasattr(vnstock, 'stock_ls_analysis'):
    print("Found at top level!")
