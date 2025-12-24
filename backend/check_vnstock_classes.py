
try:
    from vnstock import Vnstock
    print("Vnstock class found")
except ImportError:
    print("Vnstock class NOT found")

try:
    from vnstock import Quote
    print("Quote class found")
except ImportError:
    print("Quote class NOT found")

try:
    import vnstock.stock as stock
    print("vnstock.stock found")
except ImportError:
    print("vnstock.stock NOT found")
