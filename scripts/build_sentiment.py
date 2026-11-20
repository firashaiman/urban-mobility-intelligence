import argparse
from pathlib import Path

import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer


# Keep only the review fields used by the analysis. Reviewer profiles and
# other scraper metadata are left out of the output.
REVIEW_COLUMNS = [
    "place_id",
    "review_id",
    "rating",
    "review_text",
    "review_translated_text",
    "published_at_date",
]

OVERVIEW_COLUMNS = [
    "place_id",
    "name",
    "rating",
    "main_category",
    "categories",
    "address",
]


def load_station_reviews(
    mode: str, review_path: Path, overview_path: Path
) -> pd.DataFrame:
    # Read IDs as text and strip whitespace so both exports use the same join key.
    reviews = pd.read_csv(review_path, usecols=REVIEW_COLUMNS, dtype="string")
    overview = pd.read_csv(overview_path, usecols=OVERVIEW_COLUMNS, dtype="string")
    for table, path in ((reviews, review_path), (overview, overview_path)):
        table["place_id"] = table["place_id"].str.strip()
        if table["place_id"].fillna("").eq("").any():
            raise ValueError(f"{path} contains a missing place_id.")

    # Keep the individual star rating and the station-wide average as separate fields.
    overview = overview.rename(columns={"rating": "average_rating"})
    # A station can have many reviews, while its overview should have one row.
    # The left join keeps reviews visible during validation. Duplicate overview
    # keys or unmatched reviews cause the script to report an input error.
    merged = reviews[REVIEW_COLUMNS].merge(
        overview, on="place_id", how="left", validate="many_to_one", indicator=True
    )
    missing_metadata = merged["_merge"].eq("left_only").sum()
    if missing_metadata:
        raise ValueError(
            f"{review_path} has {missing_metadata} rows without matching overview metadata."
        )

    ordered_columns = REVIEW_COLUMNS + [
        "name",
        "average_rating",
        "main_category",
        "categories",
        "address",
    ]
    return merged[ordered_columns].assign(transport_type=mode.strip().upper())


def classify_sentiment(score: float) -> str:
    # Apply the FYP thresholds to the original compound score before rescaling it.
    if score >= 0.05:
        return "Positive"
    if score <= -0.05:
        return "Negative"
    return "Neutral"


def score_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    # VADER is rule-based and mainly English-oriented. Prefer the English
    # translation when present, then fall back to the original review text.
    analyzer = SentimentIntensityAnalyzer()
    original = reviews["review_text"].fillna("").str.strip()
    translated = reviews["review_translated_text"].fillna("").str.strip()
    text = translated.where(translated.ne(""), original)
    # The original workflow gives reviews with no text a zero score. These rows
    # become Neutral even though they contain no text to assess.
    scores = text.map(
        lambda value: analyzer.polarity_scores(value)["compound"] if value else 0.0
    )
    # Map VADER’s −1 to +1 score onto a 1–5 scale for comparison with star ratings.
    # The scaled value still represents text sentiment.
    return reviews.assign(
        sentiment_score=scores,
        sentiment_category=scores.map(classify_sentiment),
        sentiment_rating_scaled=((scores + 1) * 2 + 1).round(2),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        nargs=3,
        action="append",
        required=True,
        metavar=("MODE", "REVIEW_CSV", "OVERVIEW_CSV"),
        help="A matched source pair. Repeat to process additional stations.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output CSV path.")
    args = parser.parse_args()

    try:
        input_paths = {
            Path(path).resolve()
            for _, review, overview in args.source
            for path in (review, overview)
        }
        if args.output.resolve() in input_paths:
            raise ValueError("The output path must differ from all source paths.")
        frames = [
            load_station_reviews(mode, Path(review), Path(overview))
            for mode, review, overview in args.source
        ]
        # Combine station batches into a single table and reset the row index.
        scored = score_reviews(pd.concat(frames, ignore_index=True))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(args.output, index=False)
    except LookupError:
        parser.exit(
            1, "Install the VADER lexicon with python -m nltk.downloader vader_lexicon.\n"
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")

    print(f"Wrote {len(scored):,} review records to {args.output}")


if __name__ == "__main__":
    main()
