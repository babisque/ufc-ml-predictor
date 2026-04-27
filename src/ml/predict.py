import logging
import pandas as pd
import joblib
import os
from datetime import datetime

def get_fighter_profile(name, df):
    try:
        search_name = name.strip().lower()
        
        mask_f1 = df['f1_name'].astype(str).str.strip().str.lower() == search_name
        mask_f2 = df['f2_name'].astype(str).str.strip().str.lower() == search_name
        
        fights = df[mask_f1 | mask_f2]

        if fights.empty:
            logging.warning(f"No historical data found for fighter: {name}")
            return None
        
        last_fight = fights.sort_values(by='event_date').iloc[-1]

        is_f1 = str(last_fight['f1_name']).strip().lower() == search_name
        
        my_prefix = 'f1_' if is_f1 else 'f2_'
        opp_prefix = 'f2_' if is_f1 else 'f1_'

        time_minutes = last_fight['total_time_seconds'] / 60
        if time_minutes == 0: time_minutes = 1
        
        my_slpm = last_fight[f'{my_prefix}sig_str_landed'] / time_minutes
        opp_slpm = last_fight[f'{opp_prefix}sig_str_landed'] / time_minutes
        strike_adv = my_slpm - opp_slpm

        profile = {
            'name': last_fight[f'{my_prefix}name'],
            'age': last_fight.get(f'{my_prefix}age', 0),
            'height': last_fight.get(f'{my_prefix}height', 0),
            'reach': last_fight.get(f'{my_prefix}reach', 0),
            'f1_days_since_last': last_fight.get(f'{my_prefix}days_since_last', 180),
            'f1_win_streak': last_fight.get(f'{my_prefix}win_streak', 0),
            'f1_loss_streak': last_fight.get(f'{my_prefix}loss_streak', 0),
            'f1_strike_diff': strike_adv,
        }
        
        for col in df.columns:
            if col.startswith(my_prefix) and col not in [f'{my_prefix}name', f'{my_prefix}age', f'{my_prefix}height', f'{my_prefix}reach', f'{my_prefix}days_since_last', f'{my_prefix}win_streak', f'{my_prefix}loss_streak']:
                base_name = col.replace(my_prefix, 'f1_')
                profile[base_name] = last_fight[col]
                
        return profile
    
    except Exception as e:
        logging.error(f"Error retrieving profile for {name}: {e}")
        return None

def prepare_data_prevision(f1_profile, f2_profile, weight_class, training_columns, imputer):
    if f1_profile is None or f2_profile is None:
        return None

    data = {
        'age_diff': f1_profile['age'] - f2_profile['age'],
        'height_diff': f1_profile['height'] - f2_profile['height'],
        'reach_diff': f1_profile['reach'] - f2_profile['reach'],
        'ring_rust_diff': f1_profile['f1_days_since_last'] - f2_profile['f1_days_since_last'],
        'win_streak_diff': f1_profile['f1_win_streak'] - f2_profile['f1_win_streak'],
        'loss_streak_diff': f1_profile['f1_loss_streak'] - f2_profile['f1_loss_streak'],
        'strike_diff_advantage': f1_profile['f1_strike_diff'] - f2_profile['f1_strike_diff']
    }
    
    weight_col = f'weight_class_{weight_class}'
    data[weight_col] = 1

    for key, value in f1_profile.items():
        if key.startswith('f1_'):
            data[key] = value
            
    for key, value in f2_profile.items():
        if key.startswith('f1_'):
            f2_key = key.replace('f1_', 'f2_')
            data[f2_key] = value

    df_prev = pd.DataFrame([data])
    df_prev = df_prev.reindex(columns=training_columns, fill_value=0)
    
    return imputer.transform(df_prev)

def predict_winner(fighter_1, fighter_2, weight_class):
    model_path = 'models/ufc_random_forest.pkl'
    imputer_path = 'models/ufc_imputer.pkl'
    cols_path = 'models/ufc_model_columns.pkl'
    data_path = 'data/processed/balanced_fights.csv'

    if not all(os.path.exists(p) for p in [model_path, imputer_path, cols_path, data_path]):
        logging.error("Essential model or data files missing. Run the pipeline first.")
        return None

    model = joblib.load(model_path)
    imputer = joblib.load(imputer_path)
    training_columns = joblib.load(cols_path)
    historical_df = pd.read_csv(data_path)

    f1 = get_fighter_profile(fighter_1, historical_df)
    f2 = get_fighter_profile(fighter_2, historical_df)

    if f1 and f2:
        X_new = prepare_data_prevision(f1, f2, weight_class, training_columns, imputer)
        if X_new is not None:
            prediction = model.predict(X_new)
            probability = model.predict_proba(X_new)

            winner = fighter_1 if prediction[0] == 1 else fighter_2
            prop = probability[0][1] if prediction[0] == 1 else probability[0][0]
            
            return {
                'winner': winner,
                'confidence': prop * 100
            }
            
    logging.warning("Failed to prepare prediction data.")
    return None

if __name__ == "__main__":
    result = predict_winner("Ciryl Gane", "Alex Pereira", "Heavyweight")
    if result:
        logging.info("="*50)
        logging.info(f"PREDICTED WINNER: {result['winner']}")
        logging.info(f"AI Confidence: {result['confidence']:.2f}%")
        logging.info("="*50)