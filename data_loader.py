import pandas as pd
import glob
import os
import numpy as np
import json
import re
from utils import FRENCH_DAYS, TZ

class DataManager:
    _instance = None
    _data_cache = {}
    _base_path = os.path.dirname(os.path.abspath(__file__))

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance

    def get_sites(self):
        sites_path = os.path.join(self._base_path, "data", "sites.json")
        if os.path.exists(sites_path):
            try:
                with open(sites_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"Error loading sites.json: {e}")
        return []

    def get_data(self, site_id, csv_source_path=None):
        if site_id in self._data_cache:
            return self._data_cache[site_id]
        
        sites = self.get_sites()
        site_info = next((s for s in sites if s['id'] == site_id), None)
        
        if not site_info:
            print(f"Site {site_id} not found.")
            return pd.DataFrame()

        # 1. Try Loading from Parquet (Only if csv_source_path is NOT provided to allow rebuilding)
        # Or better: Logic decides. If csv_source_path is provided, we likely want to use it? 
        # But for the app we want parquet.
        # Let's check parquet first unless valid csvs are forced.
        # Check if Parquet exists
        parquet_path = os.path.join(self._base_path, "data", "parquet_store", f"{site_id}.parquet")
        
        # If csv_source_path is provided, we ASSUME we are in build/update mode or explicit override,
        # so we skip loading from parquet to ensure we read freshness from the source path.
        if not csv_source_path and os.path.exists(parquet_path):
            try:
                print(f"Loading cached data for {site_id} from {parquet_path}...")
                df = pd.read_parquet(parquet_path)
                if not df.empty:
                    self._attach_metadata(df, site_info)
                    self._data_cache[site_id] = df
                    return df
            except Exception as e:
                print(f"Error loading parquet for {site_id}: {e}")
            
        print(f"Loading CSV data for site: {site_id}...")
        
        base_search_path = csv_source_path if csv_source_path else self._base_path
        keywords = site_info.get('keywords', [])
        files = []

        # Look in subfolder named by site_id
        site_folder = os.path.join(base_search_path, site_id)
        if os.path.isdir(site_folder):
             print(f"Found dedicated folder for {site_id}: {site_folder}")
             pattern = os.path.join(site_folder, "*.csv")
             files = glob.glob(pattern)
        
        if not files:
            print(f"No files found for site {site_id} in {base_search_path}")
            return pd.DataFrame()

        dfs = []
        for file in files:
            try:
                df = self._read_csv_robust(file)
                if not df.empty:
                    dfs.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
                
        if not dfs:
             return pd.DataFrame()
             
        full_df = pd.concat(dfs, ignore_index=True)
        processed_df = process_data(full_df)

        # Check for extracted directions (Propagate from CSVs to metadata.json)
        extracted_dirs = None
        for d in dfs:
            if 'extracted_directions' in d.attrs:
                extracted_dirs = d.attrs['extracted_directions']
                break
        
        if extracted_dirs:
            d1, d2 = extracted_dirs
            print(f"Detected directions: {d1} / {d2}")
            # Save to metadata.json
            meta_path = os.path.join(self._base_path, "data", f"metadata_{site_id}.json")
            meta_data = {
                "site_name": site_info.get('name'),
                "direction_1": d1,
                "direction_2": d2
            }
            try:
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                 print(f"Error saving metadata_{site_id}.json: {e}")
        
        # Save to Parquet
        if not processed_df.empty:
            try:
                os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
                print(f"Saving cache for {site_id} to {parquet_path}...")
                processed_df.to_parquet(parquet_path)
            except Exception as e:
                 print(f"Error saving parquet for {site_id}: {e}")
        
        # Attach metadata to DF attrs
        self._attach_metadata(processed_df, site_info)
        
        self._data_cache[site_id] = processed_df
        return processed_df

    def _attach_metadata(self, df, site_info):
        # Default directions
        d1 = 'Sens 1'
        d2 = 'Sens 2'

        # Try loading metadata.json (legacy/persistent storage)
        # TODO: Make this site-specific if needed (e.g. metadata_{site_id}.json)
        meta_path = os.path.join(self._base_path, "data", f"metadata_{site_info.get('id', 'unknown')}.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    file_meta = json.load(f)
                    # Check if checks out? Or just use it.
                    d1 = file_meta.get('direction_1', d1)
                    d2 = file_meta.get('direction_2', d2)
            except Exception as e:
                print(f"Error loading metadata_{site_info.get('id', 'unknown')}.json: {e}")

        df.attrs['metadata'] = {
            'site_name': site_info.get('name'),
            'direction_1': d1,
            'direction_2': d2,
            'latitude': site_info.get('coords', [0, 0])[0],
            'longitude': site_info.get('coords', [0, 0])[1]
        }

    def _read_csv_robust(self, file):
        # Read all columns; avoid low_memory issues
        try:
             df = pd.read_csv(file, sep=';', encoding='latin1', on_bad_lines='skip', low_memory=False)
        except:
             return pd.DataFrame()
        
        # Extract Directions from Header
        extracted_directions = None
        for col in df.columns:
            if "direction_1_2" in col.lower():
                # Expected format: ... direction_1_2 (1: vers col de la Bonette) (2: vers Jausiers)
                match = re.search(r"\(1:\s*(.*?)\)\s*\(2:\s*(.*?)\)", col)
                if match:
                    extracted_directions = match.groups()
                    break
        
        # Identify relevant columns dynamically
        found_cols = _identify_columns(df.columns)
        
        # Select and Rename
        selected_data = {
            new_name: df[orig_col] 
            for orig_col, new_name in found_cols.items()
        }
        
        if 'Datetime' not in selected_data:
             return pd.DataFrame()
             
        new_df = pd.DataFrame(selected_data)
        
        if extracted_directions:
            new_df.attrs['extracted_directions'] = extracted_directions

        # Parse Datetime with mixed format support
        new_df['Datetime'] = pd.to_datetime(new_df['Datetime'], format='mixed').dt.tz_convert(TZ)
        
        # Clean numeric columns
        if 'Speed' in new_df.columns:
            if new_df['Speed'].dtype == 'object':
                new_df['Speed'] = new_df['Speed'].str.replace(',', '.', regex=False)
            new_df['Speed'] = pd.to_numeric(new_df['Speed'], errors='coerce')
        
        # Extract Temporal Features
        new_df['Date'] = new_df['Datetime'].dt.date
        new_df['Hour'] = new_df['Datetime'].dt.hour
        new_df['Month'] = new_df['Datetime'].dt.month
        new_df['Year'] = new_df['Datetime'].dt.year
        new_df['Weekday'] = new_df['Datetime'].dt.day_name()
        
        return new_df

def _identify_columns(columns):
    """
    Helper to map CSV columns to standard names based on substrings.
    """
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

def _get_unified_category(row):
    """
    Maps raw categories to [Vélos, Motos, VL, PL, Autre].
    """
    # TODO : use sterela category number for more robust mapping if available
    cat = str(row.get('Category', '')).lower()
    siredo = row.get('Category_SIREDO')
    
    # Robust check for 'Vélo' including potential encoding artifacts (Vï¿½lo, etc)
    if any(x in cat for x in ['vélo', 'velo', 'vï¿½lo', 'vlo']):
        return 'Vélos'
    elif cat == 'moto':
        return 'Motos'
    elif siredo in [1, 12] or (cat == 'u3' and pd.isna(siredo)):
        return 'VL'
    elif siredo in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14]:
        return 'PL'
    return 'Autre'

def process_data(df):
    """
    Applies business logic: Category Unification, Day Types, Localization.
    """
    if df.empty:
        return df

    # Localize Days
    df['Weekday_FR'] = df['Weekday'].map(FRENCH_DAYS)
    
    # Unified Category
    df['UnifiedCategory'] = df.apply(_get_unified_category, axis=1)
    
    # Filter out 'Autre' immediately as requested for this dashboard
    df = df[df['UnifiedCategory'] != 'Autre'].reset_index(drop=True)
    
    # Define DayType (JO vs WE)
    # Using numpy where is faster and cleaner than apply
    df['DayType'] = np.where(df['Weekday'].isin(['Saturday', 'Sunday']), 'WE', 'JO')

    return df

# For Backward Compatibility
def load_data(base_path="."):
    print("Legacy load_data called. Loading default site.")
    dm = DataManager()
    return dm.get_data('restefond')
