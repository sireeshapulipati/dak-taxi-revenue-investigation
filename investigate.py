import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from google.cloud import bigquery

# Community area mapping
COMMUNITY_AREAS = {
    1: 'Rogers Park', 2: 'West Ridge', 3: 'Uptown', 4: 'Lincoln Square',
    5: 'North Center', 6: 'Lake View', 7: 'Lincoln Park', 8: 'Near North Side',
    9: 'Edison Park', 10: 'Norwood Park', 11: 'Jefferson Park', 12: 'Forest Glen',
    13: 'North Park', 14: 'Albany Park', 15: 'Portage Park', 16: 'Irving Park',
    17: 'Dunning', 18: 'Montclare', 19: 'Belmont Cragin', 20: 'Hermosa',
    21: 'Avondale', 22: 'Logan Square', 23: 'Humboldt Park', 24: 'West Town',
    25: 'Austin', 26: 'West Garfield Park', 27: 'East Garfield Park', 28: 'Near West Side',
    29: 'North Lawndale', 30: 'South Lawndale', 31: 'Lower West Side', 32: 'Loop',
    33: 'Near South Side', 34: 'Armour Square', 35: 'Douglas', 36: 'Oakland',
    37: 'Fuller Park', 38: 'Grand Boulevard', 39: 'Kenwood', 40: 'Washington Park',
    41: 'Hyde Park', 42: 'Woodlawn', 43: 'South Shore', 44: 'Chatham',
    45: 'Avalon Park', 46: 'South Chicago', 47: 'Burnside', 48: 'Calumet Heights',
    49: 'Roseland', 50: 'Pullman', 51: 'South Deering', 52: 'East Side',
    53: 'West Pullman', 54: 'Riverdale', 55: 'Hegewisch', 56: 'Garfield Ridge',
    57: 'Archer Heights', 58: 'Brighton Park', 59: 'McKinley Park', 60: 'Bridgeport',
    61: 'New City', 62: 'West Elsdon', 63: 'Gage Park', 64: 'Clearing',
    65: 'West Lawn', 66: 'Chicago Lawn', 67: 'West Englewood', 68: 'Englewood',
    69: 'Greater Grand Crossing', 70: 'Ashburn', 71: 'Auburn Gresham', 72: 'Beverly',
    73: 'Washington Heights', 74: 'Mount Greenwood', 75: 'Morgan Park', 76: 'O\'Hare',
    77: 'Edgewater'
}

def load_driver_profiles(output_file_path):
    print("Loading driver profiles from JSON...")
    with open(output_file_path, 'r') as f:
        data = json.load(f)
    
    cols = [c['name'] for c in data['results'][0]['columns']]
    rows_data = []
    for r in data['results'][0]['rows']:
        row_val = [v.get('value') for v in r['values']]
        rows_data.append(row_val)
    
    df = pd.DataFrame(rows_data, columns=cols)
    # Convert types
    df['home_zone'] = pd.to_numeric(df['home_zone'], errors='coerce')
    df['active'] = df['active'].apply(lambda x: str(x).lower() == 'true')
    return df

def upload_to_bigquery(df, project_id, dataset_id, table_id):
    print(f"Uploading {len(df)} driver profiles to BigQuery table {project_id}.{dataset_id}.{table_id}...")
    client = bigquery.Client(project=project_id)
    
    table_ref = client.dataset(dataset_id).table(table_id)
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
            bigquery.SchemaField("taxi_id", "STRING"),
            bigquery.SchemaField("driver_tier", "STRING"),
            bigquery.SchemaField("vehicle_type", "STRING"),
            bigquery.SchemaField("company", "STRING"),
            bigquery.SchemaField("home_zone", "INTEGER"),
            bigquery.SchemaField("hire_date", "STRING"),
            bigquery.SchemaField("active", "BOOLEAN"),
        ]
    )
    
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # Wait for the load to complete.
    print("Upload completed successfully.")

def run_bigquery_analysis(project_id):
    print("Running BigQuery analysis queries...")
    client = bigquery.Client(project=project_id)
    
    # 1. Driver Tier Analysis
    print("Querying driver tier statistics...")
    tier_query = """
    SELECT
      d.driver_tier,
      EXTRACT(YEAR FROM t.trip_start_timestamp) AS year,
      COUNT(*) AS total_trips,
      SUM(t.trip_total) AS total_revenue,
      SUM(t.fare) AS total_fare,
      SUM(t.tips) AS total_tips,
      AVG(t.trip_total) AS avg_trip_total
    FROM
      `dak-demo.chicago_taxi_trips.taxi_trips` t
    JOIN
      `dak-demo.chicago_taxi_trips.driver_profiles` d
    ON
      t.taxi_id = d.taxi_id
    WHERE
      t.trip_start_timestamp >= '2019-01-01 00:00:00'
      AND t.trip_start_timestamp < '2024-01-01 00:00:00'
    GROUP BY
      d.driver_tier, year
    ORDER BY
      d.driver_tier, year;
    """
    df_tiers = client.query(tier_query).to_dataframe()
    
    # 2. Zone Analysis
    print("Querying zone statistics...")
    zone_query = """
    SELECT
      pickup_community_area,
      EXTRACT(YEAR FROM t.trip_start_timestamp) AS year,
      COUNT(*) AS total_trips,
      SUM(t.trip_total) AS total_revenue,
      AVG(t.trip_total) AS avg_trip_total
    FROM
      `dak-demo.chicago_taxi_trips.taxi_trips` t
    WHERE
      t.trip_start_timestamp >= '2019-01-01 00:00:00'
      AND t.trip_start_timestamp < '2024-01-01 00:00:00'
    GROUP BY
      pickup_community_area, year
    ORDER BY
      pickup_community_area, year;
    """
    df_zones = client.query(zone_query).to_dataframe()
    
    # 3. Combined Zone & Driver Tier Analysis
    print("Querying zone and driver tier combined statistics...")
    zone_tier_query = """
    SELECT
      t.pickup_community_area,
      d.driver_tier,
      EXTRACT(YEAR FROM t.trip_start_timestamp) AS year,
      COUNT(*) AS total_trips,
      SUM(t.trip_total) AS total_revenue
    FROM
      `dak-demo.chicago_taxi_trips.taxi_trips` t
    JOIN
      `dak-demo.chicago_taxi_trips.driver_profiles` d
    ON
      t.taxi_id = d.taxi_id
    WHERE
      t.trip_start_timestamp >= '2019-01-01 00:00:00'
      AND t.trip_start_timestamp < '2024-01-01 00:00:00'
    GROUP BY
      t.pickup_community_area, d.driver_tier, year
    ORDER BY
      t.pickup_community_area, d.driver_tier, year;
    """
    df_zone_tiers = client.query(zone_tier_query).to_dataframe()
    
    return df_tiers, df_zones, df_zone_tiers

def analyze_rideshare_csv(csv_path):
    print(f"Analyzing rideshare CSV from {csv_path}...")
    df = pd.read_csv(csv_path)
    # Convert month to datetime and extract year
    df['date'] = pd.to_datetime(df['month'])
    df['year'] = df['date'].dt.year
    
    # Filter 2019 and 2023
    df_filtered = df[df['year'].isin([2019, 2023])]
    
    # Group by year and community_area
    df_grouped = df_filtered.groupby(['year', 'community_area'])['rideshare_trip_count'].sum().reset_index()
    return df_grouped

def main():
    # Setup directories
    os.makedirs('charts', exist_ok=True)
    
    # 1. Load driver profiles
    driver_json_path = '/Users/sireesha/.gemini/antigravity-ide/brain/98a850c4-df6c-4b5a-a92e-b5a67b68b820/.system_generated/steps/105/output.txt'
    df_drivers = load_driver_profiles(driver_json_path)
    print(df_drivers.head())
    
    # 2. Upload to BigQuery
    project_id = 'dak-demo'
    dataset_id = 'chicago_taxi_trips'
    table_id = 'driver_profiles'
    upload_to_bigquery(df_drivers, project_id, dataset_id, table_id)
    
    # 3. Query BigQuery
    df_tiers, df_zones, df_zone_tiers = run_bigquery_analysis(project_id)
    
    # Save raw results for validation
    df_tiers.to_csv('charts/raw_tiers.csv', index=False)
    df_zones.to_csv('charts/raw_zones.csv', index=False)
    
    # 4. Analyze Rideshare CSV
    csv_path = '.agent/data/rideshare_trips_by_month.csv'
    df_rideshare = analyze_rideshare_csv(csv_path)
    df_rideshare.to_csv('charts/raw_rideshare.csv', index=False)
    
    # --- DATA PROCESSING ---
    print("\n--- Processing Results ---")
    
    # Tiers pivot
    print("\nDriver Tier Revenue Change (2019 vs 2023):")
    df_tiers_pivot = df_tiers.pivot(index='driver_tier', columns='year', values=['total_revenue', 'total_trips', 'avg_trip_total'])
    df_tiers_pivot.columns = [f"{col[0]}_{col[1]}" for col in df_tiers_pivot.columns]
    
    df_tiers_pivot['revenue_change_abs'] = df_tiers_pivot['total_revenue_2023'] - df_tiers_pivot['total_revenue_2019']
    df_tiers_pivot['revenue_change_pct'] = (df_tiers_pivot['revenue_change_abs'] / df_tiers_pivot['total_revenue_2019']) * 100
    df_tiers_pivot['trips_change_abs'] = df_tiers_pivot['total_trips_2023'] - df_tiers_pivot['total_trips_2019']
    df_tiers_pivot['trips_change_pct'] = (df_tiers_pivot['trips_change_abs'] / df_tiers_pivot['total_trips_2019']) * 100
    print(df_tiers_pivot)
    
    # Zones pivot
    df_zones_pivot = df_zones.pivot(index='pickup_community_area', columns='year', values=['total_revenue', 'total_trips'])
    df_zones_pivot.columns = [f"{col[0]}_{col[1]}" for col in df_zones_pivot.columns]
    df_zones_pivot = df_zones_pivot.fillna(0)
    
    df_zones_pivot['revenue_change_abs'] = df_zones_pivot['total_revenue_2023'] - df_zones_pivot['total_revenue_2019']
    df_zones_pivot['revenue_change_pct'] = np.where(df_zones_pivot['total_revenue_2019'] > 0, 
                                                    (df_zones_pivot['revenue_change_abs'] / df_zones_pivot['total_revenue_2019']) * 100, 
                                                    0)
    df_zones_pivot['trips_change_abs'] = df_zones_pivot['total_trips_2023'] - df_zones_pivot['total_trips_2019']
    df_zones_pivot['trips_change_pct'] = np.where(df_zones_pivot['total_trips_2019'] > 0, 
                                                  (df_zones_pivot['trips_change_abs'] / df_zones_pivot['total_trips_2019']) * 100, 
                                                  0)
    
    # Sort by absolute revenue change
    df_zones_pivot_sorted = df_zones_pivot.sort_values(by='revenue_change_abs', ascending=True)
    print("\nTop 10 Most Affected Zones (by absolute revenue drop):")
    print(df_zones_pivot_sorted.head(10))
    
    # Rideshare pivot
    df_rideshare_pivot = df_rideshare.pivot(index='community_area', columns='year', values='rideshare_trip_count')
    df_rideshare_pivot.columns = [f"rideshare_trips_{col}" for col in df_rideshare_pivot.columns]
    df_rideshare_pivot = df_rideshare_pivot.fillna(0)
    df_rideshare_pivot['rideshare_change_abs'] = df_rideshare_pivot['rideshare_trips_2023'] - df_rideshare_pivot['rideshare_trips_2019']
    df_rideshare_pivot['rideshare_change_pct'] = np.where(df_rideshare_pivot['rideshare_trips_2019'] > 0, 
                                                          (df_rideshare_pivot['rideshare_change_abs'] / df_rideshare_pivot['rideshare_trips_2019']) * 100, 
                                                          0)
    
    # Merge taxi and rideshare data by zone
    df_merged_zones = df_zones_pivot_sorted.join(df_rideshare_pivot, how='inner')
    df_merged_zones['zone_name'] = df_merged_zones.index.map(COMMUNITY_AREAS)
    
    print("\nTop 10 Merged Zone Analysis:")
    print(df_merged_zones[['zone_name', 'total_revenue_2019', 'total_revenue_2023', 'revenue_change_abs', 'rideshare_trips_2019', 'rideshare_trips_2023', 'rideshare_change_abs']].head(10))
    
    df_merged_zones.to_csv('charts/merged_zones.csv', index=True)
    
    # --- VISUALIZATIONS (Stunning Aesthetics) ---
    print("\nGenerating charts...")
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Chart 1: Revenue by Driver Tier (2019 vs 2023)
    fig, ax = plt.subplots(figsize=(9, 6), facecolor='#111625')
    ax.set_facecolor('#171d2f')
    
    tiers = ['Bronze', 'Silver', 'Gold']
    rev_2019 = [df_tiers_pivot.loc[t, 'total_revenue_2019'] / 1e6 for t in tiers]
    rev_2023 = [df_tiers_pivot.loc[t, 'total_revenue_2023'] / 1e6 for t in tiers]
    
    x = np.arange(len(tiers))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, rev_2019, width, label='2019', color='#3b82f6', edgecolor='none', alpha=0.9, zorder=3)
    rects2 = ax.bar(x + width/2, rev_2023, width, label='2023', color='#10b981', edgecolor='none', alpha=0.9, zorder=3)
    
    ax.set_title('Taxi Revenue by Driver Tier (2019 vs 2023)', color='#f8fafc', fontsize=16, pad=20, weight='bold')
    ax.set_xlabel('Driver Tier', color='#94a3b8', fontsize=12, labelpad=10)
    ax.set_ylabel('Total Revenue ($ Millions)', color='#94a3b8', fontsize=12, labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(tiers, color='#f8fafc', fontsize=11)
    ax.tick_params(colors='#94a3b8')
    
    ax.grid(color='#334155', linestyle='--', linewidth=0.5, alpha=0.5, zorder=0)
    
    # Legend
    legend = ax.legend(facecolor='#171d2f', edgecolor='#334155', labelcolor='#f8fafc', fontsize=11)
    
    # Value labels
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f'${h:.1f}M', xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=9)
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f'${h:.1f}M', xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=9)
        
    plt.tight_layout()
    plt.savefig('charts/revenue_by_driver_tier.png', dpi=300, facecolor='#111625')
    plt.close()
    
    # Chart 2: Taxi vs Rideshare Trips in Top Affected Zones
    top_zones_ids = [8, 32, 28, 76, 56] # Near North, Loop, Near West, O'Hare, Midway
    top_zones_names = [COMMUNITY_AREAS[i] for i in top_zones_ids]
    
    taxi_trips_2019 = [df_merged_zones.loc[i, 'total_trips_2019'] / 1e6 for i in top_zones_ids]
    taxi_trips_2023 = [df_merged_zones.loc[i, 'total_trips_2023'] / 1e6 for i in top_zones_ids]
    rs_trips_2019 = [df_merged_zones.loc[i, 'rideshare_trips_2019'] / 1e6 for i in top_zones_ids]
    rs_trips_2023 = [df_merged_zones.loc[i, 'rideshare_trips_2023'] / 1e6 for i in top_zones_ids]
    
    # Panel plot for Taxi vs Rideshare trips comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), facecolor='#111625')
    ax1.set_facecolor('#171d2f')
    ax2.set_facecolor('#171d2f')
    
    x = np.arange(len(top_zones_names))
    width = 0.35
    
    # Taxi panel
    rects_t1 = ax1.bar(x - width/2, taxi_trips_2019, width, label='2019', color='#3b82f6', alpha=0.9, zorder=3)
    rects_t2 = ax1.bar(x + width/2, taxi_trips_2023, width, label='2023', color='#f43f5e', alpha=0.9, zorder=3)
    ax1.set_title('Taxi Trip Volume (2019 vs 2023)', color='#f8fafc', fontsize=14, weight='bold', pad=15)
    ax1.set_ylabel('Trips (Millions)', color='#94a3b8', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(top_zones_names, rotation=30, ha='right', color='#f8fafc')
    ax1.tick_params(colors='#94a3b8')
    ax1.grid(color='#334155', linestyle='--', linewidth=0.5, alpha=0.5, zorder=0)
    ax1.legend(facecolor='#171d2f', edgecolor='#334155', labelcolor='#f8fafc')
    
    for r in rects_t1:
        h = r.get_height()
        ax1.annotate(f'{h:.2f}M', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=8)
    for r in rects_t2:
        h = r.get_height()
        ax1.annotate(f'{h:.2f}M', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=8)
 
    # Rideshare panel
    rects_r1 = ax2.bar(x - width/2, rs_trips_2019, width, label='2019', color='#3b82f6', alpha=0.9, zorder=3)
    rects_r2 = ax2.bar(x + width/2, rs_trips_2023, width, label='2023', color='#10b981', alpha=0.9, zorder=3)
    ax2.set_title('Rideshare Trip Volume (2019 vs 2023)', color='#f8fafc', fontsize=14, weight='bold', pad=15)
    ax2.set_ylabel('Trips (Millions)', color='#94a3b8', fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(top_zones_names, rotation=30, ha='right', color='#f8fafc')
    ax2.tick_params(colors='#94a3b8')
    ax2.grid(color='#334155', linestyle='--', linewidth=0.5, alpha=0.5, zorder=0)
    ax2.legend(facecolor='#171d2f', edgecolor='#334155', labelcolor='#f8fafc')
    
    for r in rects_r1:
        h = r.get_height()
        ax2.annotate(f'{h:.2f}M', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=8)
    for r in rects_r2:
        h = r.get_height()
        ax2.annotate(f'{h:.2f}M', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=8)
 
    plt.suptitle('Trip Volume Decline/Growth in Top Impacted Chicago Zones', color='#f8fafc', fontsize=16, weight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig('charts/taxi_vs_rideshare_trips.png', dpi=300, facecolor='#111625')
    plt.close()
    
    # Chart 3: Market Share Comparison in Key Zones
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#111625')
    ax.set_facecolor('#171d2f')
    
    total_trips_2019 = [t + r for t, r in zip(taxi_trips_2019, rs_trips_2019)]
    total_trips_2023 = [t + r for t, r in zip(taxi_trips_2023, rs_trips_2023)]
    
    taxi_share_2019 = [t / tot * 100 for t, tot in zip(taxi_trips_2019, total_trips_2019)]
    taxi_share_2023 = [t / tot * 100 for t, tot in zip(taxi_trips_2023, total_trips_2023)]
    
    rects_s1 = ax.bar(x - width/2, taxi_share_2019, width, label='2019 Share', color='#3b82f6', alpha=0.9, zorder=3)
    rects_s2 = ax.bar(x + width/2, taxi_share_2023, width, label='2023 Share', color='#ec4899', alpha=0.9, zorder=3)
    
    ax.set_title('Taxi Market Share % of Total Combined Trips (2019 vs 2023)', color='#f8fafc', fontsize=15, weight='bold', pad=20)
    ax.set_ylabel('Market Share (%)', color='#94a3b8', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(top_zones_names, rotation=25, ha='right', color='#f8fafc', fontsize=11)
    ax.tick_params(colors='#94a3b8')
    ax.grid(color='#334155', linestyle='--', linewidth=0.5, alpha=0.5, zorder=0)
    ax.legend(facecolor='#171d2f', edgecolor='#334155', labelcolor='#f8fafc')
    
    for r in rects_s1:
        h = r.get_height()
        ax.annotate(f'{h:.1f}%', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=9)
    for r in rects_s2:
        h = r.get_height()
        ax.annotate(f'{h:.1f}%', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color='#94a3b8', fontsize=9)
        
    plt.tight_layout()
    plt.savefig('charts/taxi_market_share.png', dpi=300, facecolor='#111625')
    plt.close()
 
    print("Charts generated and saved to 'charts/'.")

if __name__ == '__main__':
    main()
