
try:
    from vnstock import Vnstock, Finance
    print("Import successful")
    
    # Check Price
    stock = Vnstock().stock(symbol='VNM', source='VCI')
    print("Stock object created")
    
    # Try quote
    try:
        quote = stock.quote
        print("Stock Quote:", quote)
        # Using built-in simple quote if available or fetching history for latest
    except:
        print("quote property failed")

    # Try history for price
    try:
        hist = stock.quote.history(symbol='VNM', start='2024-12-20', end='2024-12-25')
        print("History head:")
        print(hist.tail(1))
    except Exception as e:
        print(f"History error: {e}")

except Exception as e:
    print(e)
