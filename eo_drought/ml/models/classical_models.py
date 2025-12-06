from sklearn.ensemble import RandomForestClassifier

def make_default_drought_model(n_features: int) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
    )
