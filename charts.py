import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine

conn_str = "postgresql://<CONNECTION STRING HERE>"

engine = create_engine(conn_str)

measurements_query = """
SELECT time, category, value
FROM measurements
WHERE 1=1
AND EXTRACT(MONTH FROM time) = 10
AND EXTRACT(DAY FROM time) > 10
"""

heat_events_query = """
SELECT time, category, value
FROM events
WHERE 1=1
AND category = 'heat_relay'
--Restrict to most recent attempt
AND EXTRACT(MONTH FROM time) = 10
AND EXTRACT(DAY FROM time) > 10
"""

fan_events_query = """
SELECT time, category, value
FROM events
WHERE 1=1
AND category = 'fan_relay'
--Restrict to most recent attempt
AND EXTRACT(MONTH FROM time) = 10
AND EXTRACT(DAY FROM time) > 10
"""

df_m = pd.read_sql(measurements_query, engine)
df_h = pd.read_sql(heat_events_query, engine)
df_c = pd.read_sql(fan_events_query, engine)

#Get next time in dataset by shifting column back
df_h['next_time'] = df_h['time'].shift(-1)
df_c['next_time'] = df_c['time'].shift(-1)

#Convert on/off data to % on-time data
def getPercentOnData(df_in : pd.DataFrame) -> pd.DataFrame:
    #Generate hour range
    start = df_in['time'].min().floor('h')
    end = df_in['next_time'].max().ceil('h')
    hours = pd.date_range(start, end, freq='h')

    hourly_data = []
    for hour_start in hours[:-1]:
        hour_end = hour_start + pd.Timedelta(hours=1)
        total_on = 0
        
        # Find rows overlapping with this hour
        for _, row in df_in.iterrows():
            overlap_start = max(row['time'], hour_start)
            overlap_end = min(row['next_time'], hour_end)
            overlap = (overlap_end - overlap_start).total_seconds()
            if overlap > 0 and row['value'] == 1:
                total_on += overlap
    
        percent_on = (total_on / 3600.0) * 100
        hourly_data.append({'time': hour_start, 'percent_on': percent_on})
    return pd.DataFrame(hourly_data, columns=['time', 'percent_on'])

df_heat_hours = getPercentOnData(df_h)
df_fan_hours = getPercentOnData(df_c)

#Convert timestamps to time since start
ref_time = pd.Timestamp('2025-10-11 18:00:00')
df_m['time'] = pd.to_datetime(df_m['time'])
df_m['hours_since_start'] = (df_m['time'] - ref_time).dt.total_seconds() / 3600.0

df_heat_hours['hours_since_start'] = (df_heat_hours['time'] - ref_time).dt.total_seconds() / 3600.0
df_fan_hours['hours_since_start'] = (df_fan_hours['time'] - ref_time).dt.total_seconds() / 3600.0

#Plot layout
sns.set(style="whitegrid")
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(8, 4.5), sharex=True,
    gridspec_kw={'height_ratios': [1, 1]}  # optional: top plot taller
)

# Temperature Plot
sns.lineplot(data=df_m, x='hours_since_start', y='value', ax=ax1, color='tab:green')
ax1.set_ylabel('°F')
ax1.set_title('Temperature vs Relay Usage')

# Relay plot
sns.lineplot(data=df_heat_hours, x='hours_since_start', y='percent_on', ax=ax2, color='tab:red', label = 'Heat Relay')
sns.lineplot(data=df_fan_hours, x='hours_since_start', y='percent_on', ax=ax2, color='tab:blue', label = 'Fan Relay')
ax2.set_ylabel('Relay On-Time (%)')
ax2.set_xlabel('Hours Since Start')

plt.tight_layout()
plt.show()