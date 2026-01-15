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
from data_loader import process_data

# Helper for column identification (duplicated from data_loader logic to avoid circular deps if refactored poorly, 
# but here we rely on data_loader helper if possible. 
# However, data_loader._identify_columns is private. Let's make it robust.)
# Actually, we can import it if we are careful.
# But for safety in this standalone script:
def _identify_columns(columns):
    found_cols = {}
    for col in columns:
        c_lower = col.lower()
        if 'horodate' in c_lower and 'generated' in c_lower:
            found_cols[col] = 'Datetime'
        elif 'lane' in c_lower and 'rank' not in c_lower and 'col' in c_lower:
            found_cols[col] = 'Lane'
        elif 'direction_1_2' in c_lower:
            found_cols[col] = 'Direction'
        elif 'categorysterela_label' in c_lower:
            found_cols[col] = 'Category'
        elif 'category1' in c_lower:
            found_cols[col] = 'Category_SIREDO'
        elif c_lower.startswith('speed') and 'average' not in c_lower and 'validity' not in c_lower and 'delta' not in c_lower:
            found_cols[col] = 'Speed'
    return found_cols

def extract_metadata_from_csv(filepath):
    """
    Extracts site name and direction labels from the CSV header.
    Expects header like:
    ...;lane (Col de Restefond, Route du Col de Restefond);direction_1_2 (1: vers Col de la Bonette) (2: vers Jaussiers);...
    """
    metadata = {
        "site_name": "Site Inconnu",
        "direction_1": "Sens 1",
        "direction_2": "Sens 2"
    }
    
    try:
        with open(filepath, 'r', encoding='latin1') as f:
            header = f.readline()
            
        # Extract Site Name from 'lane (...)'
        lane_match = re.search(r'lane \(([^)]+)\)', header, re.IGNORECASE)
        if lane_match:
            content = lane_match.group(1)
            # Usually "Code, Name". We take the second part if comma exists, else the whole thing
            if ',' in content:
                metadata["site_name"] = content.split(',')[1].strip()
            else:
                metadata["site_name"] = content.strip()
                
        # Extract Directions
        dir_match = re.search(r'direction_1_2 \((.*?)\)\s*\((.*?)\)', header, re.IGNORECASE)
        if dir_match:
             p1 = dir_match.group(1).replace('1:', '').strip()
             p2 = dir_match.group(2).replace('2:', '').strip()
             metadata["direction_1"] = p1
             metadata["direction_2"] = p2
             
    except Exception as e:
        print(f"Warning: Could not extract metadata from {filepath}: {e}")
        
    return metadata

def build_dataset(source_path="..", output_path="../data/parquet_store"):
    """
    Reads all CSVs, processes them, and saves them as a Partitioned Parquet Dataset.
    Structure: /data/parquet_store/year=2023/data.parquet
    """
    print(f"--- Début de la conversion ETL (Mode Générique) ---")
    
    # 1. Load Raw Data
    print("Recherche des fichiers CSV...")
    # Generic pattern: Look for any CSV containing 'WebTraffic'
    pattern = os.path.join(source_path, "*.csv")
    candidates = glob.glob(pattern)
    files = [f for f in candidates if "WebTraffic" in os.path.basename(f)]
    
    if not files:
        print("Aucun fichier 'WebTraffic' CSV trouvé.")
        return

    # Clean output directory
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path, exist_ok=True)
    
    # 2. Extract Metadata from the first file
    metadata = extract_metadata_from_csv(files[0])
    print(f"Métadonnées détectées : {metadata}")
    
    # Save metadata in the parent directory of the parquet store to avoid polluting the dataset
    meta_dir = os.path.dirname(output_path)
    os.makedirs(meta_dir, exist_ok=True)
    with open(os.path.join(meta_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    # 3. Process and Save
    all_dfs = []
    
    for file in files:
        try:
            print(f"Traitement de {os.path.basename(file)}...")
            df = pd.read_csv(file, sep=';', encoding='latin1', on_bad_lines='skip', low_memory=False)
            
            # Map Columns
            found_cols = _identify_columns(df.columns)
            selected_data = {new: df[old] for old, new in found_cols.items()}
            
            if 'Datetime' not in selected_data:
                continue
                
            new_df = pd.DataFrame(selected_data)
            
            # Types
            new_df['Datetime'] = pd.to_datetime(new_df['Datetime'], format='mixed', utc=True)
            if 'Speed' in new_df.columns:
                 if new_df['Speed'].dtype == 'object':
                    new_df['Speed'] = new_df['Speed'].str.replace(',', '.', regex=False)
                 new_df['Speed'] = pd.to_numeric(new_df['Speed'], errors='coerce')

            # Basic Temporal Features needed for Partitioning
            new_df['Year'] = new_df['Datetime'].dt.year
            
            # Rebuild full features
            new_df['Date'] = new_df['Datetime'].dt.date
            new_df['Hour'] = new_df['Datetime'].dt.hour
            new_df['Month'] = new_df['Datetime'].dt.month
            new_df['Weekday'] = new_df['Datetime'].dt.day_name()
            
            # Apply Business Logic
            final_df = process_data(new_df)
            
            all_dfs.append(final_df)
            
        except Exception as e:
            print(f"Erreur sur {file}: {e}")

    if not all_dfs:
        print("Aucune donnée valide extraite.")
        return

    full_df = pd.concat(all_dfs, ignore_index=True)
    
    print(f"Sauvegarde en Parquet partitionné par Année dans {output_path}...")
    full_df.to_parquet(output_path, partition_cols=['Year'], engine='pyarrow', compression='snappy')
    
    print("--- Terminé avec succès ! ---")

if __name__ == "__main__":
    
    # Calculate paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_root = os.path.abspath(os.path.join(script_dir))
    default_store = os.path.join(default_root, "data", "parquet_store")

    # Argument Parser
    parser = argparse.ArgumentParser(description="Convertit les fichiers CSV de trafic en un dataset Parquet optimisé.")
    parser.add_argument("--source", "-s", type=str, default=default_root, 
                        help=f"Dossier contenant les fichiers CSV (Défaut: {default_root})")
    parser.add_argument("--output", "-o", type=str, default=default_store,
                        help=f"Dossier de sortie pour le store Parquet (Défaut: {default_store})")
    
    args = parser.parse_args()
    
    # Validation
    if not os.path.isdir(args.source):
        print(f"Erreur: Le dossier source '{args.source}' n'existe pas.")
        sys.exit(1)
        
    build_dataset(source_path=args.source, output_path=args.output)
