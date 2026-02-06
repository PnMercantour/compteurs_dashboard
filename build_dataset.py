import pandas as pd
import glob
import os
import shutil
import sys
import json
import re
import argparse

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_loader import DataManager

def build_dataset(source_path=None):
    """
    Reads all CSVs, processes them using DataManager logic, and forces cache regeneration (Parquet).
    This script is useful for batch processing or updating data manually.
    """
    print(f"--- Début de la conversion ETL (Mode Multi-Sites) ---")
    
    # --- STEP 0 : Bootstrap Configuration ---
    # Ensure local 'data' folder exists
    local_data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(local_data_dir, exist_ok=True)
    
    if source_path:
        print(f"Source dossier personnalisée : {source_path}")
        # Copy sites.json if present in source
        src_sites = os.path.join(source_path, "sites.json")
        tgt_sites = os.path.join(local_data_dir, "sites.json")
        
        if os.path.exists(src_sites):
             print(f"Importation de sites.json depuis {source_path}...")
             shutil.copy2(src_sites, tgt_sites)
        else:
             print(f"Note: Pas de sites.json dans {source_path}, utilisation de la config locale existante si présente.")

    dm = DataManager()
    sites = dm.get_sites()
    
    if not sites:
        print("Erreur: Aucune configuration de site trouvée. Veuillez fournir un dossier source contenant sites.json.")
        return

    # Delete existing store to force clean build in the target Cache Directory
    # Note: Cache is always stored in ./data/parquet_store regardless of source
    store_path = os.path.join(local_data_dir, "parquet_store")
    
    # We don't necessarily want to wipe everything if we are just updating one site from a folder, 
    # but for consistent full build, let's keep it clean or make it optional.
    # For now, let's just ensure we regenerate what we process.

    if source_path:
        print(f"Source dossier personnalisée : {source_path}")

    for site in sites:
        site_id = site['id']
        site_name = site['name']
        print(f"\n--- Traitement du site : {site_name} (ID: {site_id}) ---")
        
        # We manually trigger cache generation by accessing the data
        if site_id in dm._data_cache:
            del dm._data_cache[site_id]
            
        # Calling get_data will save to Parquet automatically if data is found
        # We pass csv_source_path which makes DataManager skip reading existing parquet and look in the source.
        
        df = dm.get_data(site_id, csv_source_path=source_path)
        
        if not df.empty:
            # Note: get_data automatically saves to parquet inside (see DataManager logic)
            print(f" Succès : {len(df)} enregistrements traités et sauvegardés dans {site_id}.parquet")
        else:
            print(f" Avertissement : Aucune donnée trouvée pour {site_id}")

    print("\n--- Terminé avec succès ! ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génération du dataset Parquet pour le Dashboard.")
    parser.add_argument("--source", "-s", type=str, help="Chemin vers le dossier contenant les dossiers des sites (ex: C:/Data)")
    args = parser.parse_args()
    
    build_dataset(source_path=args.source)
