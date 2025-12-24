
try:
    from vnstock import Vnstock
    print("Vnstock imported successfully")
    
    try:
        stock = Vnstock().stock(symbol='HPG', source='VCI')
        print("Stock object created")
        
        # Try to get finance/ratio data
        # Documentation usually says stock.finance.ratio() or similar
        try:
             # Inspecting available methods/properties
             print("Attributes of stock object:", dir(stock))
             
             if hasattr(stock, 'finance'):
                 print("Finance attribute found")
                 ratio = stock.finance.ratio(period='quarterly', lang='vi')
                 print("Ratio data using stock.finance.ratio():")
                 print(ratio.head())
             else:
                 print("No 'finance' attribute on stock object")
                 
             # Try existing method in main.py logic check
             from vnstock import Finance
             print("Imported Finance class directly")
             fin = Finance(symbol='HPG', source='VCI')
             df = fin.ratio(period='quarterly', lang='vi')
             print("Finance().ratio() result:")
             print(df.head())

        except Exception as e:
            print(f"Inner error: {e}")
            
    except Exception as e:
        print(f"Setup error: {e}")

except Exception as e:
    print(f"Import error: {e}")
