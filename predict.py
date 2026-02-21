import pandas as pd
import joblib
from datetime import datetime

model = joblib.load('models/ufc_random_forest.pkl')
imputer = joblib.load('models/ufc_imputer.pkl')
training_columns = joblib.load('models/ufc_model_columns.pkl')

try:
    historical_df = pd.read_csv('data/processed/historical_df.csv')
except FileNotFoundError:
    print("Historical fights data not found. Please run the data processing script first.")
    historical_df = pd.DataFrame()

def get_fighter_profile(name, df):
    """Extract the most recent fighter profile from historical fight data."""
    fights = df[df['f1_name'] == name]

    if fights.empty:
        print(f"Warning: No historical data found for fighter: {name}")
        return None
    
    last_fight = fights.sort_values(by='event_date').iloc[-1]

    profile = {
        'name': name,
        'age': last_fight['f1_age'],
        'height': last_fight['f1_height'],
        'reach': last_fight['f1_reach'],
        'ctrl_hist_avg': last_fight.get('f1_ctrl_hist_avg', 0),
        'sig_pct_hist_avg': last_fight.get('f1_sig_pct_hist_avg', 0),
        'kd_hist_avg': last_fight.get('f1_kd_hist_avg', 0),
        'sig_str_landed_hist_avg': last_fight.get('f1_sig_str_landed_hist_avg', 0),
        'td_landed_hist_avg': last_fight.get('f1_td_landed_hist_avg', 0),
    }
    
    stance_cols = [col for col in df.columns if str(col).startswith('f1_stance_')]
    for col in stance_cols:
        profile[col] = last_fight[col]
        
    return profile

def prepare_data_prevision(f1_profile, f2_profile, weight_class):
    """Prepare and align fighter data for model prediction by calculating differences and encoding features."""
    if f1_profile is None or f2_profile is None:
        return None

    data = {
        'diff_age': f1_profile['age'] - f2_profile['age'],
        'diff_height': f1_profile['height'] - f2_profile['height'],
        'diff_reach': f1_profile['reach'] - f2_profile['reach'],
        'f1_ctrl_hist_avg': f1_profile['ctrl_hist_avg'],
        'f1_sig_pct_hist_avg': f1_profile['sig_pct_hist_avg'],
        'f1_kd_hist_avg': f1_profile['kd_hist_avg'],
        'f1_sig_str_landed_hist_avg': f1_profile['sig_str_landed_hist_avg'],
        'f1_td_landed_hist_avg': f1_profile['td_landed_hist_avg'],
        'f2_ctrl_hist_avg': f2_profile['ctrl_hist_avg'],
        'f2_sig_pct_hist_avg': f2_profile['sig_pct_hist_avg'],
        'f2_kd_hist_avg': f2_profile['kd_hist_avg'],
        'f2_sig_str_landed_hist_avg': f2_profile['sig_str_landed_hist_avg'],
        'f2_td_landed_hist_avg': f2_profile['td_landed_hist_avg'],
    }
    
    weight_col = f'weight_class_{weight_class}'
    data[weight_col] = 1

    for key, value in f1_profile.items():
        if key.startswith('f1_stance_'):
            data[key] = value
            
    for key, value in f2_profile.items():
        if key.startswith('f1_stance_'):
            f2_key = key.replace('f1_stance_', 'f2_stance_')
            data[f2_key] = value

    df_prev = pd.DataFrame([data])
    df_prev = df_prev.reindex(columns=training_columns, fill_value=0)
    
    return imputer.transform(df_prev)

if __name__ == "__main__":
    fighter_1 = "Ciryl Gane"
    fighter_2 = "Alex Pereira"
    weight_class = "Heavyweight"

    print(f"\nPreparing prediction for: {fighter_1} vs {fighter_2} in {weight_class} category...\n")
    
    f1 = get_fighter_profile(fighter_1, historical_df)
    f2 = get_fighter_profile(fighter_2, historical_df)

    if f1 is not None and f2 is not None:
        X_new = prepare_data_prevision(f1, f2, weight_class)
        
        if X_new is not None:
            print("Querying the Inference Engine (Random Forest)...")
            
            prediction = model.predict(X_new)
            probability = model.predict_proba(X_new)

            winner = fighter_1 if prediction[0] == 1 else fighter_2
            prop = probability[0][1] if prediction[0] == 1 else probability[0][0]

            print("="*50)
            print(f"PREDICTED WINNER: {winner}")
            print(f"AI Confidence: {prop:.2%}")
            print("="*50)
        else:
            print("Error preparing data row for the model.")
    else:
        print("Prediction cancelled. Missing historical data for one of the fighters.")