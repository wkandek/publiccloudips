"""
Get IP addresses for Public Cloud providers

there is one function for each provder that implements the prescribed mechanism:
- i.e. aws, azure, gcp and oracle have dedicated information sources
- Alibaba Cloud ranges are in a local config file
- a generic BGP based fucntion used for DigitalOcean and OVH

the IP addresses are sorted, the larger CIDR groups come first, otherwise by numeric value ascending

AWS:
- download https://ip-ranges.amazonaws.com/ip-ranges.json
- see: https://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html

Azure:
- uses a combo of a download URL and a weekly changing final URL for unauthenticated access
  see: https://docs.microsoft.com/en-us/azure/virtual-network/service-tags-overview#service-tags-on-premises
- excludes IP tagged with WindowsVirtualDesktop as they are really desktops

GCP:
- see: https://cloud.google.com/compute/docs/faq#find_ip_range

Oracle:
- https://docs.cloud.oracle.com/en-us/iaas/tools/public_ip_ranges.json

DigitalOcean:
- https://bgp.he.net/search?search%5Bsearch%5D=digitalocean&commit=Search

Alibaba: from local text file but see  BGP for more ranges
- https://bgp.he.net/search?search%5Bsearch%5D=%22alibaba+cloud%22&commit=Search
"""

import argparse
import datetime
import ipaddress
import hashlib
import json
import os
import re
import requests
import sys
import time

import pydig


AWSAPIURL = 'https://ip-ranges.amazonaws.com/ip-ranges.json'
AZUREDOWNLOADURL = 'https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519'
ORACLEAPIURL = 'https://docs.cloud.oracle.com/en-us/iaas/tools/public_ip_ranges.json'
GCPROOT = '_cloud-netblocks.googleusercontent.com'
GENERICAPIURL = 'https://api.bgpview.io/search?query_term='


resultset = {} 
providerversion = {}


def check_cidr(cidr):
    """checsk whether the argument is correclty formed network block"""
    try:
        ipaddress.IPv4Network(cidr)
        return True
    except:
        try:
            ipaddress.IPv6Network(cidr)
            return True
        except:
            print(f'Exception in {cidr}')
            return False


def parse_digtxt(querystr,resultset):
    """ executes dig and parses output and prints CIDR block, if necessary recursively"""
    response = pydig.query(querystr, 'txt')
    for elem in response[0].split():
        if 'include:' in elem:
            resultset = parse_digtxt(elem[8:], resultset)
        else:
            if 'ip4' in elem:
                if elem[4:] not in resultset:
                    resultset[elem[4:]] = "GCP"
            if 'ip6' in elem:
                if elem[4:] not in resultset:
                    resultset[elem[4:]] = "GCP"
    return resultset


def get_gcp(resultset, providerversion):
    """extracts the GCP CIDR blocks as tagged in DNS"""
    rundate = datetime.datetime.utcnow()
    providerversion["GCP"] = rundate.strftime('%Y/%m/%d %H:%M:%S')
    resultset = parse_digtxt(GCPROOT,resultset)
    return resultset, providerversion


def get_aws(verbosity, resultset, providerversion):
    """extracts AWS IP Cidr blocks via JSON file"""
    try:
        response = requests.get(AWSAPIURL)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            providerversion["AWS"] = cidrdata["createDate"]+" "+cidrdata["syncToken"]
            for i in range(0, len(cidrdata["prefixes"])):
                if cidrdata["prefixes"][i]["ip_prefix"] not in resultset:
                    resultset[cidrdata["prefixes"][i]["ip_prefix"]] = "AWS"
            for i in range(0, len(cidrdata["ipv6_prefixes"])):
                if cidrdata["ipv6_prefixes"][i]["ipv6_prefix"] not in resultset:
                    resultset[cidrdata["ipv6_prefixes"][i]["ipv6_prefix"]] = "AWS"
    except Exception as get_exception:
        print("Exception")
        print(get_exception)

    return resultset, providerversion


def extract_azure_URL(url):
    """extract JSON file location from download portal"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            p = re.compile('(https://download\.microsoft\.com/download/.+json)",')
            m = p.search(response.text)
    except Exception as get_exception:
        print("Exception in extract Azure URL")
        print(get_exception)
    
    return m.group(1) 


def get_azure(verbosity, resultset, providerversion):
    """extracts Azure IP addresses"""
    url = extract_azure_URL(AZUREDOWNLOADURL)
    try:
        response = requests.get(url)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            providerversion["AZURE"] = cidrdata["changeNumber"]
            for i in range(0, len(cidrdata["values"])):
                for j in range(0, len(cidrdata["values"][i]["properties"]["addressPrefixes"])):
                    if cidrdata["values"][i]["properties"]["systemService"] != "WindowsVirtualDesktop":
                        if cidrdata["values"][i]["properties"]["addressPrefixes"][j] not in resultset:
                          resultset[cidrdata["values"][i]["properties"]["addressPrefixes"][j]] = "Azure"
        else:
          print(f"Error {response.status_code}")
    except Exception as get_exception:
        print("Exception")
        print(get_exception)

    return resultset, providerversion


def get_oracle(verbosity, resultset, providerversion):
    """extracts Oracle CLoud IP addresses from JSON"""
    try:
        response = requests.get(ORACLEAPIURL)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            cidrdata = json.loads(response.content)
            providerversion["ORACLE"] = cidrdata["last_updated_timestamp"]
            for i in range(0, len(cidrdata["regions"])):
                for j in range(0, len(cidrdata["regions"][i]["cidrs"])):
                    if cidrdata["regions"][i]["cidrs"][j]["cidr"] not in resultset:
                        resultset[cidrdata["regions"][i]["cidrs"][j]["cidr"]] = "Oracle"

    except Exception as get_exception:
        print("Exception")
        print(get_exception)

    return resultset, providerversion


def get_sha256_file(filename):
    """calculates SHA256 checksum of file"""
    BLOCKSIZE = 65536
    hasher = hashlib.sha256()
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()


def get_file(provider, resultset, providerversion):
    """extracts Cloud IPs speced in file"""
    try: 
        filename = "./"+provider+"_ips.txt"
        with open(filename) as ip_file:
            ip_fileproperties = os.stat(filename)
            hashstr = get_sha256_file(filename)
            moddate = time.gmtime(ip_fileproperties.st_mtime)
            providerversion[provider.upper()] = str(ip_fileproperties.st_size) + " Size " \
                                                + time.strftime('%Y-%m-%dT%H:%M:%SZ', moddate) + " modified " \
                                                + hashstr 
            for ipspec in ip_file:
                ipspec = ipspec.strip() 
                if ipspec[0] == "#":
                    providerversion[provider.upper()] += " " + ipspec
                else:
                    if check_cidr(ipspec):
                        resultset[ipspec] = provider 
                    else:
                        print(f"Error in CIDR range: {ipspec}")
    except OSError as err:
        print(f"Error opening file:{filename}problem{0}".format(err))

    return resultset, providerversion


def get_generic(search, verbosity, resultset, providerversion):
    """BGB query and extracts the CIDR blocks associated"""
    try:
        response = requests.get(GENERICAPIURL+search)
        if verbosity:
            print(response.status_code)
        if response.status_code == 200:
            rundate = datetime.datetime.utcnow()
            providerversion[search.upper()] = rundate.strftime('%Y/%m/%d %H:%M:%S')
            cidrdata = json.loads(response.content)
            for i in range(0, len(cidrdata["data"]["ipv4_prefixes"])):
                if cidrdata["data"]["ipv4_prefixes"][i]["prefix"] not in resultset:
                    resultset[cidrdata["data"]["ipv4_prefixes"][i]["prefix"]] = search
            for i in range(0, len(cidrdata["data"]["ipv6_prefixes"])):
                if cidrdata["data"]["ipv6_prefixes"][i]["prefix"] not in resultset:
                    resultset[cidrdata["data"]["ipv6_prefixes"][i]["prefix"]] = search
    except Exception as get_exception:
        print("Exception")
        print(get_exception)

    return resultset, providerversion


def sort_ip(ip):
    """ sort function for IPv4 and IPv6 CIDR ranges
        favors the biggest network first i.e. 1.2.3.0/24 comes after 1.2.0.0/16"""
    if "." in ip:
        return (int(ip.split("/")[1] or "0"),
                int(ip.split("/")[0].split(".")[0]),
                int(ip.split("/")[0].split(".")[1]),
                int(ip.split("/")[0].split(".")[2]),
                int(ip.split("/")[0].split(".")[3])
               )
    elif ":" in ip:
        return (int(ip.split("/")[1] or "0"),
                int(ip.split(":")[0],16),
                int(ip.split(":")[1],16),
                int(ip.split(":")[2] or "0",16)
               )
                

def print_resultset(start, resultset, providerversion):
    """prints the results gathered, and pre- and appends comment lines with version info"""
    # build a set of providers
    pcp = set() 
    for i in resultset:
        if resultset[i] not in pcp:
            pcp.add(resultset[i])

    # print all providers and their ranges in alphabetical order
    print(f"# Start run {start.strftime('%Y/%m/%d %H:%M:%S')}")
    for p in sorted(pcp):
        if p.upper() in providerversion:
            print(f"# {p} Start Versiondata: {providerversion[p.upper()]}")
        else:
            print(f"# {p} Start")
        for ip in sorted(resultset, key = sort_ip): 
            if p in resultset[ip]:
                print(ip)
        print(f"# {p} End")
    end = datetime.datetime.utcnow()
    print(f"# End run {end.strftime('%Y/%m/%d %H:%M:%S')}")

    

## main
if __name__ == '__main__':
    rs = {}
    pv = {}
    parser = argparse.ArgumentParser(description="Get IP address in CIDR form")
    parser.add_argument("-v", "--verbose", help="modify output verbosity", action="store_true")
    args = parser.parse_args()
    today = datetime.datetime.utcnow()
    rs, pv = get_aws(args.verbose, rs, pv)
    rs, pv = get_azure(args.verbose, rs, pv)
    rs, pv = get_gcp(rs, pv)
    rs, pv = get_oracle(args.verbose, rs, pv)
    rs, pv = get_generic("digitalocean", args.verbose, rs, pv)
    rs, pv = get_generic("ovh", args.verbose, rs, pv)
    rs, pv = get_file("alibaba", rs, pv)
    print_resultset(today, rs, pv)
