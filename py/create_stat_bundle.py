import zipfile
import tempfile
import json
import sys

import MySQLdb

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from common import *
from db import *

BUCKET='microput'

dbcon = None
s3con = None

def generateLocations(dc_info):
    loc_s = ''
    for dc in dc_info:
        rbl = ""
        cbl = ""
        rwr = "";
        loc_s += "# %s (%s) \n" % (dc['dc_name'], dc['client_name'])
        loc_s += "/c%s/dc%s/ {\n" % (dc['client_id'], dc['dc_id'])
        loc_s += "log not found off;\n";
        loc_s += "expires -1;\n";
        loc_s += "root /opt/enr/a/htdocs;\n";
        loc_s += "access_log /opt/enr/log/c%s.dc%s.enr.log c%s_dc%s;\n" % (dc['client_id'], dc['dc_id'], dc['client_id'], dc['dc_id'])

        code = dc['http_code']
        code_type = dc['code_type']

        for p in dc['payload']:
            if p['do_unset'] == 'N':
                pass
            else:
                rbl += "ngx.header['Set-Cookie'] = {'%s=%s;Domain=.opendsp.com;Path=/;Max-Age=%s;'}\n" % (p['name'],p['value'],p['expiry'])
        
        if code == 200:
            if code_type == 'image':
                rwr = "rewrite ^ /1x1.gif break;\n";
            else:
                payload_text = dc['payload_text']
                if not dc['payload_text']:
                    payload_text = "OK"
                    dc['ct'] = "text/html";
                payload_text = json.dumps(payload_text)
                rbl += "ngx.header['Content-Type'] = \"%s\"\n" % dc['ct']
                cbl += 'ngx.say(%s)' % payload_text
                cbl += "\n"
        elif code in (301, 302):
            rwr = "rewrite ^ /bar redirect;\n";
            rwr += "break;\n";
        elif code == 204:
            pass

        loc_s += "\n" + 'rewrite_by_lua "' + "\n";
        loc_s += rbl 
        loc_s += '";' + "\n";

        loc_s += "\n" + 'content_by_lua "' + "\n";
        loc_s += cbl
        loc_s += '";' + "\n";

        loc_s += "\n" + rwr

        loc_s += "}\n\n"
        return loc_s

def fwrite(fname, s):
    f = open(fname, "w")
    print "Wrting to %s " % fname
    f.write(s)
    f.close()


def main():
    global s3con, dbcon
    d = parse_creds(CRED_FILE)
    db = EnrDb()
    db.connect()
    s3con = S3Connection(d['akey'], d['skey'])
    bucket = s3con.get_bucket(CONFIG_BUCKET)
    k = Key(bucket)
    k.key = "VERSION.TXT"
    # help(k)
    s3_version = int(k.get_contents_as_string().strip())
    db_bundle = db.getLatestBundle()
    print db_bundle
    if not db_bundle:
        db_version = 0
    else:
        pass
    print "In DB: %s, on S3: %s" % (db_version, s3_version)

    if db_version == s3_version:
        print "All up to date at version %s" % db_version
        sys.exit()
    if db_version < s3_version:
        print "I have no idea what's over there on S3..."
        
        
    dc_info = db.getDataCollectionInfo()
    print 'DATA COLLECTIONS'
    print dc_info

    tmp_dir = tempfile.mkdtemp('microput')

    log_s = ''
    logdefs = db.getLogdefs()
    for l in logdefs:
        log_s += "# \n" 
        log_s += "log_format c%s_dc%s %s;\n" % l
    log_f = tmp_dir + "/nogit_logdefs.conf"
    fwrite(log_f, log_s)

    loc_s = generateLocations(dc_info)
    loc_f = tmp_dir + "/nogit_locations.conf"
    fwrite(loc_f, loc_s)
    
    new_ver = db.addBundle(loc_s, log_s)

    bundle = "bundle%s.zip" % new_ver
    zfname = tmp_dir + ("/%s" % bundle)
    print "Creating %s for version %s" % (zfname, new_ver)
    zf = zipfile.ZipFile(zfname, 'w')
    zf.write(loc_f)
    zf.write(log_f)
    zf.close()
    
    s3con = S3Connection(d['akey'], d['skey'])
    bucket = s3con.get_bucket(CONFIG_BUCKET)
    k = Key(bucket)
    k.key = "VERSION.TXT"
    print "Changing version on S3"
    k.set_contents_from_string(new_ver)

    print "Uploading bundle"
    k.key = "bundles/" + bundle
    k.set_contents_from_filename(zfname)
    print "Done!"
    
    
    

    
    
        
    


if __name__ == "__main__":
    main()
