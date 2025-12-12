
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

# Create dummy data
data = {
    'RSI': np.random.uniform(20, 80, 100),
    'Dist_SMA20': np.random.uniform(-0.1, 0.1, 100),
    'Return_1d': np.random.uniform(-0.05, 0.05, 100),
    'Vol_20': np.random.uniform(0.01, 0.03, 100),
    'Target': np.random.randint(0, 2, 100)
}
df = pd.DataFrame(data)

# Features and Target
X = df[['RSI', 'Dist_SMA20', 'Return_1d', 'Vol_20']]
y = df['Target']

# Train Model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# Save Model
joblib.dump(model, 'quant_ai_model.pkl')
print("Dummy model created: quant_ai_model.pkl")
