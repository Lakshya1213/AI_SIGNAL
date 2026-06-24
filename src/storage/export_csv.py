import os
import pandas as pd
from typing import List
import sys
# Add project root to sys.path to allow running/importing directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.schemas.startup_schema import StartupEntity
from src.schemas.product_schema import ProductEntity
from src.schemas.paper_schema import PaperEntity
from src.schemas.job_schema import JobEntity
from src.schemas.news_schema import NewsEntity
from src.utils.logger import Logger

def export_to_excel(
    startups: List[StartupEntity],
    products: List[ProductEntity],
    papers: List[PaperEntity],
    jobs: List[JobEntity],
    news: List[NewsEntity],
    mapping_log: List[dict],
    output_path: str = "outputs/graphone_data.xlsx"
):
    """
    Export all pipeline outputs into a single Excel file with 6 tabs.
    """
    Logger.info(f"Preparing data export to {output_path}...")
    
    # Ensure directory exists
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    # 1. Startups Sheet
    startup_dicts = []
    for s in startups:
        d = s.to_dict()
        startup_dicts.append({
            "schemaVersion": d["schemaVersion"],
            "recordType": d["recordType"],
            "source.name": d["source"]["name"],
            "source.url": d["source"]["url"],
            "content.entityName": d["content"]["entityName"],
            "content.data.employeeCount": d["content"]["data"]["employeeCount"],
            "collectedAt": d["collectedAt"]
        })
    df_startups = pd.DataFrame(startup_dicts)

    # 2. Products Sheet
    product_dicts = []
    for p in products:
        d = p.to_dict()
        product_dicts.append({
            "schemaVersion": d["schemaVersion"],
            "recordType": d["recordType"],
            "source.name": d["source"]["name"],
            "source.url": d["source"]["url"],
            "content.startupName": d["content"]["startupName"],
            "content.productName": d["content"].get("productName", ""),
            "content.pricingModel": d["content"]["pricingModel"],
            "collectedAt": d["collectedAt"]
        })
    df_products = pd.DataFrame(product_dicts)

    # 3. Research Papers Sheet
    paper_dicts = []
    for pa in papers:
        d = pa.to_dict()
        paper_dicts.append({
            "schemaVersion": d["schemaVersion"],
            "recordType": d["recordType"],
            "content.title": d["content"]["title"],
            "content.authors": ", ".join(d["content"]["authors"]) if d["content"]["authors"] else "",
            "content.paper_url": d["content"]["paper_url"],
            "content.github_url": d["content"]["github_url"],
            "content.github_stars": d["content"]["github_stars"],
            "content.published_date": d["content"]["published_date"],
            "collectedAt": d["collectedAt"]
        })
    df_papers = pd.DataFrame(paper_dicts)

    # 4. Jobs Sheet
    job_dicts = []
    for j in jobs:
        d = j.to_dict()
        job_dicts.append({
            "schemaVersion": d["schemaVersion"],
            "recordType": d["recordType"],
            "content.company": d["content"]["company"],
            "content.date": d["content"]["date"],
            "content.is_remote": d["content"]["is_remote"],
            "content.role_family": d["content"]["role_family"],
            "collectedAt": d["collectedAt"]
        })
    df_jobs = pd.DataFrame(job_dicts)

    # 5. News Sheet
    news_dicts = []
    for n in news:
        d = n.to_dict()
        news_dicts.append({
            "schemaVersion": d["schemaVersion"],
            "recordType": d["recordType"],
            "source.name": d["source"]["name"],
            "source.url": d["source"]["url"],
            "content.title": d["content"]["title"],
            "content.published_date": d["content"]["published_date"],
            "content.fullText": d["content"]["fullText"],
            "collectedAt": d["collectedAt"]
        })
    df_news = pd.DataFrame(news_dicts)

    # 6. Entity Mapping Log Sheet
    df_mapping = pd.DataFrame(mapping_log) if mapping_log else pd.DataFrame(columns=["raw_name", "canonical_name", "similarity_score", "matched_seed"])

    # Define primary and alternative save paths for redundancy
    save_paths = [
        output_path,
        "data/exports/graphone_data.xlsx"
    ]

    # Write to Excel in both paths
    for path in save_paths:
        try:
            dir_name_path = os.path.dirname(path)
            if dir_name_path:
                os.makedirs(dir_name_path, exist_ok=True)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df_startups.to_excel(writer, sheet_name="Startups", index=False)
                df_products.to_excel(writer, sheet_name="Products", index=False)
                df_papers.to_excel(writer, sheet_name="Research Papers", index=False)
                df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
                df_news.to_excel(writer, sheet_name="News", index=False)
                df_mapping.to_excel(writer, sheet_name="Entity Mapping Log", index=False)
            Logger.success(f"Excel export completed. File saved at {path}")
        except Exception as e:
            Logger.error(f"Failed to export Excel file to {path}: {e}")

    # Write individual CSV files to outputs/csv/ and data/exports/csv/
    csv_dirs = [
        os.path.join(os.path.dirname(output_path), "csv"),
        "data/exports/csv"
    ]
    for csv_dir in csv_dirs:
        try:
            os.makedirs(csv_dir, exist_ok=True)
            df_startups.to_csv(os.path.join(csv_dir, "startups.csv"), index=False)
            df_products.to_csv(os.path.join(csv_dir, "products.csv"), index=False)
            df_papers.to_csv(os.path.join(csv_dir, "papers.csv"), index=False)
            df_jobs.to_csv(os.path.join(csv_dir, "jobs.csv"), index=False)
            df_news.to_csv(os.path.join(csv_dir, "news.csv"), index=False)
            df_mapping.to_csv(os.path.join(csv_dir, "entity_mapping_log.csv"), index=False)
            Logger.success(f"CSV exports completed. Files saved in {csv_dir}/")
        except Exception as e:
            Logger.error(f"Failed to export CSV files to {csv_dir}: {e}")
