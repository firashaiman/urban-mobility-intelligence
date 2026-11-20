# Data sources and dictionary

## Sources

| Source | Role in the project | Access |
|---|---|---|
| Prasarana Static GTFS | Schedules for LRT, MRT, Monorail and BRT | [Rapid Rail KL feed](https://api.data.gov.my/gtfs-static/prasarana?category=rapid-rail-kl) |
| KTMB Static GTFS | KTM schedules | [KTMB feed](https://api.data.gov.my/gtfs-static/ktmb) |
| BAS.MY Static GTFS | Bus schedules for Alor Setar, Kangar, Ipoh, Johor Bahru, Kota Bharu, Kuala Terengganu, Melaka and Seremban | [Official feed list](https://developer.data.gov.my/realtime-api/gtfs-static.en) |
| Google Maps review and station overview exports | Review text, individual star ratings and station metadata | Original exports are kept private |

The official GTFS feeds are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source data is credited to the respective operators via data.gov.my. The project joins the source tables and derives additional analytical columns. The API links serve current feeds, which can differ from the snapshots used for the FYP.

## GTFS inputs and joins

| Input | What it contains | Fields used to connect tables |
|---|---|---|
| `agency.txt` | Operator details | `agency_id` |
| `routes.txt` | Route IDs, names and categories where supplied | `route_id`, `agency_id` |
| `trips.txt` | Trips, directions and service IDs | `trip_id`, `route_id`, `service_id` |
| `stops.txt` | Stop names and coordinates | `stop_id` |
| `stop_times.txt` | Scheduled arrival and departure times in stop order | `trip_id`, `stop_id`, `stop_sequence` |
| `calendar.txt` | Days of the week and dates when a service runs | `service_id` |
| `calendar_dates.txt` | Date-specific service additions or removals, where supplied | `service_id`, `date` |

## Operations export

Reference file: `final_transit_master_combined.csv`. Each row represents a scheduled stop record in the original export. Consecutive stops are ordered within a trip using `stop_sequence`.

| Column | Meaning |
|---|---|
| `Route_id`, `Route_long_name` | Source route identifier and descriptive name |
| `Transport_type` | Mode or operator label used for reporting |
| `Trip_id`, `Stop_id` | Source identifiers for the trip and current stop |
| `Arrival_time`, `Departure_time` | Scheduled times at the current stop |
| `Stop_name`, `Stop_lat`, `Stop_lon` | Current stop name, latitude and longitude |
| `Stop_search` | Search label for the current stop |
| `NextStopName`, `Next_Stop_Lat`, `Next_Stop_Lon` | Name and coordinates of the next stop within the trip |
| `Distance_km` | Haversine distance between consecutive stop coordinates, in kilometres |
| `Dwell_Time_mins` | Scheduled departure minus scheduled arrival at the current stop, in minutes |
| `Travel_Time_Next_mins` | Scheduled arrival at the next stop minus scheduled departure from the current stop, in minutes |
| `Average_Speed_kmh` | Estimated speed between consecutive stops using their distance and scheduled travel time |
| `Service_Days` | Service-day information where available |
| `Peak_Hour_Flag`, `Time_of_Day` | Time-band labels. The original export uses `Time_of_Day` for KTM and `Peak_Hour_Flag` for the other modes. |

The distance is a straight-line estimate between stops. Schedule-derived times and speeds describe planned service. For cross-mode time-band comparisons, use the populated field for each mode and keep unknown periods visible as a separate category.

## Sentiment export

Reference file: `combined_transit_reviews.csv`. Each row represents a review record after joining the review export to station overview metadata on `place_id`.

| Column | Meaning |
|---|---|
| `place_id`, `review_id` | Source identifiers for the place and review |
| `rating`, `average_rating` | Individual review star rating and station-level average rating from the overview export |
| `review_text`, `review_translated_text` | Original text and translated text when available |
| `published_at_date` | Review publication date |
| `name`, `main_category`, `categories`, `address` | Place name, categories and address from the station overview |
| `transport_type` | Transit mode assigned during consolidation |
| `sentiment_score` | VADER compound score on a −1 to +1 scale |
| `sentiment_category` | Positive at or above 0.05, Negative at or below −0.05, and Neutral in between |
| `sentiment_rating_scaled` | Compound score mapped to a 1–5 scale using `(sentiment_score + 1) * 2 + 1` |

The scoring workflow prefers translated English text and falls back to the original text. In the original export, records with neither text field received a compound score of zero and were labeled Neutral. The scaled sentiment score comes from text analysis. `rating` records the stars selected by the reviewer.
