#!/usr/bin/env python3

import getopt
import os
import sys
import json
import datetime
import urllib.parse
import xml.etree.ElementTree
import requests

def help_opts():
    '''Script help'''
    print("nxcget.py -h [-l <output-files>] [[-f <input-files>] -g <local folder>] -a <username>:<pass> -s <since-date> -u <until-date> -o <nextcloud file> <nextcloud folder>")
    print("arguments:")
    print("<nextcloud folder>       The NextCloud folder containing the data. The argument")
    print("                         is not needed if the '-f' option is used with '-g'.")
    print("                         Or, if the '-o' option is used.")
    print("")
    print("options:")
    print("-h                       Print this help.")
    print("-l <output-files>        Print the list of files in the folder to the output-files JSON file.")
    print("-f <input-files>         Use as input the JSON file list of files to download.")
    print("-g <local folder>        Download the files to the local folder.")
    print("-a <username>:<pass>     Username and password for the account.")
    print("-s <since-date>          Select files modified starting from and including this date. Format: YYYY-MM-DD")
    print("-u <until-date>          Select files modified before and including this date. Format: YYYY-MM-DD")
    print("")


def get_resource(node, HOST, since_date, until_date):
    '''Extract the resources from the response node'''
    resource = {}
    discard_resource_1 = False
    discard_resource_2 = False

    for child in list(node):
        if child.tag == "{DAV:}href":
            resource["path"] = HOST + child.text.strip()
        elif child.tag == "{DAV:}propstat":
            status_node = child.find("{DAV:}status")
            if "200 OK" in status_node.text:
                prop_node = child.find("{DAV:}prop")
                collection_node = prop_node.find("{DAV:}resourcetype").find("{DAV:}collection")
                if collection_node is not None:
                    resource["type"] = "collection"
                    resource["size"] = 0
                    resource["lastmodified"] = "2000-01-01"
                else:
                    resource["type"] = "file"
                    resource["size"] = int(prop_node.find("{DAV:}getcontentlength").text)
                    date_obj = datetime.datetime.strptime(prop_node.find("{DAV:}getlastmodified").text,
                            "%a, %d %b %Y %H:%M:%S %Z")
                    if since_date and date_obj < since_date:
                        discard_resource_1 = True
                    if until_date and date_obj > until_date:
                        discard_resource_2 = True
                    resource["lastmodified"] = date_obj.strftime("%Y-%m-%d")

    if discard_resource_1 or discard_resource_2:
        resource = {}

    return resource


def list_data(user, upass, next_folder, HOST, since_date, until_date):
    '''Find and return the list of files and folders in the given folder'''
    resources = []

    session = requests.Session()
    session.auth = (user, upass)
    request = requests.Request("PROPFIND", next_folder)
    prep_req = session.prepare_request(request)
    response = session.send(prep_req)
    if response.status_code == 207:
        root_node = xml.etree.ElementTree.fromstring(response.text)
        for child in root_node:
            resource = {}
            if child.tag == "{DAV:}response":
                resource = get_resource(child, HOST, since_date, until_date)
                if (resource and resource["type"] == "collection"
                        and resource["path"][0:-1] != next_folder):
                    new_folder = resource["path"][0:-1]
                    resources = resources + list_data(user, upass,
                                                      new_folder, HOST,
                                                      since_date,
                                                      until_date)
                else:
                    if resource:
                        resources.append(resource)

    return resources


def get_data(user, upass, output_dir, ORIG_PATH,
             since_date, until_date, resources, verbose):
    '''Get the data from the given folder'''

    # Loop over the resources getting the output and storing in a file on disk
    for resource in resources:
        if verbose:
            print("Processing: ", resource)
        if resource["type"] == "file":
            download = True
            url = urllib.parse.urlparse(resource["path"])
            rel_file_path = os.path.relpath(url.path, ORIG_PATH)
            rel_dir = os.path.dirname(rel_file_path)
            out_dir = os.path.join(output_dir, rel_dir)
            out_file = os.path.join(output_dir, rel_file_path)
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir)

            if os.path.isfile(out_file):
                stat_file = os.stat(out_file)
                if stat_file.st_size == resource["size"]:
                    download = False

            if since_date or until_date:
                res_date = datetime.datetime.strptime(resource["lastmodified"], "%Y-%m-%d")
                if since_date and res_date < since_date:
                    download = False
                if until_date and res_date > until_date:
                    download = False

            if download:
                download_file(user, upass, resource["path"], out_file, verbose)


def download_file(user, upass, infile, outfile, verbose):
    if verbose:
        print("downloading ", infile)
    session = requests.Session()
    session.auth = (user, upass)
    response = session.get(infile, stream=True)
    response.raise_for_status()
    with open(outfile, 'wb') as fout:
        for chunk in response.iter_content(chunk_size=8192):
            fout.write(chunk)



if __name__ == "__main__":
    error_flag = False
    infile_flag = False
    get_flag = False
    list_flag = False
    user = ""
    upass = ""
    output_file = ""
    NEXT_FOLDER = ""
    since = ""
    until = ""
    verbose = False
    since_date = None
    until_date = None
    onefile = False
    input_file = ""


    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:], "hvl:g:a:f:s:u:o:",
                                   ["list=", "files=", "get=", "auth=",
                                    "since=", "until=", "onefile="])
    except getopt.GetoptError:
        print("nxcget.py -h -v [[-l <output-files>] [[-f <input-files>] -g <local folder>] -a <username>:<pass> -s <since-date> -u <until-date> <nextcloud folder>][-o <nextcloud file>]")
        sys.exit(2)

    for opt, arg in OPTS:
        if opt == "-h":
            help_opts()
        elif opt in ("-a", "auth"):
            user, upass = arg.split(":")
            user = user.strip()
            upass = upass.strip()
        elif opt in ("-f"):
            infile_flag = True
            input_file = arg
        elif opt in ("-g", "get"):
            get_flag = True
            output_dir = arg
        elif opt in ("-l", "list"):
            list_flag = True
            output_file = arg
        elif opt in ("-s", "since"):
            since = arg
        elif opt in ("-u", "until"):
            until = arg
        elif opt == "-v":
            verbose = True
        elif opt in ("-o", "onefile"):
            onefile = True
            input_file = arg
    
    if onefile and get_flag:
        download = True
        out_dir = os.path.join(output_dir)
        out_file = os.path.join(output_dir, os.path.basename(input_file))
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)

        if os.path.isfile(out_file):
            stat_file = os.stat(out_file)
            if stat_file.st_size == input_file:
                download = False
        if download:
            download_file(user, upass, input_file, out_file, verbose)
        sys.exit(0)

    if len(ARGS) != 1 and not infile_flag:
        error_flag = True
    else:
        if not infile_flag:
            NEXT_FOLDER = ARGS[0]

    if infile_flag and len(ARGS) > 0:
        error_flag = True

    if since:
        try:
            since_date = datetime.datetime.strptime(since, "%Y-%m-%d")
        except ValueError:
            print("Date must be in YYYY-MM-DD format (e.g. 2020-03-20")
            sys.exit(3)

    if until:
        try:
            until_date = datetime.datetime.strptime(until, "%Y-%m-%d")
        except ValueError:
            print("Date must be in YYYY-MM-DD format (e.g. 2020-03-20")
            sys.exit(3)

    if since_date and until_date and since_date > until_date:
        print("Since date cannoe be greater than Until date.")
        sys.exit(4)

    URL = urllib.parse.urlparse(NEXT_FOLDER)
    HOST = URL.scheme + "://" + URL.netloc
    ORIG_PATH = URL.path

    if infile_flag and not get_flag:
        error_flag = True
    if infile_flag and list_flag:
        error_flag = True
    if list_flag and (get_flag or infile_flag):
        error_flag = True
    if get_flag and list_flag:
        error_flag = True

    if error_flag:
        print("nxcget.py -h [-l <output-files>] [[-f <input-files>] -g <local folder>] -a <username>:<pass> -s <since-date> -u <until-date> <nextcloud folder>")
        sys.exit(2)
 
    if infile_flag:
        with open(input_file, "r") as fin:
            input_json = json.load(fin)
        FILES = input_json["resources"]
        ORIG_PATH = input_json["root_path"]
    else:
        FILES = list_data(user, upass, NEXT_FOLDER, HOST,
                          since_date, until_date)

    if list_flag and not infile_flag and not get_flag:
        files_only = [x for x in FILES if x["type"] == "file"]
        file_resources = {"total": len(files_only),
                          "root_path": ORIG_PATH,
                          "resources": files_only}
        with open(output_file, "w") as fout:
            json.dump(file_resources, fout)


    if get_flag and not list_flag:
        get_data(user, upass, output_dir, ORIG_PATH, since_date,
                 until_date, FILES, verbose)
