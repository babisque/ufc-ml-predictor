import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def feature_engineering():
    """Read cleaned data, calculate historical averages and attribute differences."""
    data_path = 'data/processed/balanced_fights.csv'
    if not os.path.exists(data_path):
        print(f"Error: File {data_path} not found.")
        return None

    df = pd.read_csv(data_path)
    
    df['diff_age'] = df['f1_age'] - df['f2_age']
    df['diff_height'] = df['f1_height'] - df['f2_height']
    df['diff_reach'] = df['f1_reach'] - df['f2_reach']

    encoding_columns = ['weight_class', 'f1_stance', 'f2_stance']
    df = pd.get_dummies(df, columns=encoding_columns, drop_first=True)

    df['event_date'] = pd.to_datetime(df['event_date'])
    df = df.sort_values(by='event_date', ascending=True)
    df.reset_index(drop=True, inplace=True)

    f1_statistics = ['f1_kd', 'f1_sig_str_landed', 'f1_td_landed', 'f1_ctrl', 'f1_sig_pct']
    f2_statistics = ['f2_kd', 'f2_sig_str_landed', 'f2_td_landed', 'f2_ctrl', 'f2_sig_pct']

    for col in f1_statistics:
        new_col = col + '_hist_avg'
        df[new_col] = df.groupby('f1_name')[col].transform(lambda x: x.shift(1).expanding().mean())

    for col in f2_statistics:
        new_col = col + '_hist_avg'
        df[new_col] = df.groupby('f2_name')[col].transform(lambda x: x.shift(1).expanding().mean())

    historical_columns = [c + '_hist_avg' for c in f1_statistics + f2_statistics]
    df[historical_columns] = df[historical_columns].fillna(0)

    os.makedirs('data/processed', exist_ok=True)
    df.to_csv('data/processed/historical_df.csv', index=False)
    
    return df

def train_model():
    df = feature_engineering()
    if df is None:
        return

    spoilers = [
        'f1_kd', 'f2_kd', 'f1_sig_str_landed', 'f2_sig_str_landed',
        'f1_sig_str_attempted', 'f2_sig_str_attempted', 'f1_sig_pct', 'f2_sig_pct',
        'f1_tot_str_landed', 'f2_tot_str_landed', 'f1_tot_str_attempted', 'f2_tot_str_attempted',
        'f1_td_landed', 'f2_td_landed', 'f1_td_attempted', 'f2_td_attempted',
        'f1_td_pct', 'f2_td_pct', 'f1_sub_att', 'f2_sub_att',
        'f1_rev', 'f2_rev', 'f1_ctrl', 'f2_ctrl', 'total_time_seconds', 'method_detail',
        'f1_age', 'f2_age', 'f1_reach', 'f2_reach', 'f1_height', 'f2_height',
    ]

    df_model = df.drop(columns=spoilers, errors='ignore')
    
    text_columns = ['f1_name', 'f2_name', 'f1_link', 'f2_link', 'event_date', 'referee']
    df_model = df_model.drop(columns=text_columns, errors='ignore')

    X = df_model.drop('target', axis=1)
    y = df_model['target']

    training_columns = X.columns.tolist()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    imputer = SimpleImputer(strategy='mean')
    X_train_clean = imputer.fit_transform(X_train)
    X_test_clean = imputer.transform(X_test)

    model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42)
    model.fit(X_train_clean, y_train)

    y_pred = model.predict(X_test_clean)
    acc = accuracy_score(y_test, y_pred)
    print(f"Training complete. Test accuracy: {acc:.2%}")

    os.makedirs('models', exist_ok=True)
    joblib.dump(model, 'models/ufc_random_forest.pkl')
    joblib.dump(imputer, 'models/ufc_imputer.pkl')
    joblib.dump(training_columns, 'models/ufc_model_columns.pkl')

if __name__ == "__main__":
    train_model()
