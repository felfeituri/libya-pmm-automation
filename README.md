# Libya PMM Automation Pipeline

**Author:** Fadwa Elfeituri ([\@felfeituri](https://github.com/felfeituri))

Automation system for WFP Libya's monthly Price Market Monitoring (PMM) workflow. Transforms a multi-day manual process into a streamlined pipeline that handles data collection progress monitoring, data extraction, quality assurance, MEB calculations, database management, output generation, and report preparation.

> **Note:** This system is developed specifically for **WFP Libya's** Price Market Monitoring workflow. The data structure, MEB basket composition, administrative boundaries, and output formats are configured for the Libya Country Office. Other WFP country offices may have different workflows and requirements. If you are interested in adapting this pipeline for your country office, please reach out via [GitHub](https://github.com/felfeituri) or [email] (mailto::fadwa.feituri@gmail.com) to discuss configuration for your use case.

## Key Features

-   **87% time reduction** (days → hours per month)
-   **Automated MEB calculations** at municipality, regional, and national levels
-   **Dual environment support** (Docker containers + local execution)
-   **Historical data tracking** (24+ months stored in PostgreSQL)
-   **Professional outputs** (14 Excel files, 12 SVG charts, interactive HTML map)
-   **DataBridges integration** for WFP global systems

## Technology Stack

-   **Python 3.11** (pandas, SQLAlchemy, openpyxl, matplotlib, seaborn, plotly)
-   **Docker & Docker Compose** (containerized workflow)
-   **PostgreSQL 15** (historical data storage)
-   **Jupyter Notebooks** (interactive QA/QC analysis)

## Pipeline Overview

The monthly workflow consists of **7 phases**:

| Phase | Script | Environment | Description |
|----------------|----------------|--------------------|--------------------|
| 1 | `01_run_data_export.py` | Local | Export raw data from WFP MoDa API |
| 2 | `02_run_qaqc.py` | Local | QA/QC analysis with Jupyter notebooks |
| 3 | `03_run_preprocessing.py` | Docker | MEB calculations & exchange rate processing |
| 4 | `04_run_database_loading.py` | Docker | Load processed data into PostgreSQL |
| 5 | `05_run_data_outputs.py` | Docker | Generate Excel outputs (14 files) |
| 6 | `06_run_visualizations.py` | Docker | Generate charts & interactive map (13 files) |
| 7 | `07_run_report.py` | Local | Prepare Word document report template |

> **Shortcut:** Phases 3-6 can be run together with `99_run_step03_to_step06.py`

## Project Structure

```         
├── config.py                  # Configuration (uses environment variables)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build configuration
├── docker-compose.yml         # Docker services (PostgreSQL, pgAdmin, app)
├── .env.example               # Template for environment variables
│
├── 01_run_data_export.py      # Phase 1: MoDa data export
├── 02_run_qaqc.py             # Phase 2: QA/QC analysis
├── 03_run_preprocessing.py    # Phase 3: MEB calculations
├── 04_run_database_loading.py # Phase 4: Database loading
├── 05_run_data_outputs.py     # Phase 5: Excel outputs
├── 06_run_visualizations.py   # Phase 6: Charts & map
├── 07_run_report.py           # Phase 7: Report template
├── 99_run_step03_to_step06.py # Combined phases 3-6
│
├── scripts/                   # Core pipeline modules
│   ├── 00_Setup/              # Database setup & backup/restore
│   ├── 01_Data_Export/        # MoDa API integration
│   ├── 02_QAQC/               # Quality assurance checks
│   ├── 03_Preprocessing/      # MEB & exchange rate processing
│   ├── 04_Database_Loading/   # PostgreSQL data loading
│   ├── 05_Data_Outputs/       # Excel file generation
│   ├── 06_Visualizations/     # Chart & map generation
│   └── 07_Report/             # Report template preparation
│
├── inputs/                    # Input data files
│   ├── Currency Exchange Rates - The Central Bank of Libya.xlsx
│   ├── food_price_indices_data.csv
│   ├── libya_boundaries.geojson
│   ├── Master_Exchange_Rate.xlsx
│   └── PMM_QAQC_Template.ipynb
│
└── outputs/                   # Generated output files
```

## Setup

### Prerequisites

-   **Docker Desktop 4.0+** ([download](https://www.docker.com/products/docker-desktop))
-   **Python 3.11+** ([download](https://www.python.org/downloads/))
-   **OneDrive** sync with SharePoint team drive
-   **WFP MoDa** account with API token

### 1. Clone the Repository

``` bash
git clone https://github.com/felfeituri/libya-pmm-automation.git
cd libya-pmm-automation
```

### 2. Configure Environment Variables

``` bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

``` env
# Database
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5433

# pgAdmin
PGADMIN_DEFAULT_EMAIL=your_email
PGADMIN_DEFAULT_PASSWORD=your_pgadmin_password
```

### 3. Create OneDrive Symlinks

The pipeline needs access to three OneDrive-synced folders. Create symlinks:

``` bash
# Replace paths with your actual OneDrive sync locations
ln -s "/path/to/your/Monthly Reports" ~/onedrive_pmm
ln -s "/path/to/your/DataBridges" ~/databridges_pmm
ln -s "/path/to/your/Master Data" ~/masterdata_pmm
```

### 4. Configure MoDa API Token

Store your MoDa API token in a secure location:

``` bash
mkdir -p ~/path/to/secure/location
echo 'MODA_TOKEN=your_moda_token_here' > ~/path/to/secure/location/.env
```

Then update the `MODA_ENV_PATH` in `config.py` to point to this file.

### 5. Install Python Dependencies

``` bash
pip install -r requirements.txt
```

### 6. Set Up Docker

> **Note:** The `docker-compose.yml` uses container and volume names specific to Libya (e.g., `libya_pmm_db`, `libya_pmm_database`). If adapting for another country office, update these names in `docker-compose.yml` before proceeding.

``` bash
# Create persistent volumes (names must match docker-compose.yml)
docker volume create <your_database_volume_name>
docker volume create <your_pgadmin_volume_name>

# Start containers
docker-compose up -d

# Verify containers are running
docker-compose ps
```

### 7. Initialize Database

**Option A: Restore from backup** (if you have one)

``` bash
docker exec -it <app_container> bash scripts/00_Setup/restore_database.sh backups/your_backup.sql
```

**Option B: Create from scratch**

``` bash
docker exec -it <app_container> python scripts/00_Setup/create_database_schema.py
```

### 8. Fonts

The visualization scripts use the **Aptos** font family for charts. This is a Microsoft proprietary font and cannot be redistributed. You must provide your own:

1.  Locate the Aptos font files from your Microsoft Office installation
2.  Copy them to the `fonts/` directory in the project root

## Monthly Workflow Usage

### Prerequisites (Before Each Month)

1.  **Update CBL exchange rates** — download from [Central Bank of Libya](https://cbl.gov.ly/en/currency-exchange-rates/) and replace `inputs/Currency Exchange Rates - The Central Bank of Libya.xlsx`
2.  **Update FAO Food Price Index** — download from [FAO](https://www.fao.org/worldfoodsituation/foodpricesindex/en/) and replace `inputs/food_price_indices_data.csv`
3.  **Get MoDa Form ID** — find the 6-digit form ID from the current month's survey on [MoDa](https://moda.wfp.org)
4.  **Verify OneDrive sync** is active

### Run the Pipeline

``` bash
# Phase 1: Export data from MoDa (local)
python 01_run_data_export.py <YEAR> <MONTH> <FORM_ID>

# Phase 2: QA/QC analysis (local)
python 02_run_qaqc.py <YEAR> <MONTH>

# ⚠️ Review QA/QC results before proceeding!

# Phases 3-6: Processing, loading, outputs, visualizations (Docker)
docker exec -it <app_container> python 99_run_step03_to_step06.py <YEAR> <MONTH>

# ⚠️ Manual step: Fill parallel market exchange rates when prompted

# Phase 7: Report template (local)
python 07_run_report.py <YEAR> <MONTH>

# ⚠️ Manual step: Edit the Word document report
```

**Example for December 2025:**

``` bash
python 01_run_data_export.py 2025 12 340405
python 02_run_qaqc.py 2025 12
docker exec -it <app_container> python 99_run_step03_to_step06.py 2025 12
python 07_run_report.py 2025 12
```

## Database Management

### Backup

``` bash
docker exec -it <app_container> bash scripts/00_Setup/backup_database.sh
```

### Restore

``` bash
docker exec -it <app_container> bash scripts/00_Setup/restore_database.sh backups/your_backup.sql
```

### Load Historical Data

``` bash
# Load all available months
docker exec -it <app_container> python scripts/04_Database_Loading/load_meb_to_db.py --all

# Load a specific month
docker exec -it <app_container> python scripts/04_Database_Loading/load_meb_to_db.py 2025 12

# Force reload (overwrites existing)
docker exec -it <app_container> python scripts/04_Database_Loading/load_meb_to_db.py --all --force
```

### pgAdmin (Optional)

Access the database UI at <http://localhost:5050> using the credentials from your `.env` file.

## Pipeline Outputs

Each monthly run generates:

| Category | Files | Format | Location |
|-------------------|-----------------|-----------------|-------------------|
| Monthly tables | 3 files (MEB comparison, commodity prices, geopoints) | Excel | `Monthly Reports/<year>/<month>/Tables/` |
| Master data | 3 files (historical, MoM trends, YoY trends) | Excel | `Master Data/MEB/` |
| Exchange rates | 1 file (MoM & YoY trends) | Excel | `Master Data/Exchange Rate/` |
| DataBridges | 2 files (prices + exchange rates) | Excel | `DataBridges/` |
| National charts | 3 SVGs (Full/Food/NFI MEB) | SVG | `Monthly Reports/<year>/<month>/Graphics/Charts/` |
| Regional charts | 6 SVGs (Food & NFI per region) | SVG | `Monthly Reports/<year>/<month>/Graphics/Charts/` |
| Other charts | 3 SVGs (transfer values, exchange rate, FAO index) | SVG | `Monthly Reports/<year>/<month>/Graphics/Charts/` |
| Interactive map | 1 HTML map | HTML | `Monthly Reports/<year>/<month>/Graphics/Map/` |

## Docker Services

| Service       | Port | Description                    |
|---------------|------|--------------------------------|
| PostgreSQL 15 | 5433 | Database server                |
| pgAdmin 4     | 5050 | Database management UI         |
| App           | —    | Pipeline execution environment |

> Container and volume names are defined in `docker-compose.yml` and should be configured for your deployment.

## Troubleshooting

### Docker containers not starting

``` bash
docker-compose down
docker-compose up -d
docker-compose logs
```

### Database connection failed

-   Ensure Docker containers are running: `docker-compose ps`
-   Check `.env` has correct credentials
-   Wait 30 seconds after starting containers for PostgreSQL to initialize

### MoDa export fails

-   Verify your API token is valid
-   Check the Form ID (6 digits from the survey URL)
-   Ensure internet connection is active

### Missing fonts in charts

-   Copy Aptos font files to the `fonts/` directory
-   The fonts are proprietary and must be obtained from a Microsoft Office installation

## License

Copyright (c) 2025 Fadwa Elfeituri. All rights reserved.

This project is the original work of **Fadwa Elfeituri**. Permission must be obtained from the author before using, modifying, or distributing this code. If you use this project or any part of it, proper credit and citation are required.

For permission requests or adaptation inquiries, please contact via [GitHub](https://github.com/felfeituri).
