"""
# get IP addresses for Public Cloud providers
#
# there is one function for each provder that uses the prescribed mechanism
# i.e. aws, gcp, azure
# a hardcoded function for Alibaba Cloud
# and a generic BGP based fucntion used fo DigitalOcean and ....
#
# AWS:
# - download https://ip-ranges.amazonaws.com/ip-ranges.json
# - see: https://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html
#
# Azure:
# - json file download
# - excludes IP tagged with WindowsVirtualDesktop as they are really desktops
#
# GCP:
# - see: https://cloud.google.com/compute/docs/faq#find_ip_range
#
# Oracle:
# - https://docs.cloud.oracle.com/en-us/iaas/tools/public_ip_ranges.json
#
# DigitalOcean:
# - https://bgp.he.net/search?search%5Bsearch%5D=digitalocean&commit=Search
#
# Alibaba:
# - https://bgp.he.net/search?search%5Bsearch%5D=%22alibaba+cloud%22&commit=Search


"""

import argparse
import json
import requests

import pydig


AWSAPIURL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'
AZUREAPIURL = 'https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_20200511.json'
ORACLEAPIURL = 'https://docs.cloud.oracle.com/en-us/iaas/tools/public_ip_ranges.json'
GCPROOT = '_cloud-netblocks.googleusercontent.com'
GENERICAPIURL = 'https://api.bgpview.io/search?query_term='


def parse_digtxt(querystr):
    """ executes dig and parses output and prints CIDR block, if necessary recursively"""
    response = pydig.query(querystr, 'txt')
    for elem in response[0].split():
        if 'include:' in elem:
            parse_digtxt(elem[8:])
        else:
            if 'ip4' in elem:
                print(elem[4:])
            if 'ip6' in elem:
                print(elem[4:])


def get_gcp():
    """calculates the GCP CIDR blocks as tagged in DNS"""
    print('# GCP Start')
    parse_digtxt(GCPROOT)
    print('# GCP End')


def get_aws(verbosity):
    """print AWS IP Cidr blocks"""
    print("# AWS Start")
    try:
        response = requests.get(AWSAPIURL)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            for i in range(0, len(cidrdata["prefixes"])):
                print(cidrdata["prefixes"][i]["ip_prefix"])
            for i in range(0, len(cidrdata["ipv6_prefixes"])):
                print(cidrdata["ipv6_prefixes"][i]["ipv6_prefix"])
    except Exception as get_exception:
        print("Exception")
        print(get_exception)
    print("# AWS End")


def get_azure(verbosity):
    """prints Azure IP addresses"""
    print("# Azure Start")
    try:
        response = requests.get(AZUREAPIURL)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            for i in range(0, len(cidrdata["values"])):
                for j in range(0, len(cidrdata["values"][i]["properties"]["addressPrefixes"])):
                    if cidrdata["values"][i]["properties"]["systemService"] != "WindowsVirtualDesktop":
                        print(cidrdata["values"][i]["properties"]["addressPrefixes"][j])
    except Exception as get_exception:
        print("Exception")
        print(get_exception)
    print("# Azure End")


def get_oracle(verbosity):
    """prints Oracle CLoud IP addresses"""
    print("# Oracle Start")
    try:
        response = requests.get(ORACLEAPIURL)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            for i in range(0, len(cidrdata["regions"])):
                for j in range(0, len(cidrdata["regions"][i]["cidrs"])):
                    print(cidrdata["regions"][i]["cidrs"][j]["cidr"])
    except Exception as get_exception:
        print("Exception")
        print(get_exception)
    print("# Oracle End")


def get_alibaba():
    """prints Alibaba Cloud IPs"""
    #47.89.85.0/24   Alibaba Cloud (India) LLP (C06858506)United States
    #47.74.192.0/18  Alibaba Cloud (Singapore) Private Limited (C06869034)United States
    #47.74.128.0/18  Alibaba Cloud (Singapore) Private Limited (C06869034)United States
    #47.74.128.0/17  Alibaba Cloud (Singapore) Private Limited (C06869034)
    print('# Alibaba Start')
    print('47.89.85.0/24')
    print('47.74.192.0/18')
    print('47.74.128.0/18')
    print('47.74.128.0/17')
    print('# Alibaba End')


def generic_get(search, verbosity):
    """BGB query and prints the CIDR blocks associated"""
    print(f"# {search} Start")
    try:
        response = requests.get(GENERICAPIURL+search)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            for i in range(0, len(cidrdata["data"]["ipv4_prefixes"])):
                print(cidrdata["data"]["ipv4_prefixes"][i]["prefix"])
            for i in range(0, len(cidrdata["data"]["ipv6_prefixes"])):
                print(cidrdata["data"]["ipv6_prefixes"][i]["prefix"])
    except Exception as get_exception:
        print("Exception")
        print(get_exception)
    print(f"# {search} End")


## main
parser = argparse.ArgumentParser(description="Get IP address in CIDR form")
parser.add_argument("-v", "--verbose", help="modify output verbosity", action="store_true")
args = parser.parse_args()
get_aws(args.verbose)
get_azure(args.verbose)
get_gcp()
get_alibaba()
get_oracle(args.verbose)
generic_get("digitalocean", args.verbose)
generic_get("ovh", args.verbose)
