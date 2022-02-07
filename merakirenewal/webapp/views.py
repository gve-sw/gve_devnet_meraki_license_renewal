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


import os, json, mimetypes

from django.contrib.auth import authenticate
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce
from django.db.models import F

from . import util
from . import check_sku
from webapp.models import Log

# Create your views here.

class Partner():
    def __init__(self):  
        self.name = None
        self.country = None
        self.email = None
        self.api_keys = []
        self.deadline = None
        self.orgs = []
        self.sendreport = False

def index(request):
    util.set_users()

    context = {
        'hiddenLinks': True,
        'countries' : util.countries(),
    }
    
    return render(request, 'webapp/home.html', context)

def settings(request):
    global partner
    partner = Partner()
    context = {
        'hiddenLinks': True,
        'countries' : util.countries(),
    }
    try:
        partner.name = request.POST["name"].strip()
        partner.country = request.POST["country"].strip()
        partner.email = request.POST["email"].strip()
        partner.api_keys = util.parse_api_keys(request.POST["api-keys"])
        partner.deadline = int(request.POST["deadline"].strip())
        if 'send-report' in request.POST:
            partner.sendreport = True
        else:
            partner.sendreport = False

        error_message = []
        if not util.email_check(partner.email):
            error_message += ["It is necessary to use a corporate e-mail address"]
        if partner.country.startswith('Select'):
            error_message += ["Please select a country from the dropdown list"]
        if partner.api_keys[0].startswith('Please'):
            error_message += ["Please upload a valid CSV format, or enter the API keys manually"]

        context['config_error'] = error_message

        if len(error_message) > 0:
            return render(request, 'webapp/home.html', context) 
        else:
            try: 
                orgs = []
                i = 0
                for k in partner.api_keys:
                    i += 1
                    try:
                        k_orgs = check_sku.check_api_key(threshold=partner.deadline, apikey=k)
                        k_orgs.sort(key=util.get_nb_devices, reverse=True)
                        orgs += [{
                            "apikey": k,
                            "obscuredapikey" : f"{i}",
                            "orgs": k_orgs
                        }]
                    except Exception as e:
                        orgs += [{
                            "apikey": k,
                            "obscuredapikey" : f"{i}",
                            "orgs": []
                        }]
                        print(e)
                partner.orgs = orgs
                return redirect('overview') 
            except Exception as e:
                print(e)
                context['config_error'] = ["Something went wrong on our side. Please try again"]
                return render(request, 'webapp/home.html', context)  

    except Exception as e: 
        print(e)
        context['config_error'] = ["Something went wrong on our side. Please try again"]
        return render(request, 'webapp/home.html', context)  

def overview(request):
    global partner
    
    context = {
        'deadline' : partner.deadline,
        'organisations' : partner.orgs,
        'hiddenLinks' : True,
        'partnerdata' : util.partner_to_data(partner)
    }

    try:
        util.make_log(partner.orgs, partner)
        if partner.sendreport:
            util.send_report(partner)

        return render(request, 'webapp/overview.html', context)
    except Exception as e: 
        print(e)  
        return render(request, 'webapp/overview.html', context)

@login_required
def logs(request):
    logs=[]
    for log in Log.objects.all().order_by(F("requestdate").desc()):
        logs += [{
            "name" : log.name,
            "country" : log.country,
            "email" : log.email,
            "requestdate" : log.requestdate,
            "requestdeadline" : log.requestdeadline,
            "apikeys" : log.apikeys,
            "expired" : log.expired,
            "expiring" : log.expiring
        }]
    
    context = {
        'logs' : logs,
        'hiddenLinks' : True,
    }

    try:
        return render(request, 'webapp/logs.html', context)
    except Exception as e: 
        print(e)  
        return render(request, 'webapp/logs.html', context)

def download_overview(request):
    partner = util.data_to_partner(json.loads(request.POST['partner']))

    util.make_overview_csv(partner.orgs)
    filepath = f'{os.path.dirname(__file__)}/overview.csv'
    path = open(filepath, 'r')
    mime_type, _ = mimetypes.guess_type(filepath)
    response = HttpResponse(path, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % 'overview.csv'
    return response

def download_logs(request):
    util.make_logs_csv()
    filepath = f'{os.path.dirname(__file__)}/logs.csv'
    path = open(filepath, 'r')
    mime_type, _ = mimetypes.guess_type(filepath)
    response = HttpResponse(path, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % 'logs.csv'
    return response

def upload_api_csv(request):
    file = request.FILES["file"]
    if not file.name.lower().endswith('.csv'):
        return "Please upload a valid CSV format, or enter the API keys manually"
    return HttpResponse(file.read())

def download_overview_pdf(request):
    partner = util.data_to_partner(json.loads(request.POST['partner']))

    util.make_overview_pdf(partner.orgs)
    filepath = f'{os.path.dirname(__file__)}/static/webapp/images/overview.pdf'
    path = open(filepath, 'r', encoding='latin-1')
    mime_type, _ = mimetypes.guess_type(filepath)
    response = HttpResponse(path, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % 'overview.pdf'
    return response

def download_logs_pdf(request):
    util.make_logs_pdf()
    filepath = f'{os.path.dirname(__file__)}/static/webapp/images/logs.pdf'
    path = open(filepath, 'r', encoding='latin-1')
    mime_type, _ = mimetypes.guess_type(filepath)
    response = HttpResponse(path, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % 'logs.pdf'
    return response

