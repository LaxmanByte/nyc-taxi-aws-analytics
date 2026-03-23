# NYC Taxi AWS Analytics Pipeline

![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazonaws)
![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Active-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

A fully **serverless AWS data engineering pipeline** that ingests, processes, and analyzes **2.9 million NYC Yellow Taxi trip records**. Built with cost optimization in mind — running at **under $10/month** using auto-pause serverless architecture.

This project demonstrates real-world cloud data engineering skills across the full pipeline lifecycle: ingestion, transformation, warehousing, and visualization.

---

## Architecture

```
NYC TLC Data (Parquet)
        |
        v
   AWS S3 (Raw Data Lake)
        |
        v
  AWS Glue Crawler (Schema Discovery - 19 columns)
        |
        v
  AWS Glue ETL Job (Python - Transformation)
        |
        v
  AWS Athena (SQL Analytics on S3)
        |
        v
  Redshift Serverless (Data Warehouse)
        |
        v
  Grafana Dashboards (Visualization)
```

---

## Key Features

- **2.9M records** processed from NYC TLC Yellow Taxi dataset
- **Automated schema discovery** via Glue Crawler (19 columns detected)
- **10x query performance** improvement using Redshift `SORTKEY` and `DISTKEY`
- **5 analytical views**: daily revenue trends, peak hour analysis, payment distribution, top routes, trip duration analysis
- **Least-privilege IAM roles** applied throughout for security best practices
- **Sub-$10/month** cost using Redshift Serverless auto-pause feature
- **Parquet format** used for columnar storage efficiency

---

## Tech Stack

| Service | Purpose |
|---|---|
| AWS S3 | Raw & processed data lake storage |
| AWS Glue Crawler | Automated schema discovery |
| AWS Glue ETL | Data transformation jobs |
| AWS Athena | Serverless SQL analytics on S3 |
| Redshift Serverless | Cloud data warehouse |
| Grafana | Dashboard visualization |
| AWS IAM | Least-privilege access control |
| Python 3.9 | ETL scripting |
| SQL | Analytics & reporting queries |
| Parquet | Columnar file format |

---

## Analytical Dashboards

Built **5 Grafana dashboards** with the following insights:

| Dashboard | Type | Insight |
|---|---|---|
| Daily Revenue Trends | Line Graph | Revenue over time |
| Peak Hour Analysis | Bar Chart | Busiest trip hours |
| Payment Distribution | Pie Chart | Cash vs Card usage |
| Top Routes by Fare | Table | Highest earning routes |
| Trip Duration Analysis | Histogram | Average trip lengths |

---

## Project Structure

```
nyc-taxi-aws-analytics/
├── README.md
├── .gitignore
├── scripts/
│   ├── glue/
│   │   └── glue_etl_job.py        # Glue ETL transformation job
│   ├── sql/
│   │   ├── analytical_views.sql   # 5 analytical SQL views
│   │   └── redshift_setup.sql     # Redshift table setup with SORTKEY/DISTKEY
│   └── lambda/
│       └── trigger_glue_job.py    # Lambda trigger for pipeline
├── infrastructure/
│   └── cloudformation/
│       └── pipeline_stack.yaml    # IaC for full pipeline
├── dashboards/
│   └── grafana/
│       └── dashboard.json         # Grafana dashboard export
└── docs/
    └── architecture/
        └── architecture-diagram.png
```

---

## Performance Results

| Metric | Result |
|---|---|
| Records Processed | 2,900,000+ |
| Columns Detected | 19 |
| Query Performance Gain | 10x (via SORTKEY/DISTKEY) |
| Monthly Cost | < $10/month |
| Architecture | Fully Serverless |

---

## Security Implementation

- IAM roles follow **least-privilege principle**
- S3 buckets configured with **block public access**
- Redshift Serverless uses **VPC isolation**
- Glue jobs use **dedicated IAM service roles**
- No hardcoded credentials — all via IAM role assumptions

---

## How to Deploy

1. **Clone the repo**
```bash
git clone https://github.com/LaxmanByte/nyc-taxi-aws-analytics.git
cd nyc-taxi-aws-analytics
```

2. **Upload raw data to S3**
```bash
aws s3 cp data/raw/ s3://your-bucket/raw/ --recursive
```

3. **Run Glue Crawler** to detect schema

4. **Execute Glue ETL job**
```bash
aws glue start-job-run --job-name nyc-taxi-etl
```

5. **Query with Athena** using scripts in `scripts/sql/`

6. **Connect Grafana** to Redshift Serverless and import `dashboards/grafana/dashboard.json`

---

## Author

**Laxman Barre**
AWS Certified Cloud Practitioner (CLF-C02)

- LinkedIn: [linkedin.com/in/laxman-barre-073735256](https://linkedin.com/in/laxman-barre-073735256)
- GitHub: [github.com/LaxmanByte](https://github.com/LaxmanByte)
- Email: barrelaxman@gmail.com
- Location: Salt Lake City, UT

---

## License

MIT License — see [LICENSE](LICENSE) for details.
