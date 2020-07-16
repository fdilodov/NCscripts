# NCscripts
The nxget.py script is a command-line application to download data from NextCloud. It's written in Python and makes use of the NextCloud webdav API.

## Installation
The script is written in python3 and only makes use of the requests package. If you do not have write access to your main python installation, or you do not want to add packages to your system
installation you can create a user python installation:

```
python3 -m venv env
source ./env/bin/activate
pip install -r requirements.txt
```

This should result in your local python3 being ready to use.

## Usage

```
nxget.py -h -v [-l <output-files>] [[-f <input-files>] -g <local folder>] -a <username>:<pass> -s <since-date> -u <until-date> -o <nextcloud file> <nextcloud folder>

Arguments:
<nextcloud folder>       The NextCloud folder containing the data. The argument is not needed if the '-f' option is used with '-g'.
                         Or, if the '-o' option is used.

Options
-h                       Print this help.
-v                       Print verbose output.
-o <nextcloud file>      Download <nextcloud file> from NextCloud. This must be a single file.
-l <output-files>        Print the list of files in the folder to the output-files JSON file.
-f <input-files>         Use as input the JSON file list of files to download.
-g <local folder>        Download the files to the local folder.
-a <username>:<pass>     Username and password for the account.
-s <since-date>          Select files modified starting from and including this date. Format: YYYY-MM-DD
-u <until-date>          Select files modified before and including this date. Format: YYYY-MM-DD
```

The script can be used in 3 modes:

### To get a list of files to download

```
./nxget.py -l output_files.json -a username:pass https://nextcloud/user/folder
```

This will result in a JSON file *output_files.json* to be created with the list of files to download in the folder *https://nextcloud/user/folder*. The script will contain files in that directory and all files in subdirectories.

You can use the `-s` (since) and `-u` (until) options to restrict the listing to certain date ranges. The format for the dates is *YYYY-MM-DD*. *Note* if you want to get the files on a particular day (eg 10 Mar 2020) then you need to specify `-s 2020-03-10 -u 2020-03-11` as the dates are taken from 00:00 on that day.


### To download a list of files

```
./nxget.py -f output_files.json -a username:pass -g somedir
```

This will download the files contained in the JSON file *output_files.json* into the directory *somedir*. Depending on the network it can take sometime to complete. If the download fails part-way through you can re-run the script. It will skip the successful downloads and only download files that have an incorrect filesize (according to the file size metadata information in the JSON file). 

### To download files belonging to a folder
Instead of first getting a list of files and then downloading the list you can run the script to
perform both tasks in one go.

```
./nxget.py -g somedir -a username:pass https://nextcloud/user/folder
```

This will download all the files in the folder *https://nextcloud/user/folder* and in subfolders and store the files under the directory *somedir*. This may be more convenient if you have a 
good network connection.

### To download an individual file
You can download a single file using the command:

```
./nxget.py -g somedir -a username:pass -o https://nextcloud/user/folder/file.dat
```

This will download the file *https://nextcloud/user/folder/file.dat* into the directory *somedir*. 

