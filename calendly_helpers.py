import requests
import json
import pandas as pd
import time
import datetime
from datetime import timedelta
import pickle
import configparser

from functools import lru_cache

config = configparser.ConfigParser()
config.read('calendly_secrets.ini')
CLIENTID = config['Calendly']['CLIENTID']
CLIENTSECRET = config['Calendly']['CLIENTSECRET']
REDIRECT_URI = config['Calendly']['REDIRECT_URI']

USERS = config['Calendly']['USERS']
ORANIZATION = config['Calendly']['ORANIZATION']


def today_str(fmt="%Y-%m-%d"):
    date = datetime.datetime.strftime(datetime.datetime.now(), fmt)
    return date


def yesterday_str(fmt="%Y-%m-%d"):
    today = datetime.datetime.now()
    yesterday = today - timedelta(days=1)
    date = datetime.datetime.strftime(yesterday, fmt)

    return date


def url_for_code():
    return 'https://auth.calendly.com/oauth/authorize?client_id={}&response_type=code&redirect_uri=http://localhost'.format(
        CLIENTID)


def get_ttl_hash(seconds=7200):
    """Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)


@lru_cache
def retreive_access_token(code, ttl_hash=None):
    del ttl_hash
    url = "https://auth.calendly.com/oauth/token"

    payload = {'grant_type': 'authorization_code',
               'client_id': CLIENTID,
               'client_secret': CLIENTSECRET,
               'code': code,
               'redirect_uri': REDIRECT_URI}
    headers = {'Content-Type': 'application/json'}
    response = requests.request(
        "POST", url, data=json.dumps(payload), headers=headers)
    return(response.json()['access_token'])


def restore_access_token_from_pickle():
    return pickle.load(open('token.p', 'rb'))


def refresh_access_token():
    """Tries to use the old access token if available. If not calls retreive_access_token() to create a new token.

    Returns:
        access_token [str]: the access token for the rest of the API calls
    """
    access_token = restore_access_token_from_pickle()
    url = "https://auth.calendly.com/oauth/introspect"

    payload = {'client_id': CLIENTID,
               'client_secret': CLIENTSECRET,
               'token': access_token}
    headers = {'Content-Type': 'application/json'}

    response = requests.request(
        "POST", url, data=json.dumps(payload), headers=headers)

    print(response.json())

    if response.json()['active'] is True:
        return access_token
    else:
        print(url_for_code())
        code = input("Provide Code: ")

        access_token = retreive_access_token(
            code=code, ttl_hash=get_ttl_hash())
        pickle.dump(access_token, open('token.p', 'wb'))
        return access_token


def retreive_userid(access_token):
    url = "https://api.calendly.com/users/me"

    headers = {
        'Authorization': 'Bearer {}'.format(access_token)}

    response = requests.request("GET", url, headers=headers)
    userid = response.json()['resource']['uri']
    return(userid)


def get_scheduled_events(access_token):
    counter = 100
    url = "https://api.calendly.com/scheduled_events"

    querystring = {
        "user": "https://api.calendly.com/users/CFCHKQ5NWBSURA7V", "count": counter}

    headers = {'Authorization': 'Bearer {}'.format(access_token)}

    response = requests.request(
        "GET", url, headers=headers, params=querystring)
    next_page = response.json()['pagination']['next_page']

    full_file = pd.json_normalize(response.json()['collection'])

    while next_page:

        response = requests.request(
            "GET", next_page, headers=headers, params=querystring)
        next_page = response.json()['pagination']['next_page']

        page = pd.json_normalize(response.json()['collection'])

        full_file = full_file.append(page)

    return full_file


def get_invitees(event_url, access_token):
    event_uuid = parse_event_uuid(event_url)

    url = "https://api.calendly.com/scheduled_events/{}/invitees".format(
        event_uuid)

    querystring = {"sort": "created_at:asc", "count": "100"}

    headers = {'Authorization': 'Bearer {}'.format(access_token)}

    response = requests.request(
        "GET", url, headers=headers, params=querystring)
    try:
        invitees = response.json()['collection']
    except:
        print(response.json())

    return pd.DataFrame([parse_contact(item) for item in invitees])


def parse_event_uuid(event_url):
    return event_url.split('/')[-1]


def parse_qna(qna, contact):
    for question in qna:
        if question['question'] == 'Employee ID#:':
            contact['EmpNum'] = question.get('answer', None)
        elif question['question'] == 'When is the next day you are scheduled to work, after the selected date? (it is recommended that you are NOT scheduled to work the day following your POD appointment)':
            contact['working_after_vaccine'] = question.get('answer', None)
        elif question['question'] == 'Unit/Dept:':
            contact['unit'] = question.get('answer', None)
        elif question['question'] == 'Title:':
            contact['position'] = question.get('answer', None)


def parse_contact(item):
    contact = {}
    contact['created_at'] = item['created_at']
    contact['email'] = item.get('email', None)
    contact['event'] = item.get('event', None)
    contact['name'] = item.get('name', None)
    qna = item.get('questions_and_answers')
    parse_qna(qna, contact)
    contact['uri'] = item['uri']
    contact['updated_at'] = item['updated_at']
    contact['contact_number'] = item['text_reminder_number']
    contact['status'] = item['status']

    return contact


def get_invitee_details(events_df, access_token):
    df = None
    for event_url in list(events_df.uri):
        try:
            if df is None:
                df = get_invitees(event_url, access_token)
            else:
                df = df.append(get_invitees(event_url, access_token))
        except:
            print(event_url)
    return df
