import argparse

from eo_drought.ml.global_climate_ml import (
    analyze_field,
    print_report,
    make_feature_vector,
    build_training_dataset,
    train_ml_model,
    recommend_irrigation,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Global climate + Sentinel-2 ML drought & irrigation intelligence (EO Drought)."
    )
    parser.add_argument("--name", type=str, required=True, help="Field name")
    parser.add_argument("--crop", type=str, default="Unknown", help="Crop name")
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--days-back", type=int, default=10,
                        help="Number of days back from today to analyze.")
    parser.add_argument("--train-samples", type=int, default=20,
                        help="Number of random global fields for ML training.")
    parser.add_argument("--seed", type=int, default=0,
                        help="Random seed for reproducibility.")
    args = parser.parse_args()

    print("=== BUILDING TRAINING DATASET (GLOBAL CLIMATE + S2 ML) ===")
    X, y = build_training_dataset(
        num_samples=args.train_samples,
        days_back=args.days_back,
        seed=args.seed,
    )

    print("\n=== TRAINING RANDOM FOREST REGRESSOR ===")
    model, metrics = train_ml_model(
        X,
        y,
        test_fraction=0.25,
        seed=args.seed,
    )
    print("ML model performance (predicting analytic drought risk):")
    print(f"- R^2: {metrics['r2']:.3f} (may be NaN if test size=1)")
    print(f"- MAE: {metrics['mae']:.2f} risk points")
    print(f"- Train size: {metrics['n_train']}, Test size: {metrics['n_test']}")
    print()

    print("=== ANALYZING TARGET FIELD (ANALYTIC + EO + ML) ===")
    report = analyze_field(
        name=args.name,
        crop=args.crop,
        lat=args.lat,
        lon=args.lon,
        days_back=args.days_back,
    )
    print_report(report)

    x = make_feature_vector(report.features)
    ml_risk = float(model.predict(x.reshape(1, -1))[0])
    print("ML-calibrated risk (RandomForest on global climate + S2 features):")
    print(f"- Drought / water-stress risk (ML): {ml_risk:.1f}/100.\n")

    rec_text = recommend_irrigation(report, ml_risk)
    print(rec_text)


if __name__ == "__main__":
    main()
