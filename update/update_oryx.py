#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import datetime as dt

def download_page():
    url = "https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html"
    response = requests.get(url)
    html = BeautifulSoup(response.text, 'html.parser')
    return html
    
def format_dataframe(df):
    flagmap = {
        'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Flag_of_the_Soviet_Union.svg/23px-Flag_of_the_Soviet_Union.svg.png': 'ussr',
        'https://upload.wikimedia.org/wikipedia/en/thumb/f/f3/Flag_of_Russia.svg/23px-Flag_of_Russia.svg.png': 'russian federation',
        'https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Flag_of_Ukraine.svg/23px-Flag_of_Ukraine.svg.png': 'ukraine',
        'https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Flag_of_Belarus.svg/23px-Flag_of_Belarus.svg.png': 'belarus',
        'https://upload.wikimedia.org/wikipedia/en/thumb/a/ae/Flag_of_the_United_Kingdom.svg/23px-Flag_of_the_United_Kingdom.svg.png': 'united kingdom',
        'https://upload.wikimedia.org/wikipedia/en/thumb/a/a4/Flag_of_the_United_States.svg/23px-Flag_of_the_United_States.svg.png': 'united states'
    }

    df['category'] = df.subheading.apply(lambda _: _.split('(')[0])
    df['country'] = df.heading.apply(lambda _: _.split('-')[0].strip())
    df['equipment_origin'] = df.flag.map(flagmap)
    return df

def parse_article(html):
    
    dataset = []
    article = html.select('.post-body.entry-content div')[-1]
    blocks = html.select('article h3, article ul')

    heading = ''
    subheading = ''
    for block in blocks:
        if block.name == 'h3':
            if 'color: red' in str(block):
                heading = block.get_text()
            subheading = block.get_text()
        elif block.name == 'ul':
            for li in block.select('li'):
                flag = li.select('img.thumbborder')[0]['src']
                equipment = li.get_text().split(':')[0].strip()
                for a in li.select('a'):
                    source = a['href']
                    text = a.get_text()
                    dataset.append(dict(
                        heading = heading,
                        subheading = subheading,
                        flag = flag,
                        equipment = equipment,
                        source = source,
                        text = text
                    ))
    df = pd.DataFrame(dataset)
    df = format_dataframe(df)
    return df

def parse_category(text, country):
    data = []
    name = text.split('(')[0]
    for section in text.split(','):
        parts = section.split(':')
        if len(parts) == 2:
            state = parts[0].split()[-1]
            value = int(re.findall('[0-9]*', parts[1].split()[0])[0])
            data.append(dict(
                country = country,
                category = name,
                state = state,
                value = value
            ))
    return data

def parse_categories(df):
    categories = []
    for text, country in df.groupby('subheading').country.first().iteritems():
        categories.extend(parse_category(text, country))
    categories = pd.DataFrame(categories)
    return categories

def get_data(html):
    df = parse_article(html)
    summary = parse_categories(df)
    reports = df[['country', 'category', 'equipment', 'equipment_origin', 'text', 'source']]
    return summary, reports

def get_timestamp():
    return dt.datetime.utcnow().replace(microsecond=0)

def get_difference(summary, prev_summary):
    index_cols = ['country', 'category', 'state']
    df_diff = pd.concat([
        prev_summary.set_index(index_cols), 
        summary.set_index(index_cols)], axis=1).fillna(0)
    df_diff.columns = [0,1]
    df_diff['value'] = df_diff[1] - df_diff[0]
    df_diff = df_diff[df_diff.value != 0]
    return df_diff.reset_index()[['country', 'category', 'state', 'value']]

def normalize_log(log):
    category_changes = [{
        'to_replace': 'communications station',
        'replace_with': 'communications stations'
    }]
    log['category'] = log.category.apply(lambda _: _.lower().strip())
    log = log.groupby(['timestamp', 'country', 'category', 'state']).value.sum().reset_index()
    for change in category_changes:
        log.category = log.category.replace(change['to_replace'], change['replace_with'])
    return log

def update_log(summary):
    prev_summary = pd.read_csv('summary.csv')
    log = pd.read_csv('log.csv', date_parser=['timestamp'])
    summary_diff = get_difference(summary, prev_summary)
    timestamp = get_timestamp()
    summary_diff.insert(0, 'timestamp', timestamp)
    log = pd.concat([log, summary_diff])
    log = normalize_log(log)
    return log

def save_all(summary, reports, log):
    summary.to_csv('summary.csv', index=False)
    reports.to_csv('reports.csv', index=False)
    log.to_csv('log.csv', float_format="%.0f", index=False)

html = download_page()
summary, reports = get_data(html)
log = update_log(summary)
save_all(summary, reports, log)
