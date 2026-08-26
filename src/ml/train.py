import pandas as pd
import numpy as np
import joblib
import os
import json
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)

METRICS_PATH = 'models/metrics.json'
CANDIDATE_METRICS_PATH = 'models/metrics_candidate.json'
PROMOTION_TOLERANCE = 0.005  # allow up to 0.5pp accuracy regression before withholding promotion
TEST_FRACTION = 0.2

SPOILERS = [
    'f1_kd', 'f2_kd', 'f1_sig_str_landed', 'f2_sig_str_landed',
    'f1_sig_str_attempted', 'f2_sig_str_attempted', 'f1_sig_pct', 'f2_sig_pct',
    'f1_tot_str_landed', 'f2_tot_str_landed', 'f1_tot_str_attempted', 'f2_tot_str_attempted',
    'f1_td_landed', 'f2_td_landed', 'f1_td_attempted', 'f2_td_attempted',
    'f1_td_pct', 'f2_td_pct', 'f1_sub_att', 'f2_sub_att',
    'f1_rev', 'f2_rev', 'f1_ctrl', 'f2_ctrl', 'total_time_seconds', 'method_detail',
]

TEXT_COLUMNS = ['f1_name', 'f2_name', 'f1_link', 'f2_link', 'event_date', 'referee']


def load_training_data():
    """Load the fully engineered training set produced by feature_engineering.py -> shuffle_data.py -> pairwise_features.py."""
    data_path = 'data/processed/balanced_fights.csv'
    if not os.path.exists(data_path):
        print(f"Error: File {data_path} not found.")
        return None
    return pd.read_csv(data_path)


def temporal_split(df):
    """Split chronologically instead of randomly: the last ~20% of event dates become the
    held-out set. Splitting on the date value (not row position) guarantees a fight's two
    shuffled mirror rows -- which always share the same event_date -- land on the same side."""
    unique_dates = np.sort(df['event_date'].unique())
    cutoff_idx = int(len(unique_dates) * (1 - TEST_FRACTION))
    cutoff_date = unique_dates[cutoff_idx]

    train_mask = df['event_date'] < cutoff_date
    test_mask = ~train_mask
    return train_mask, test_mask, cutoff_date


def compute_metrics(y_true, y_pred, y_proba):
    return {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_true, y_proba),
        'brier_score': brier_score_loss(y_true, y_proba),
        'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
    }


def compute_baselines(df, test_mask, y_test):
    """Naive comparators to contextualize the model's accuracy. The dataset is 50/50 by
    construction (shuffle_data.py mirrors every fight), so majority-class is a weak sanity
    check; the Elo baseline (once f1_elo/f2_elo exist) is the meaningful one."""
    majority_class = int(y_test.mode().iloc[0])
    majority_pred = pd.Series(majority_class, index=y_test.index)
    baselines = {
        'majority_class_accuracy': accuracy_score(y_test, majority_pred),
    }

    if 'f1_elo' in df.columns and 'f2_elo' in df.columns:
        elo_pred = (df.loc[test_mask, 'f1_elo'] > df.loc[test_mask, 'f2_elo']).astype(int)
        baselines['elo_accuracy'] = accuracy_score(y_test, elo_pred)
    else:
        baselines['elo_accuracy'] = None

    return baselines


def load_previous_metrics():
    if not os.path.exists(METRICS_PATH):
        return None
    with open(METRICS_PATH) as f:
        return json.load(f)


def train_model():
    df = load_training_data()
    if df is None:
        return

    df['event_date'] = pd.to_datetime(df['event_date'])
    df = df.sort_values('event_date').reset_index(drop=True)

    train_mask, test_mask, cutoff_date = temporal_split(df)

    df_model = df.drop(columns=SPOILERS, errors='ignore')
    df_model = df_model.drop(columns=TEXT_COLUMNS, errors='ignore')

    X = df_model.drop('target', axis=1)
    y = df_model['target']

    training_columns = X.columns.tolist()

    X_train, X_test = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]

    imputer = SimpleImputer(strategy='mean')
    X_train_clean = imputer.fit_transform(X_train)
    X_test_clean = imputer.transform(X_test)

    model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42)
    model.fit(X_train_clean, y_train)

    y_pred = model.predict(X_test_clean)
    y_proba = model.predict_proba(X_test_clean)[:, 1]

    metrics = compute_metrics(y_test, y_pred, y_proba)
    baselines = compute_baselines(df, test_mask, y_test)

    metrics_record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'n_train': int(train_mask.sum()),
        'n_test': int(test_mask.sum()),
        'test_cutoff_date': str(cutoff_date),
        'baseline_majority_class_accuracy': baselines['majority_class_accuracy'],
        'baseline_elo_accuracy': baselines['elo_accuracy'],
        **metrics,
    }

    previous = load_previous_metrics()
    os.makedirs('models', exist_ok=True)

    if previous is None:
        promote = True
        reason = "no previous model to compare against; auto-promoting"
    elif metrics_record['accuracy'] >= previous['accuracy'] - PROMOTION_TOLERANCE:
        promote = True
        reason = (f"accuracy {metrics_record['accuracy']:.4f} not worse than previous "
                   f"{previous['accuracy']:.4f} beyond tolerance {PROMOTION_TOLERANCE}")
    else:
        promote = False
        reason = (f"accuracy {metrics_record['accuracy']:.4f} worse than previous "
                   f"{previous['accuracy']:.4f} beyond tolerance {PROMOTION_TOLERANCE}")

    metrics_record['promoted'] = promote
    metrics_record['promotion_reason'] = reason

    print(f"Test accuracy: {metrics['accuracy']:.2%} | Precision: {metrics['precision']:.4f} | "
          f"Recall: {metrics['recall']:.4f} | F1: {metrics['f1']:.4f} | "
          f"ROC-AUC: {metrics['roc_auc']:.4f} | Brier: {metrics['brier_score']:.4f}")
    print(f"Confusion matrix (rows=true, cols=pred): {metrics['confusion_matrix']}")
    elo_msg = (f"{baselines['elo_accuracy']:.2%}" if baselines['elo_accuracy'] is not None
               else "unavailable (elo feature not yet computed)")
    print(f"Baselines - majority class: {baselines['majority_class_accuracy']:.2%} | elo: {elo_msg}")

    if promote:
        joblib.dump(model, 'models/ufc_random_forest.pkl')
        joblib.dump(imputer, 'models/ufc_imputer.pkl')
        joblib.dump(training_columns, 'models/ufc_model_columns.pkl')
        with open(METRICS_PATH, 'w') as f:
            json.dump(metrics_record, f, indent=2)
        print(f"Model promoted: {reason}")
    else:
        with open(CANDIDATE_METRICS_PATH, 'w') as f:
            json.dump(metrics_record, f, indent=2)
        print(f"Model NOT promoted, previous model kept: {reason}")
        print(f"Candidate metrics saved to {CANDIDATE_METRICS_PATH} for inspection.")

    # A candidate not clearing the promotion bar is an expected outcome, not a pipeline
    # failure -- pipeline.py aborts on any non-zero exit, so this must still exit 0.


if __name__ == "__main__":
    train_model()
