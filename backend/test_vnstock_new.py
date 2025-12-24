
try:
    from vnstock import stock_historical_data, stock_ls_analysis, listing_companies
    print("Import success")
    
    # Test Historical Data
    df = stock_historical_data("HPG", "2023-01-01", "2023-01-10", "1D", "stock")
    print(f"Historical Data:\n{df.head()}")

    # Test Fundamentals
    # Note: stock_ls_analysis might need specific parameters or might use different function in v3
    # User snippet: df = stock_ls_analysis(ticker, lang='vi', days_to_now=1)
    # Let's try that
    try:
        fund = stock_ls_analysis("HPG", lang='vi')
        print(f"Fundamentals:\n{fund.head()}")
    except Exception as e:
        print(f"Fundamentals Error: {e}")

    # Test VN30 list
    try:
        # listing_companies returning DataFrame
        test_ls = listing_companies(group='VN30')
        print(f"VN30 List:\n{test_ls.head()}")
    except Exception as e:
        print(f"List Error: {e}")

except Exception as e:
    print(f"Import Error: {e}")
