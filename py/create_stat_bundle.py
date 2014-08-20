#!/opt/enr/virtupy/bin/python
import zipfile
import tempfile
import json
import sys
import os

import MySQLdb

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from common import *
from db import *

BUCKET='microput'

dbcon = None
s3con = None

def generateLocations(tmp_dir, dc_info):
    loc_s = ''
    for dc in dc_info:
        print "Processing %s..." % dc
        rbl = ""
        cbl = ""
        rwr = "";
        loc_s += "# %s (%s) \n" % (dc['dc_name'], dc['client_name'])
        loc_s += "location = /c%s/dc%s/ {\n" % (dc['client_id'], dc['dc_id'])
        loc_s += "\tlog_not_found off;\n";
        loc_s += "\texpires -1;\n";
        loc_s += "\troot /opt/enr/a/htdocs;\n";
        loc_s += "\taccess_log /opt/enr/log/c%s.dc%s.enr.log c%s_dc%s;\n" % (dc['client_id'], dc['dc_id'], dc['client_id'], dc['dc_id'])

        code = dc['http_code']
        code_type = dc['code_type']

        for p in dc['payload']:
            if p['do_unset'] == 'Y':
                pass
            else:
                rbl += "ngx.header['Set-Cookie'] = {'%s=%s;Domain=.opendsp.com;Path=/;Max-Age=%s;'}\n" % (p['name'],p['value'],p['expiry'])


        if code == 200:
            if code_type == 'image':
                print "Simple 1x1 pixel..."
                rwr = "\trewrite ^ /1x1.gif";
                rwr += "\tbreak;\n";
            else:
                payload_text = dc['payload_text']
                if not dc['payload_text']:
                    payload_text = "OK"
                    dc['ct'] = "text/html";
                payload_text = json.dumps(payload_text)
                print "Custom text."
                rbl += "ngx.header['Content-Type'] = \"%s\"\n" % dc['ct']
                cbl += 'ngx.say(%s)' % payload_text
                cbl += "\n"
        elif code in (301, 302):
            rwr = "rewrite ^ /bar redirect;\n";
            rwr += "break;\n";
        elif code == 204:
            pass

        rblfname = "rewrite_%s.lua" % dc['dc_id']
        rblfpath = tmp_dir + ("/lua/%s" % rblfname)
        rblf = open(rblfpath, 'w')
        rblf.write(rbl)
        rblf.close()

        loc_s += "\n\trewrite_by_lua_file /opt/enr/all/conf/lua/%s;\n"  % rblfname

        if cbl:
            cblfname = "content_%s.lua" % dc['dc_id']
            cblfpath = tmp_dir + ("/lua/%s" % cblfname)
            cblf = open(cblfpath, 'w')
            cblf.write(cbl)
            cblf.close()
            loc_s += "\n\tcontent_by_lua_file /opt/enr/all/conf/lua/%s;\n"  % cblfname
            loc_s += "\tbreak;\n";
            if rwr:
                print "!!! Rewrite section remaining, not writing: " + rwr
        else:
            loc_s += "\n\t" + rwr
            
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
    db_version = 0
    if not db_bundle:
        db_version = 0
    else:
        print "Bundle in DB: " +  str(db_bundle)
        db_version = db_bundle[0]
    print
    print "In DB: %s, on S3: %s" % (db_version, s3_version)

    if db_version < s3_version:
        print "I have no idea what's over there on S3..."
        
        
    dc_info = db.getDataCollectionInfo()

    tmp_dir = tempfile.mkdtemp('microput')
    os.mkdir(tmp_dir + "/lua")

    log_s = ''
    logdefs = db.getLogdefs()
    for l in logdefs:
        log_s += "\n# %s (%s)\n" % l[0:2]
        log_s += "log_format c%s_dc%s '%s';\n" % (l[2:])
    log_s += "\n"
    log_f = tmp_dir + "/nogit_logdefs.conf"
    fwrite(log_f, log_s)

    loc_s = generateLocations(tmp_dir, dc_info)
    loc_f = tmp_dir + "/nogit_locations.conf"
    fwrite(loc_f, loc_s)

    if db_bundle[1] == loc_s and db_bundle[2] == log_s:
        new_ver = db_version
    else:
        new_ver = db.addBundle(loc_s, log_s)

    if new_ver == s3_version:
        print "All up to date at version %s" % db_version
        sys.exit()

    bundle = "bundle%s.zip" % new_ver
    zfname = tmp_dir + ("/%s" % bundle)
    print "Creating %s for version %s" % (zfname, new_ver)
    zf = zipfile.ZipFile(zfname, 'w')
    add_to_zip(zf,loc_f, os.path.basename(loc_f))
    add_to_zip(zf,log_f, os.path.basename(log_f))
    
    lua_list = os.listdir(tmp_dir + "/lua")
    for lua_file in lua_list:
        lua_file = tmp_dir + "/lua/" + lua_file
        add_to_zip(zf, lua_file, "lua/" + os.path.basename(lua_file))

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
    
def add_to_zip(zf, f, arc):
    print "Adding %s as %s to %s" % (f, arc, zf)
    zf.write(f, arc)
    
    

    
    
        
    


if __name__ == "__main__":
    main()
