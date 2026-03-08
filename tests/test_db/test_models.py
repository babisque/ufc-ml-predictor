from src.db import connection, models


def test_init_and_save_prediction_deduplicates(tmp_path, monkeypatch):
    db_file = tmp_path / "preds.db"
    monkeypatch.setattr(connection, "DB_PATH", str(db_file))
    monkeypatch.setattr(models, "get_db_connection", connection.get_db_connection)

    models.init_db()
    models.save_prediction("UFC 300", "A", "B", "Lightweight", "A", 0.7)
    models.save_prediction("UFC 300", "A", "B", "Lightweight", "A", 0.7)

    rows = models.get_event_predictions("UFC 300")
    assert len(rows) == 1
    assert rows[0][0] == "A"
    assert rows[0][1] == "B"
    assert rows[0][3] == "A"


def test_get_statistics_and_last_event(tmp_path, monkeypatch):
    db_file = tmp_path / "preds.db"
    monkeypatch.setattr(connection, "DB_PATH", str(db_file))
    monkeypatch.setattr(models, "get_db_connection", connection.get_db_connection)

    models.init_db()
    models.save_prediction("UFC X", "F1", "F2", "WW", "F1", 0.8)
    models.save_prediction("UFC X", "F3", "F4", "LW", "F3", 0.6)
    models.save_prediction("Individual Fight", "I1", "I2", "MW", "I1", 0.55)

    with connection.get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE predictions SET actual_winner = ?, is_correct = ? WHERE event_name = ? AND fighter_1 = ?",
            ("F1", 1, "UFC X", "F1"),
        )
        cur.execute(
            "UPDATE predictions SET actual_winner = ?, is_correct = ? WHERE event_name = ? AND fighter_1 = ?",
            ("F4", 0, "UFC X", "F3"),
        )
        conn.commit()

    total_resolved, total_correct, total_pending = models.get_statistics()
    assert total_resolved == 2
    assert total_correct == 1
    assert total_pending >= 0

    event, total, correct, fights = models.get_last_event_predictions()
    assert event == "UFC X"
    assert total == 2
    assert correct == 1
    assert len(fights) >= 2