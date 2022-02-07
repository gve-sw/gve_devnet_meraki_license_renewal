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

import re
import datetime
import json
import csv
import requests
import os
import smtplib

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import utils

from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from webapp.models import Log
from django.contrib.auth.models import User
from django.db.models import F

from . import views

def email_check(email):
    with open(f'{os.path.dirname(__file__)}/email_whitelist.json', 'r') as f:
        white = json.load(f)
        for w in white:
            new_w = w.replace('.', '\.')
            matches = re.findall(f"@{new_w}$", email)
            if len(matches) > 0:
                return True
    return False

def parse_api_keys(keys):
    new_keys = keys.replace('\r\n', '\n', 1000)
    return list(filter(lambda x : len(x) > 0, list(map(lambda x : x.strip(), new_keys.split('\n')))))

def countries():
    return ['Algeria', 'Angola', 'Argentina', 'Australia', 'Austria', 'Azerbaijan', 'Bahrain', 'Belgium', 'Botswana', 'Brazil', 'Bulgaria', 'Canada', 'Chile', 'Colombia', 'Costa Rica', 'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Ecuador', 'Estonia', 'Ethiopia', 'Egypt', 'Finland', 'France', 'Germany', 'Ghana', 'Greece', 'Hong Kong', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Korea', 'Kuwait', 'Latvia', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'Macedonia', 'Malaysia', 'Malta', 'Mauritius', 'Mexico', 'Morocco', 'Mozambique', 'Namibia', 'New Zealand', 'Nigeria', 'Norway', 'Panama', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Oman', 'Qatar', 'Réunion', 'Romania', 'Russia', 'Saudi Arabia', 'Singapore', 'Senegal', 'Serbia', 'Slovakia', 'Slovenia', 'South Africa', 'Spain', 'Sweden', 'Switzerland', 'Taiwan', 'Thailand', 'The Netherlands', 'Turkey', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 'Venezuela', 'Vietnam', 'Zambia', 'Zimbabwe']

def make_log(orgs, partner):
    expired = 0
    expiring = 0

    request_date = datetime.date.today()
    for key in orgs:
        for org in key['orgs']:
            for sku in org['skulist']:
                if sku['statustext'] == 'Expired':
                    expired += 1
                elif sku['statustext'] == 'Expiring':
                    expiring += 1
    
    try:
        db_entry = Log(
            name = partner.name,
            country = partner.country,
            email = partner.email,
            requestdate = request_date.strftime("%d/%m/%Y"),
            requestdeadline = partner.deadline,
            apikeys = len(partner.api_keys),
            apikeysstring = str(partner.api_keys),
            expired = expired,
            expiring = expiring
        )
        db_entry.save()

    except Exception as e:
        print(e)
    
def make_overview_csv(orgs):
    with open(f'{os.path.dirname(__file__)}/overview.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'API key',
            'Organisation name',
            'SKU',
            'SKU amount',
            'Renewal date',
            'SKU status'
        ])
        for entry in orgs:
            for org in entry['orgs']:
                for sku in org['skulist']:
                    writer.writerow([
                        entry['obscuredapikey'],
                        org['name'],
                        sku['SKU'],
                        sku['amount'],
                        sku['datestring'],
                        sku['statustext']
                    ])

def make_overview_pdf(orgs):
    doc = SimpleDocTemplate(f"{os.path.dirname(__file__)}/static/webapp/images/overview.pdf", pagesize=letter)

    elements = []

    img = utils.ImageReader(f"{os.path.dirname(__file__)}/static/webapp/images/meraki_logo.png")
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    im = Image(f"{os.path.dirname(__file__)}/static/webapp/images/meraki_logo.png", width=5*cm, height=5*cm*aspect)
    elements.append(im)

    elements.append(Spacer(1, cm * 0.5)) 

    img = utils.ImageReader(f"{os.path.dirname(__file__)}/static/webapp/images/Logo_long_green.png")
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    im2 = Image(f"{os.path.dirname(__file__)}/static/webapp/images/Logo_long_green.png", width=4*cm, height=4*cm*aspect)
    elements.append(im2)

    elements.append(Spacer(1, cm * 0.75)) 

    for entry in orgs:
        elements.append(Paragraph(f"API key {entry['obscuredapikey']}", style=ParagraphStyle("mystyle")))
        elements.append(Spacer(1, cm * 0.75)) 

        data = [[
            'Organisation name',
            'SKU',
            'SKU amount',
            'Renewal date',
            'SKU status'
        ]]
        for org in entry['orgs']:
            for sku in org['skulist']:
                data += [[
                    org['name'],
                    sku['SKU'],
                    sku['amount'],
                    sku['datestring'],
                    sku['statustext']
                ]]

        t = Table(data)

        t.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Courier-Bold'),
            ]))

        elements.append(t)
        elements.append(Spacer(1, cm * 0.75)) 

    doc.build(elements)

def make_logs_csv():
    with open(f'{os.path.dirname(__file__)}/logs.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Partner name',
            'Partner country',
            'Partner email',
            'Request date',
            'Requested timeframe',
            'API keys',
            'Expired SKUs',
            "Expiring SKUs"
        ])

        for log in Log.objects.all().order_by(F("requestdate").desc()):
            writer.writerow([
                log.name,
                log.country,
                log.email,
                log.requestdate,
                log.requestdeadline,
                log.apikeys,
                log.expired,
                log.expiring
            ])

def obscure_api_key(key):
    if len(key) > 2:
        return "XXXXX" + key[-3:]
    else:
        return "XXXXX" + key

def set_users():
    User.objects.all().delete()
    with open(f'{os.path.dirname(__file__)}/users.json', 'r') as f:
        users = json.load(f)
        for u in users:
            if not User.objects.filter(username = u['username']):
                User.objects.create_user(u['username'], u['email'], u['password'])

def make_logs_pdf():
    data = [[
            'Name',
            'Country',
            'Email',
            'Date',
            'Deadline',
            'API keys',
            'Expired',
            "Expiring"
        ]]
    for log in Log.objects.all().order_by(F("requestdate").desc()):
        data += [[
                log.name,
                log.country,
                log.email,
                log.requestdate,
                log.requestdeadline,
                log.apikeys,
                log.expired,
                log.expiring
            ]]
    
    doc = SimpleDocTemplate(f"{os.path.dirname(__file__)}/static/webapp/images/logs.pdf", pagesize=letter)

    elements = []

    img = utils.ImageReader(f"{os.path.dirname(__file__)}/static/webapp/images/meraki_logo.png")
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    im = Image(f"{os.path.dirname(__file__)}/static/webapp/images/meraki_logo.png", width=5*cm, height=5*cm*aspect)
    elements.append(im)

    elements.append(Spacer(1, cm * 0.5)) 

    img = utils.ImageReader(f"{os.path.dirname(__file__)}/static/webapp/images/Logo_long_green.png")
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    im2 = Image(f"{os.path.dirname(__file__)}/static/webapp/images/Logo_long_green.png", width=4*cm, height=4*cm*aspect)
    elements.append(im2)

    elements.append(Spacer(1, cm * 0.75)) 

    t = Table(data)

    t.setStyle(TableStyle([
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Courier-Bold'),
        ]))

    elements.append(t)
    doc.build(elements)

def send_report(partner):
    make_overview_pdf(partner.orgs)

    load_dotenv()

    SENDER_EMAIL = os.environ['SENDER_EMAIL']
    SENDER_PW = os.environ['SENDER_PW']

    title = "Meraki License Overview"
    html = """\
                    <html>
                    <head></head>
                    <body>
                        <p>
                        Your Meraki license overview was generated as attached.<br/>
                        </p>
                    </body>
                    </html>
            """
    text = "Your Meraki license overview was generated as attached."
    
    sender = SENDER_EMAIL
    
    # Create message container 
    msg = MIMEMultipart('alternative')
    msg['Subject'] = title
    msg['From'] = sender
    msg['To'] = partner.email

    # Record the MIME types of both parts - text/plain and text/html 
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    with open(f"{os.path.dirname(__file__)}/static/webapp/images/overview.pdf", "rb") as f:
            part3 = MIMEApplication(f.read(),_subtype="pdf")
    part3.add_header('Content-Disposition','attachment',filename=str(f"overview.pdf"))

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    msg.attach(part3)

    # Send the message via local SMTP server.
    mail = smtplib.SMTP('smtp.gmail.com', 587)

    mail.ehlo()

    mail.starttls()

    mail.login(SENDER_EMAIL, SENDER_PW)
    mail.send_message(msg)
    mail.quit()

def get_nb_devices(org):
    sum = 0
    for s in org['skulist']:
        sum += s['amount']
    return sum

def partner_to_data(partner):
    return json.dumps( {
        "name" : partner.name,
        "country" : partner.country,
        "email" : partner.email,
        "api_keys" : partner.api_keys,
        "deadline" : partner.deadline,
        "orgs" : partner.orgs,
        "sendreport" : partner.sendreport
    } )

def data_to_partner(data):
    p = views.Partner()
    p.name = data["name"]
    p.country = data["country"]
    p.email = data["email"]
    p.api_keys = data["api_keys"]
    p.deadline = data["deadline"]
    p.orgs = data["orgs"]
    p.sendreport = data["sendreport"]
    return p
