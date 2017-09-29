#!/usr/bin/python
# -*- coding: utf-8 -*-

from six.moves import urllib
from datetime import datetime
from subprocess import call
from mastodon import Mastodon
import time
import threading
import csv
import os
import json
import time
import signal
import sys
import os.path        # For checking whether secrets file exists
import requests       # For doing the web stuff, dummy!


###############################################################################
# INITIALISATION
###############################################################################

do_upload = True
# Run without uploading, if specified
if '--no-upload' in sys.argv:
    do_upload = False

# Check mastostats.csv exists, if not, create it
if not os.path.isfile("mastostats.csv"):
        print("mastostats.csv does not exist, creating it...")

        # Create CSV header row
        with open("mastostats.csv", "w") as myfile:
            myfile.write("timestamp,usercount,instancecount\n")
        myfile.close()

# Check cnmastostats.csv exists, if not, create it
if not os.path.isfile("cnmastostats.csv"):
        print("cnmastostats.csv does not exist, creating it...")

        # Create CSV header row
        with open("cnmastostats.csv", "w") as myfile:
            myfile.write("timestamp,cnusercount,cninstancecount,cmxusercount,cmxtootcount,tootcnusercount,tootcntootcount,acgusercount,acgtootcount\n")
        myfile.close()

# Returns the parameter from the specified file
def get_parameter( parameter, file_path ):
    # Check if secrets file exists
    if not os.path.isfile(file_path):
        print("File %s not found, exiting."%file_path)
        sys.exit(0)

    # Find parameter in file
    with open( file_path ) as f:
        for line in f:
            if line.startswith( parameter ):
                return line.replace(parameter + ":", "").strip()

    # Cannot find parameter, exit
    print(file_path + "  Missing parameter %s "%parameter)
    sys.exit(0)

# Load secrets from secrets file
secrets_filepath = "secrets/secrets.txt"
uc_client_id     = get_parameter("uc_client_id",     secrets_filepath)
uc_client_secret = get_parameter("uc_client_secret", secrets_filepath)
uc_access_token  = get_parameter("uc_access_token",  secrets_filepath)

# Load configuration from config file
config_filepath = "config.txt"
mastodon_hostname = get_parameter("mastodon_hostname", config_filepath) # E.g., mastodon.social

# Initialise Mastodon API
mastodon = Mastodon(
    client_id = uc_client_id,
    client_secret = uc_client_secret,
    access_token = uc_access_token,
    api_base_url = 'https://' + mastodon_hostname,
)

# Initialise access headers
headers={ 'Authorization': 'Bearer %s'%uc_access_token }


###############################################################################
# GET THE DATA
###############################################################################

# Get current timestamp
ts = int(time.time())

page = requests.get('https://instances.mastodon.xyz/instances.json')

instances = json.loads(page.content)

user_count = 0
instance_count = 0
for instance in instances:
    if not "users" in instance: continue
    user_count += instance["users"]
    if instance["up"] == True:
        instance_count += 1

print("Number of users: %s " % user_count)
print("Number of instances: %s " % instance_count)

# Get Chinese instances info
cnuser_count = 0
cninstance_count = 0
cmxuser_count = 0
cmxtoot_count = 0
for instance in instances:
    if not "info" in instance: continue
    if not "languages" in instance["info"]: continue
    if "zh" in instance["info"]["languages"]:
        if not "users" in instance: continue
        cnuser_count += instance["users"]
        if instance["up"] == True:
            cninstance_count += 1
    if instance["name"] == "cmx.im":
        cmxuser_count = instance["users"]
        cmxtoot_count = instance["statuses"]
    if instance["name"] == "tootcn.com":
        tootcnuser_count = instance["users"]
        tootcntoot_count = instance["statuses"]
    if instance["name"] == "acg.mn":
        acguser_count = instance["users"]
        acgtoot_count = instance["statuses"]

print("Number of Chinese users: %s " % cnuser_count)
print("Number of Chinese instances: %s " % cninstance_count)
print("Number of CMX users: %s " % cmxuser_count)
print("Number of CMX statuses %s " % cmxtoot_count)
###############################################################################
# LOG THE DATA
###############################################################################

# Append to CSV file
with open("mastostats.csv", "a") as myfile:
    myfile.write(str(ts) + "," + str(user_count) + "," + str(instance_count) + "\n")

with open("cnmastostats.csv", "a") as myfile:
    myfile.write(str(ts) + "," + str(cnuser_count) + "," + str(cninstance_count) + "," + str(cmxuser_count) + "," + str(cmxtoot_count) + "," + str(tootcnuser_count) + "," + str(tootcntoot_count) + "," + str(acguser_count) + "," + str(acgtoot_count) + "\n")

###############################################################################
# WORK OUT THE TOOT TEXT
###############################################################################

# Load CSV file
with open('mastostats.csv') as f:
    usercount_dict = [{k: int(v) for k, v in row.items()}
        for row in csv.DictReader(f, skipinitialspace=True)]

with open('cnmastostats.csv') as f:
    cnusercount_dict = [{k: int(v) for k, v in row.items()}
        for row in csv.DictReader(f, skipinitialspace=True)]

# Returns the timestamp,usercount pair which is closest to the specified timestamp
def find_closest_timestamp( input_dict, seek_timestamp ):
    a = []
    for item in input_dict:
        a.append( item['timestamp'] )
    return input_dict[ min(range(len(a)), key=lambda i: abs(a[i]-seek_timestamp)) ]


# Calculate difference in times
hourly_change_string = ""
daily_change_string  = ""
weekly_change_string = ""

one_hour = 60 * 60
one_day  = one_hour * 24
one_week = one_hour * 168

# Hourly change
if len(usercount_dict) > 2:
    one_hour_ago_ts = ts - one_hour
    one_hour_ago_val = find_closest_timestamp( usercount_dict, one_hour_ago_ts )
    hourly_change = user_count - one_hour_ago_val['usercount']
    print "Hourly change %s"%hourly_change
    if hourly_change > 0:
        hourly_change_string = "过去一小时中" + " + " + format(hourly_change, ",d") + "位用户\n"

# Daily change
if len(usercount_dict) > 24:
    one_day_ago_ts = ts - one_day
    one_day_ago_val = find_closest_timestamp( usercount_dict, one_day_ago_ts )
    daily_change = user_count - one_day_ago_val['usercount']
    print "Daily change %s"%daily_change
    if daily_change > 0:
        daily_change_string = "过去一天中" + " + " + format(daily_change, ",d") + "位用户\n"

# Weekly change
if len(usercount_dict) > 168:
    one_week_ago_ts = ts - one_week
    one_week_ago_val = find_closest_timestamp( usercount_dict, one_week_ago_ts )
    weekly_change = user_count - one_week_ago_val['usercount']
    print "Weekly change %s"%weekly_change
    if weekly_change > 0:
        weekly_change_string = "过去一周中" + " + " + format(weekly_change, ",d") + "位用户\n"

# Chinese Instance Monitoring
# Hourly change
if len(cnusercount_dict) > 2:
    one_hour_ago_ts = ts - one_hour
    one_hour_ago_val = find_closest_timestamp( cnusercount_dict, one_hour_ago_ts )
    cnuser_hourly_change = cnuser_count - one_hour_ago_val['cnusercount']
    # cninstance_hourly_change = cninstance_count - one_hour_ago_val['cninstancecount']

    cmxuser_hourly_change = cmxuser_count - one_hour_ago_val['cmxusercount']
    cmxtoot_hourly_change = cmxtoot_count - one_hour_ago_val['cmxtootcount']
    tootcnuser_hourly_change = tootcnuser_count - one_hour_ago_val['tootcnusercount']
    tootcntoot_hourly_change = tootcntoot_count - one_hour_ago_val['tootcntootcount']
    acguser_hourly_change = acguser_count - one_hour_ago_val['acgusercount']
    acgtoot_hourly_change = acgtoot_count - one_hour_ago_val['acgtootcount']

    print "CN User Hourly change %s"%cnuser_hourly_change
    # print "CN Instance Hourly change %s"%cninstance_hourly_change
    print "CMX User Hourly change %s"%cmxuser_hourly_change
    print "CMX Toot Hourly change %s"%cmxtoot_hourly_change

    cnuser_hourly_change_string = "+ " + format(cnuser_hourly_change, ",d") + "(" + format(cnuser_count, ",d") + ") 位用户\n"

    # cninstance_hourly_change_string = "+" + format(cninstance_hourly_change, ",d") + "(" + format(cninstance_count, ",d") + ") 位用户\n"
    cmxuser_hourly_change_string = "+ " + format(cmxuser_hourly_change, ",d") + "(" + format(cmxuser_count, ",d") + ") 位用户\n"
    cmxtoot_hourly_change_string = "+ " + format(cmxtoot_hourly_change, ",d") + "(" + format(cmxtoot_count, ",d") + ") 条嘟文\n"
    tootcnuser_hourly_change_string = "+ " + format(tootcnuser_hourly_change, ",d") + "(" + format(tootcnuser_count, ",d") + ") 位用户\n"
    tootcntoot_hourly_change_string = "+ " + format(tootcntoot_hourly_change, ",d") + "(" + format(tootcntoot_count, ",d") + ") 条嘟文\n"
    acguser_hourly_change_string = "+ " + format(acguser_hourly_change, ",d") + "(" + format(acguser_count, ",d") + ") 位用户\n"
    acgtoot_hourly_change_string = "+ " + format(acgtoot_hourly_change, ",d") + "(" + format(acgtoot_count, ",d") + ") 条嘟文\n"

    # sys.exit(0)
###############################################################################
# CREATE AND UPLOAD THE CHART
###############################################################################

# Generate chart
call(["gnuplot", "generate.gnuplot"])


if do_upload:
    # Upload chart
    file_to_upload = 'graph.png'

    print "Uploading %s..."%file_to_upload
    media_dict = mastodon.media_post(file_to_upload)

    print "Uploaded file, returned:"
    print str(media_dict)

    ###############################################################################
    # T  O  O  T !
    ###############################################################################

    toot_text = "<-----长毛象宇宙中----->\n"
    toot_text += format(user_count, ",d") + " 位用户\n"
    toot_text += format(instance_count, ",d") + " 个已知活跃实例\n"
    toot_text += hourly_change_string
    toot_text += daily_change_string
    toot_text += weekly_change_string
    # toot_text += "<-----长毛象中文区----->\n"
    # toot_text += format(cnuser_count, ",d") + " 位中文用户\n"
    # toot_text += format(cninstance_count, ",d") + " 个已知中文实例\n"
    # toot_text += cnuser_hourly_change_string
    toot_text += "<--------cmx.im-------->\n"
    toot_text += cmxuser_hourly_change_string
    toot_text += cmxtoot_hourly_change_string
    # toot_text += "cmx.im共有 " + format(cmxuser_count, ",d") + " 位用户\n"
    # toot_text += "他们一共嘟出了 " + format(cmxtoot_count, ",d") + " 条嘟文\n"
    toot_text += "<------tootcn.com------>\n"
    toot_text += tootcnuser_hourly_change_string
    toot_text += tootcntoot_hourly_change_string
    toot_text += "<--------acg.mn-------->\n"
    toot_text += acguser_hourly_change_string
    toot_text += acgtoot_hourly_change_string


    print "Tooting..."
    print toot_text

    mastodon.status_post(toot_text, in_reply_to_id=None, media_ids=[media_dict] )

    print "Successfully tooted!"
else:
    print("--no-upload specified, so not uploading anything")
