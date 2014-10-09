#!/opt/enr/virtupy/bin/python
# $Id$
import sys
import os
import time
import datetime
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from common import *



def problem(s):
    log(s)
    sys.exit(1)



def main():
    if len(sys.argv) == 1:
        log("Going over all files in %s" % LOG_DIR)
        log_file_list = os.listdir(LOG_DIR)
        for log_file in log_file_list:
            process_file(log_file)
    else:
        log_file = sys.argv[1]
        process_file(log_file)

def process_file(log_file):
    log("Processing %s" % log_file)
    inst_id = get_instance_id()
    d = parse_creds(CRED_FILE)
    conn = S3Connection(d['akey'], d['skey'])
    # TODO this should be configurable
    if not log_file.endswith('.%s' % COMPRESSION):
        log("Expected a %s file" % COMPRESSION)
        return
    
    # Files should be of the following format:
    # <user>.<table>.enr.log.<date>.<sec>.gz
    fparts = log_file.split('.')
    if len(fparts) != 7:
        log("Does not look like our log: %s" % log_file)
        return
    if fparts[2] != 'enr' or fparts[3] != 'log':
        log("Does not look like our log: %s" % log_file)
        return
    if len(fparts) != 7:
        log("Expected 7 parts in %s: <user>.<table>.enr.log.<date>.<time>.gz, but got %s" % (log_file, len(fparts)))
        return
    user = fparts[0]
    table = fparts[1]
    compression = fparts[6]
    
    try:
        year = fparts[4][0:4]
        month = fparts[4][4:6]
        day = fparts[4][6:8]
        sec = float(fparts[5])
        dt =  datetime.datetime.fromtimestamp(sec)
        # TODO - should we do extra check to match dt's y/m/d fields
        # with the once we got from fparts[4]?
        hour = dt.hour
        if hour < 10:
            hour = '0%s' % hour
    except Exception, e:
        log("Skipping %s: not our log: %s" % (log_file, e))
        return

    log_file_remote = "%s.%s.%s.%s.%s.log.%s" % (user, table, inst_id, fparts[4], fparts[5], compression)
    log_file_full = os.path.join(LOG_DIR, log_file)
    
    # Date first
    key_prefix = 'year=%s/month=%s/day=%s/hour=%s/user=%s/table=%s' % (year, month, day, hour, user, table)
    upload(conn, S3_BUCKET_DATE_FIRST, key_prefix, log_file_remote, log_file_full)


    # User first
    key_prefix = 'user=%s/table=%s/year=%s/month=%s/day=%s/hour=%s' % (user, table, year, month, day, hour)
    upload(conn, S3_BUCKET_USER_FIRST, key_prefix, log_file_remote, log_file_full)
    
    os.unlink(log_file_full)

def upload(conn, bucket_name, key_prefix, remote_name, local_name):
    bucket = conn.get_bucket(bucket_name)    
    k = Key(bucket)
    k.key = key_prefix  + "/" + remote_name
    log("In bucket %s, putting %s under %s" % (bucket_name, local_name, k.key))
    log(k.set_contents_from_filename(local_name))

             
if __name__ == "__main__":
    log("Starting upload process")
    main()
    log("Done")

