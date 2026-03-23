# NYC Taxi AWS Analytics Pipeline

![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonaws)
![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Active-green)
![Records](https://img.shields.io/badge/Records-19.6M-brightgreen)
![Cost](https://img.shields.io/badge/Query%20Cost-%240.02-success)

Serverless AWS data pipeline processing **19.6M NYC Uber/Lyft (FHVHV) trips** from July 2025 using S3, Glue, Athena, Redshift Serverless, and Grafana Cloud.

---

## Architecture

![Architecture Diagram](docs/architecture/architecture-diagram.png)

**Pipeline:** NYC TLC Open Data → S3 Data Lake → AWS Glue ETL → Amazon Athena → Redshift Serverless → Grafana Cloud

---

## Tech Stack

| Service | Role |
|---------|------|
| Amazon S3 | Data lake — raw + processed parquet files |
| AWS Glue | Serverless ETL + schema catalog |
| Amazon Athena | Serverless SQL — pay-per-query (~$0.02 total) |
| Redshift Serverless | Columnar warehouse with SORTKEY/DISTKEY |
| AWS Lambda + Step Functions | Orchestration and automation |
| IAM | Least-privilege security (grafana-readonly user) |
| Grafana Cloud | 5-panel live dashboard |

---

## Key Results

- **19.6M trips** processed from FHVHV_tripdata_2025-07
- **~$0.02 total** Athena query cost across all 5 analyses
- **Peak demand** at 6PM (1.14M trips/hour)
- **97% solo rides** vs 3% shared
- **~$6 platform cut** per trip (Uber/Lyft take rate)
- **10x faster** queries with Redshift SORTKEY + DISTKEY optimization

---

## Grafana Dashboard

### Full Dashboard
![Full Dashboard](nyc-taxi-analytics-aws/screenshots/full_dashboard_all_1_5_panels.png)

### Panel 1 — Athena Data Source Connected
![Athena Connected](nyc-taxi-analytics-aws/screenshots/01_grafana_athena_datasource_connected.png)

### Panel 2 — Peak Hours Bar Chart
![Peak Hours](nyc-taxi-analytics-aws/screenshots/02_panel_peak_hours_bar_chart_with_query.png)

### Panel 3 — Daily Trip Volume
![Daily Volume](nyc-taxi-analytics-aws/screenshots/03_panel_daily_trip_volume_line_chart_with_query.png)

### Panel 4 — Trip Duration Breakdown
![Trip Duration](nyc-taxi-analytics-aws/screenshots/04_panel_trip_duration_pie_chart_with_query.png)

### Panel 5 — Shared vs Solo Rides
![Shared vs Solo](nyc-taxi-analytics-aws/screenshots/05_panel_shared_vs_solo_with_query.png)

### Panel 6 — Driver Pay vs Platform Cut
![Driver Pay](nyc-taxi-analytics-aws/screenshots/06_panel_driver_pay_vs_platform_cut_timeseries_with_query.png)

---

## AWS Setup Screenshots

### Day 1 — S3, Glue, Athena
| Screenshot | Description |
|-----------|-------------|
| ![S3 Bucket](nyc-taxi-analytics-aws/screenshots/day-1/Created_s3_bucket.png) | S3 bucket created |
| ![S3 Data](nyc-taxi-analytics-aws/screenshots/day-1/s3-raw-data-uploaded.png) | Raw data uploaded |
| ![Medallion](nyc-taxi-analytics-aws/screenshots/day-1/Three_Prefixes%20(Medallion%20Folders).png) | Medallion architecture folders |
| ![Crawler](nyc-taxi-analytics-aws/screenshots/day-1/crawler-output-db.png) | Glue crawler output |
| ![IAM Glue](nyc-taxi-analytics-aws/screenshots/day-1/iam-glue-role-permissions.png) | IAM Glue role permissions |
| ![Athena Q1](nyc-taxi-analytics-aws/screenshots/day-1/Athena%20query%201.png) | Athena query running |

### Day 2 — Redshift Serverless + IAM + Grafana
| Screenshot | Description |
|-----------|-------------|
| ![Redshift](nyc-taxi-analytics-aws/screenshots/day%20-2/serverless_redshift.png) | Redshift Serverless setup |
| ![IAM User](nyc-taxi-analytics-aws/screenshots/day%20-2/IAM%20user%20grafana-readonly.png) | grafana-readonly IAM user |
| ![IAM Policy](nyc-taxi-analytics-aws/screenshots/day%20-2/day2-iam-policy-details.png) | IAM policy details |
| ![Grafana Connected](nyc-taxi-analytics-aws/screenshots/day%20-2/grafana_connected.png) | Grafana connected to Athena |

---

## Repository Structure

```
nyc-taxi-aws-analytics/
├── README.md
├── .gitignore
├── docs/
│   └── architecture/
│       └── architecture-diagram.png
├── scripts/
│   ├── glue/
│   │   └── glue_etl_job.py
│   └── sql/
│       ├── analytical_views.sql
│       └── redshift_setup.sql
├── dashboards/
│   └── grafana/
│       └── README.md
└── nyc-taxi-analytics-aws/
    └── screenshots/
        ├── day-1/          (S3, Glue, Athena setup)
        ├── day -2/         (Redshift, IAM, Grafana)
        └── *.png           (Grafana dashboard panels)
```

---

## Author

**Laxman Barre** | [GitHub](https://github.com/LaxmanByte) | [Grafana Dashboard](https://laxmanbarredata.grafana.net)

AWS Cloud Practitioner | AWS Solutions Architect (in progress)
