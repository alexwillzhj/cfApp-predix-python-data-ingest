import os
import json
import redis
import requests
import cPickle as pickle
from flask import Flask, request
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
import numpy as np
import websocket
import time
from apscheduler.schedulers.background import BackgroundScheduler
import code

app = Flask(__name__)

# Get VCAP_APPLICATION
cf_env = os.getenv('VCAP_APPLICATION')
if cf_env is None:
    # Config basic and UAA info
    with open('localConfig.json') as json_file:
        local_env = json.load(json_file)
    host = 'localhost'
    uaa_url = local_env['development']['uaa_url']
    base64ClientCredential = local_env['development']['base64ClientCredential']
    client_id = local_env['development']['client_id']
    grant_type = local_env['development']['grant_type']

    # Config redis
    redis_host = local_env['development']['redis_host']
    redis_port = int(local_env['development']['redis_port'])
    redis_password = local_env['development']['redis_password']
    redis_db = 0

    # Config Timeseries
    ts_query_url = local_env['development']['timeseries_query_url']
    ts_ingest_url = local_env['development']['timeseries_ingest_url']
    ts_zone_id = local_env['development']['timeseries_zone_id']

    # Data File
    jsonfilename = '2015_smd_hourly_loc.json'

else:
    # Config basic and UAA info
    host = json.loads(cf_env)['application_uris'][0]
    uaa_url = str(os.getenv('uaa_url'))
    base64ClientCredential = str(os.getenv('base64ClientCredential'))
    client_id = str(os.getenv('client_id'))
    grant_type = str(os.getenv('grant_type'))

    # Config redis
    env_vars = os.environ.get('VCAP_SERVICES')
    redis_service = json.loads(env_vars)['redis'][0]
    redis_host = redis_service['credentials']['host']
    redis_port = redis_service['credentials']['port']
    redis_password = redis_service['credentials']['password']
    redis_db = 0

    # Config Timeseries
    ts_service = json.loads(env_vars)['predix-timeseries'][0]
    ts_query_url = ts_service['credentials']['query']['uri']
    ts_ingest_url = ts_service['credentials']['ingest']['uri']
    ts_zone_id = ts_service['credentials']['ingest']['zone-http-header-value']

    # Data File
    jsonfilename = '/home/vcap/app/2015_smd_hourly_loc.json'


# Obtain PORT
port = int(os.getenv("PORT", 64781))

# Initialize Timeseries info
ts = {'name': 'timeseries'}

# Initialize runtime_record
scheduler = BackgroundScheduler()

# Open data file
with open(jsonfilename) as json_data:
    json_data = json.load(json_data)
data_loc = json_data['data']['loc_data']

# Initialize data pointer
data_pointer = 0    # the beginning of the data


# Obtain TOKEN for Timeseries service
@app.route('/getToken', methods=['GET'])
def token_client():
    url = uaa_url + "/oauth/token"
    payload = "client_id=" + client_id + "&grant_type=" + grant_type
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'authorization': "Basic " + base64ClientCredential
    }
    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response.text)
    return response_json['access_token']


@app.route('/')
def welcome_func():
    return "Welcome to 'power data ingest to timeseries'!"


@app.route('/getTSStatus', methods=['GET'])
def setting_ts():
    # Get token
    ts['token'] = str(token_client())

    # Get times eries information in local mode
    try:
        ts['query_url'] = ts_query_url
        ts['ingest_url'] = ts_ingest_url
        ts['headers'] = {
            'content-type': "application/json",
            'authorization': "Bearer " + ts['token'],
            'Origin': 'https://www.predix.io',
            'predix-zone-id': ts_zone_id
        }
        return "Timeseries service ready."
    except:
        return "Timeseries service error."


@app.route('/tsIngestPower', methods=['GET'])
def ts_ingest_power_func(ingest_tagname='tmp', ingest_timestamp='0', ingest_value='0'):

    # get data pointer
    global data_pointer

    # Get token or Update token
    setting_ts()

    # Get time for ingest_timestamp
    curr_time_cnt = time.time()
    ingest_timestamp = str(int(round(curr_time_cnt / 10) * 10 * 1000))

    # ts query body
    ts['ingest_body'] = '{"messageId": "1453338376222", \
                         "body": ['

#    code.interact(local=locals())

    for idx, tagname in enumerate(data_loc.keys()):
        if 'Date' not in tagname and 'Hour' not in tagname:
            ts['ingest_body'] += '{"name": "POWER_FORECAST_' + tagname + '",\
                                    "datapoints":[[' + ingest_timestamp + ',' + str(data_loc[tagname][data_pointer]) + ',3]], \
                                    "attributes": {"host": "server1","customer": "Acme"}}'
            if idx < len(data_loc.keys()) - 1:
                ts['ingest_body'] += ','

    ts['ingest_body'] += ']}'

    ws = websocket.create_connection(ts['ingest_url'], header=ts['headers'])

    response = ws.send(ts['ingest_body'])

    data_pointer += 1

    if data_pointer >= len(data_loc[data_loc.keys()[0]]):
        data_pointer = 0

    print ts['ingest_body']

    return str(response)


# start ts ingesting job
job_ts_ingest = scheduler.add_job(ts_ingest_power_func, 'interval', seconds=10)
job_ts_ingest.pause()


@app.route('/startIngestScheduler', methods=['GET'])
def start_ingest_func():
    # start job
    global job_ts_ingest
    job_ts_ingest.resume()
    return "Job " + job_ts_ingest.id + " started!"


@app.route('/pauseIngestScheduler', methods=['GET'])
def pause_ingest_func():
    # start job
    global job_ts_ingest
    job_ts_ingest.pause()
    return "Job " + job_ts_ingest.id + " paused!"


if __name__ == '__main__':

    if cf_env is None:
        setting_ts()
        scheduler.start()

        app.run(host='127.0.0.1', port=5555)
    else:
        setting_ts()
        scheduler.start()

        app.run(host='0.0.0.0', port=port)
