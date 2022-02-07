# Copyright (c) 2020 Cisco and/or its affiliates.

# This software is licensed to you under the terms of the Cisco Sample
# Code License, Version 1.1 (the "License"). You may obtain a copy of the
# License at

#                https://developer.cisco.com/docs/licenses

# All use of the material herein must be in accordance with the terms of
# the License. All rights not expressly granted by the License are
# reserved. Unless required by applicable law or agreed to separately in
# writing, software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

readMe= """This is a script to send an email alert if the remaining license time in an org an admin has
 access to is less than X days, or if its license capacity is not enough for its current device
 count. The alert is sent using an SMTP server; by  default Gmail. Use an automation platform
 like Zapier to read this email and trigger further actions.
Command line syntax:
 python merakilicensealert.py -k <key> [-u <user> -p <pass> -d <dest>] [-s <srv>] [-t <days>]
    [-m include_empty]
Mandatory argument:
 -k <key>             : Your Meraki Dashboard API key
Arguments to enable sending emails. All three must be given to send email:
 -u <user>            : The username (email address) that will be used to send the alert message
 -p <pass>            : Password for the email address where the message is sent from
 -d <dest>            : Recipient email address
Optional arguments:
 -s <server>          : Server to use for sending SMTP. If omitted, Gmail will be used
 -t <days>            : Alert threshold in days for generating alert. Default is 90
 -m include_empty     : Flag: Also send warnings for new orgs with no devices
Example 1, send email for orgs with 180 or less days license remaining:
 python merakilicensealert.py -k 1234 -u source@gmail.com -p 4321 -d alerts@myserver.com -t 180
Example 2, print orgs with 360 or less days remaining to screen:
 python merakilicensealert.py -k 1234 -t 360"""


import sys, requests, time, json, os
from typing import Text
from datetime import datetime, date

class c_organizationdata:
    def __init__(self):
        self.name          = ''
        self.id            = ''
        self.licensestate  = ''
        self.timeremaining = 0
        self.code          = 4
        self.status        = ''
        self.statustext    = ''
        self.licensetype   = ''
        self.skulist       = []
#end class

#Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting dashboard API max request rate
API_EXEC_DELAY = 0.21

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 30
REQUESTS_READ_TIMEOUT = 30


#used by merakirequestthrottler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now()

STATE_OK = 0
STATE_ORANGE = 1
STATE_RED = 2
STATE_EMPTY = 3
STATE_FAILED = 4
STATE_REQUIRED = 5

def translate_code(org):
    org.status = 'success'
    org.statustext = 'Ok'
    for s in org.skulist:
        if s['statustext'] == 'Expired':
            org.status = 'danger'
            org.statustext = 'Expired'
            return org
        elif s['statustext'] == 'Expiring':
            org.status = 'warning'
            org.statustext = 'Expiring'
    return org

def merakirequestthrottler(p_requestcount=1):
    #makes sure there is enough time between API requests to Dashboard not to hit shaper
    global LAST_MERAKI_REQUEST

    if (datetime.now()-LAST_MERAKI_REQUEST).total_seconds() < (API_EXEC_DELAY*p_requestcount):
        time.sleep(API_EXEC_DELAY*p_requestcount)

    LAST_MERAKI_REQUEST = datetime.now()
    return


def getorglist(p_apikey):
    #returns the organizations' list for a specified admin

    merakirequestthrottler()
    try:
        r = requests.get('https://dashboard.meraki.com/api/v0/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        print('ERROR 01: Unable to contact Meraki cloud')
        sys.exit(2)

    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'id':'null'})
        return returnvalue

    rjson = r.json()

    return(rjson)


def getshardhost():
    return("api.meraki.com")


def getlicensestate(p_apikey, p_shardhost, p_orgid):
    #returns the organizations' list for a specified admin

    merakirequestthrottler()
    try:
        r = requests.get('https://%s/api/v0/organizations/%s/licenseState' % (p_shardhost, p_orgid) , headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        raise Exception('ERROR 03: Unable to contact Meraki cloud')

    if r.status_code != requests.codes.ok:
        raise Exception('ERROR 03: Unable to contact Meraki cloud')

    rjson = r.json()

    return(rjson)

def calcdaysremaining(p_merakidate):
    #calculates how many days remain between today and a date expressed in the Dashboard API license time format

    mdate = datetime.date(datetime.strptime(p_merakidate, '%b %d, %Y UTC'))
    today = date.today()

    #the first part (before space) of the date difference is number of days. rest is garbage
    retvalue = int(str(mdate - today).split(' ')[0])

    return retvalue

def checklicensewarning(p_apikey, p_orglist, p_timethreshold, p_modeincludeempty = False):
    #checks org list for license violations and expiration warnings

    filterlist = []
    i = 0

    for org in p_orglist:
        filterlist.append(c_organizationdata())
        filterlist[i].id = org.id
        filterlist[i].name = org.name
        try:
            licensestate  = getlicensestate(p_apikey, org.shardhost, org.id)
            filterlist[i].licensestate = licensestate['status']

            # Set time remaining
            if licensestate['expirationDate'] == 'N/A':
                if p_modeincludeempty:
                    timeremaining = 0
                else:
                    if licensestate['status'] != 'License Required':
                        timeremaining = p_timethreshold + 1
                    else:
                        timeremaining = 0
            else:
                timeremaining = calcdaysremaining(licensestate['expirationDate'])
            filterlist[i].timeremaining = timeremaining

            # Set code
            if licensestate['status'] == "OK":
                if licensestate['expirationDate'] == 'N/A':
                    filterlist[i].code = STATE_EMPTY
                elif timeremaining > p_timethreshold:
                    filterlist[i].code = STATE_OK
                else:
                    filterlist[i].code = STATE_ORANGE
            else:
                if timeremaining < p_timethreshold: 
                    filterlist[i].code = STATE_RED
                elif licensestate['status'] != 'N/A':  
                    filterlist[i].code = STATE_REQUIRED
                else:
                    filterlist[i].code = STATE_EMPTY
        except:
            filterlist[i].licensestate = 'Failed to connect'
            filterlist[i].timeremaining = 0
            filterlist[i].code = STATE_FAILED
        i += 1

    return(filterlist)

def check_eos(sku):
    current_date = datetime.today()
    result = []
    with open(f'{os.path.dirname(__file__)}/endofsale.json', 'r') as f:
        eos_info = json.load(f)
        for s in eos_info:
            if s['SKU'] == sku:
                eos_date = datetime.strptime(s['eosale'], '%b %d, %Y')
                eosu_date = datetime.strptime(s['eosupport'], '%b %d, %Y')
                if eos_date < current_date:
                    result += ["End of Sale"]
                if eosu_date < current_date:
                    result += ["End of Support"]
                return result
    return result

def check_sku(apikey, org, deadline):
    merakirequestthrottler()

    result = {
        'licensetype' : 'Per-device',
        'skulist' : []
    }

    try:
        r = requests.get('https://%s/api/v0/organizations/%s/licenses' % (getshardhost(), org.id) , headers={'X-Cisco-Meraki-API-Key': apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        raise Exception('ERROR 03: Unable to contact Meraki cloud')

    sku_list = []
    # Co-term licensing
    if r.status_code != requests.codes.ok:
        result['licensetype'] = 'Co-termination'
        try:
            r = requests.get('https://%s/api/v0/organizations/%s/licenseState' % (getshardhost(), org.id) , headers={'X-Cisco-Meraki-API-Key': apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
            r.raise_for_status()

            exp_date = r.json()['expirationDate']
            devices = r.json()['licensedDeviceCounts']

            mdate = datetime.date(datetime.strptime(exp_date, '%b %d, %Y UTC'))
            for d in devices.keys():
                sku_list += [{
                    'SKU' : d,
                    'expiration' : exp_date,
                    'datestring': f"{mdate.day}/{mdate.month}/{mdate.year}",
                    'timeremaining' : calcdaysremaining(exp_date),
                    'amount' : devices[d],
                    'endofsale' : check_eos(d)
                }]
        except:
            raise Exception('ERROR 03: Unable to contact Meraki cloud')

    # Per-device licensing
    else:
        for l in r.json():
            added = False
            for sku in sku_list:
                if sku['SKU'] == l['licenseType'] and sku['expiration'] == l['expirationDate']:
                    sku['amount'] += 1
                    added = True
            if not added:
                if l['expirationDate'] is None:
                    sku_list += [{
                            'SKU' : l['licenseType'],
                            'expiration' : None,
                            'datestring' : 'Not activated',
                            'timeremaining': 10000000000000,
                            'amount' : 1,
                            'endofsale' : check_eos(l['licenseType'])
                        }]
                else:
                    mdate = datetime.date(datetime.strptime(l['expirationDate'], '%Y-%m-%dT%H:%M:%SZ'))
                    today = date.today()
                    remaining = str(mdate - today).split(' ')[0]
                    sku_list += [{
                            'SKU' : l['licenseType'],
                            'expiration' : l['expirationDate'],
                            'datestring': f"{mdate.day}/{mdate.month}/{mdate.year}",
                            'timeremaining': int(remaining),
                            'amount' : 1,
                            'endofsale' : check_eos(l['licenseType'])
                        }]
        sku_list = sorted(sku_list, key=lambda k: k['timeremaining'])
    
    for s in sku_list:
        if s['expiration'] is None or int(s['timeremaining']) > deadline:
            s['status'] = 'success'
            s['statustext'] = 'Ok'
        elif int(s['timeremaining']) < 0:
            s['status'] = 'danger'
            s['statustext'] = 'Expired'
        else:
            s['status'] = 'warning'
            s['statustext'] = 'Expiring'

    result['skulist'] = sku_list

    org.licensetype = result['licensetype']
    org.skulist = result['skulist']
    return org


def check_api_key(apikey, threshold, include_empty = False):
    # compile list of organizations to be processed
    orglist = []
    orgjson = getorglist(apikey)
    if orgjson[0]['id'] == 'null':
        raise Exception('ERROR 07: Unable to retrieve org list')

    i = 0
    for record in orgjson:
        orglist.append(c_organizationdata())
        orglist[i].name = record['name']
        orglist[i].id   = record['id']
        i += 1


    # get shard host/FQDN where destination org is stored
    for record in orglist:
        record.shardhost = getshardhost()

    # find orgs in license incompliance state

    filterlist = checklicensewarning(apikey, orglist, threshold, include_empty)
    
    result = []
    for org in filterlist:
        if org.code != STATE_FAILED and org.code != STATE_EMPTY:
            try:
                full_org = translate_code(check_sku(apikey, org, threshold))
                result += [
                    {
                        'name': full_org.name,
                        'licensetype': full_org.licensetype,
                        'skulist': full_org.skulist,
                        'status': full_org.status,
                        'statustext': full_org.statustext
                    }
                ]
            except Exception as e:
                print("fail here")
                print(e)

    return result
