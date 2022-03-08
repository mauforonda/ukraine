#!/usr/bin/env python

import requests
import datetime as dt
import pandas as pd

def parse_feature(f):
    desc = {}
    for entry in  f['properties']['description'].split('\n'):
        entry_parts = entry.split(': ')
        if len(entry_parts) > 1:
            desc[entry_parts[0].lower()] = entry_parts[1].strip()
    lon, lat = f['geometry']['coordinates']
    title = f['properties']['title']
    event_group = f['properties']['group']
    return {**{'title':title, 'lat':lat, 'lon':lon, 'event_group':event_group}, **desc}

def parse_map(response):
    groups = {g['id']:g['title'] for g in response['geojson']['groups']}
    df = pd.DataFrame([parse_feature(f) for f in response['geojson']['features'] if f['properties'].__contains__('description')])
    df['date'] = pd.to_datetime(df['date'].str.replace('.', '/', regex=False), format='%d/%m/%Y')
    df['event_group'] = df['event_group'].map(groups)
    return df[['entry', 'date', 'event_group', 'title', 'brief description', 'lat', 'lon', 'country', 'province', 'district', 'town/city', 'arms/munition', 'violence level', 'link', 'geolocation']]

def update_time(response):
    # time = dt.datetime.fromtimestamp(response['latest_map_version'])
    time = dt.datetime.utcnow().replace(microsecond=0)
    with open('time', 'w+') as f:
        f.write(time.isoformat())

response = requests.post('https://maphub.net/json/map_load/176607', json={}).json()
df = parse_map(response)

df.sort_values(['date', 'entry', 'brief description']).to_csv('events.csv', index=False)
update_time(response)
