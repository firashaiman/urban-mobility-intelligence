# Running the reconstructed pipelines

The scripts were reconstructed after the FYP using the report, source samples, and original exports. The live Power BI report presents the original analysis. Running the scripts with current feeds can produce different results as operators update their schedules.

## Setup on Windows

Open PowerShell in the repository folder. With Python 3.12 installed, run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m nltk.downloader vader_lexicon
```

The VADER lexicon is required for the sentiment script.

## Build the schedule dataset

Download the [Prasarana Rapid Rail KL feed](https://api.data.gov.my/gtfs-static/prasarana?category=rapid-rail-kl). Extract the ZIP so `trips.txt`, `routes.txt`, `stops.txt`, and `stop_times.txt` are directly inside `data/raw/prasarana/`. Keep `calendar.txt` in the same folder if the feed includes it.

```powershell
.\.venv\Scripts\python.exe scripts/build_operations.py --source prasarana data/raw/prasarana --output outputs/operations.csv
```

For other operators, extract each feed into its own folder and repeat `--source`. Use `ktmb` for KTMB and `basmy` for each BAS.MY feed. See the [official feed list](https://developer.data.gov.my/realtime-api/gtfs-static.en) and the [data dictionary](data-dictionary.md) for sources and column definitions.

Each output row represents a scheduled stop record. The script uses the recurring weekly calendar where available. It does not expand frequency templates into individual departures or apply date-specific service exceptions.

## Try the sentiment pipeline with synthetic data

The records below are fictional. They demonstrate three cases without sharing any original Google Maps review data.

```powershell
New-Item -ItemType Directory -Force data/raw/demo | Out-Null

@'
place_id,review_id,rating,review_text,review_translated_text,published_at_date
demo-station,review-1,5,Excellent service!,,2026-01-01
demo-station,review-2,1,Terrible experience.,,2026-01-02
demo-station,review-3,3,,,2026-01-03
'@ | Set-Content -Encoding utf8 data/raw/demo/reviews.csv

@'
place_id,name,rating,main_category,categories,address
demo-station,Example Station,3.0,Train station,Train station,Example address
'@ | Set-Content -Encoding utf8 data/raw/demo/overview.csv

.\.venv\Scripts\python.exe scripts/build_sentiment.py --source LRT data/raw/demo/reviews.csv data/raw/demo/overview.csv --output outputs/demo_sentiment.csv
```

Open `outputs/demo_sentiment.csv`. The expected labels are `Positive`, `Negative`, and `Neutral`. The third row follows the original FYP rule that assigns a zero score to records with no review text.
