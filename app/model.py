import os
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'lgbm_fare.pkl')

FEATURES = [
    'trip_distance',
    'passenger_count',
    'hour',
    'day_of_week',
    'trip_duration_min',
    'pickup_zone_id',
    'dropoff_zone_id',
]
TARGET = 'fare_amount'


def train(df: pd.DataFrame) -> dict:
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=63,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = r2_score(y_test, y_pred)

    importance = dict(zip(FEATURES, model.feature_importances_.tolist()))

    return {
        'mae': round(mae, 4),
        'rmse': round(rmse, 4),
        'r2': round(r2, 4),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'feature_importance': importance,
    }


def predict(data: dict) -> float:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError('Model not trained yet')
    model = joblib.load(MODEL_PATH)
    df = pd.DataFrame([data])[FEATURES]
    return float(model.predict(df)[0])


def is_trained() -> bool:
    return os.path.exists(MODEL_PATH)
