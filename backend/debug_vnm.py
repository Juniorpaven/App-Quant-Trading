
from vnstock import Finance, Stock
import pandas as pd

def check_vnm_fundamentals():
    print("Checking VNM Fundamentals...")
    try:
        # 1. Get Financial Ratios (Quarterly)
        fin = Finance(symbol='VNM', source='VCI')
        df_ratio = fin.ratio(period='quarterly', lang='vi')
        
        if isinstance(df_ratio.columns, pd.MultiIndex):
            df_ratio.columns = [' '.join(col).strip() for col in df_ratio.columns.values]
            
        # Find EPS column
        eps_col = next((c for c in df_ratio.columns if 'eps' in c.lower() or 'lợi nhuận trên mỗi' in c.lower()), None)
        print(f"EPS Column found: {eps_col}")
        
        if eps_col:
            # Take last 4 quarters
            last_4 = df_ratio.head(4)
            print("Last 4 quarters data:")
            print(last_4[['Meta Năm', 'Meta Kỳ', eps_col]])
            
            eps_ttm = last_4[eps_col].sum()
            print(f"EPS TTM (Sum 4 quarters): {eps_ttm}")
            
        # 2. Get Current Price
        stock = Stock(symbol='VNM', source='VCI')
        quote = stock.quote()
        # quote usually returns a dataframe with 'close' or 'price'
        print("Quote Data:")
        print(quote)
        
        current_price = quote['close'].iloc[0] if not quote.empty else 0
        print(f"Current Price: {current_price}")
        
        if eps_ttm and current_price:
            pe_realtime = current_price / eps_ttm
            print(f"Calculated P/E (Price/EPS_TTM): {pe_realtime}")

    except Exception as e:
        print(f"Error: {e}")

check_vnm_fundamentals()
