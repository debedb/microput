#!/opt/enr/virtupy/bin/python
import tempfile
import zipfile
import os

from boto.s3.connection import S3Connection
from boto.s3.key import Key
import MySQLdb

import sys
from common import *

dbcon = None
s3con = None

def main():
    d = parse_creds(CRED_FILE)
    s3con = S3Connection(d['akey'], d['skey'])
    bucket = s3con.get_bucket(CONFIG_BUCKET)
    k = Key(bucket)
    k.key = "VERSION.TXT"
    # help(k)
    version = int(k.get_contents_as_string().strip())
    try:
        with open(ENR_HOME + '/all/conf/VERSION.TXT') as f:
            cur_version = int(f.read().strip())
    except IOError, e:
        if e.errno == 2:
            cur_version = 0
        else:
            raise
    print 'Comparing %s to %s' % (version, cur_version)
    if cur_version == version:
        print "Up-to-date, bye."
        sys.exit()
    if cur_version > version:
        print "We have greater version than bundle. That's weird. Won't do anything."
        sys.exit()
    print "Upgrading %s to %s..." % (cur_version, version)
    if not os.path.exists('/tmp/bundles'):
        os.mkdir('/tmp/bundles')
    b = "bundles/bundle%s.zip" % version
    bfname = "/tmp/%s" % b
    bz = open(bfname, "w")
    print "Fetching version %s from %s into %s" % (version, b, bz)
    k.key = b
    k.get_contents_to_file(bz)
    bz.close()

    conf_dir = ENR_HOME + '/all/conf'
    print "Changing directory to %s" % conf_dir
    os.chdir(conf_dir)
    print "Unzipping %s into %s" % (bfname, conf_dir)
    zf = zipfile.ZipFile(bfname, 'r')
    zf.extractall(conf_dir)
    print "Reloading nginx"
    (exit_code, out,err) = run_cmd(['/sbin/service','nginx','reload'])
    print out
    print err
    print "Error code: %s" % exit_code
    if exit_code:
        print "Rolling back...."
    sys.exit(exit_code)

if __name__ == "__main__":
    print
    print '================================================='
    main()
