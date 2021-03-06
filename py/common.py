from copy import deepcopy
import os
from nogit_constants import *

from string import ascii_letters, digits
import boto
from subprocess import Popen

ENR_HOME = '/opt/enr'

CRED_FILE = ENR_HOME + '/skak/skak.ini'

LOG_DIR = ENR_HOME + '/log'

CONF_DIR = ENR_HOME + '/all/conf'

COMPRESSION = "gz"

def run_cmd(cmd):
    log("Executing %s" % cmd)
    p = Popen(cmd)
    (out, err) = p.communicate()
    stdout = ""
    stderr = ""
    if out:
        for l in out:
            stdout += l + "\n"
    if err:
        for l in err:
            stderr += l + "\n"
    exit_code = p.wait()
    return (exit_code, stdout, stderr)

CREDS = None

CONFIG_BUCKET='bin.opendsp.com'
       
def parse_creds(cred_file):
    global CREDS
    if CREDS:
        return CREDS
    d = {}
    creds = open(cred_file)
    for line in creds:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            print 'Ignoring line %s' % line
            continue
        try:
            (key,value) = line.split('=',1)            
        except Exception, e:
            print 'Ignoring line %s: %s' % (line, e)
            continue
        d[key] = value
    creds.close()
    CREDS = deepcopy(d) 
    return d

CREDS = parse_creds(CRED_FILE)

def list_regions():
    regions = boto.ec2.regions(aws_access_key_id=CREDS['akey'],
                               aws_secret_access_key=CREDS['skey'])
    return regions

def list_node_ids():
    regions = list_regions()
    instances = {}
    all_elbs = []
    region_names = [region.name for region in regions]
    # For now we know we're just in US west...
    region_names = ['us-west-1']
    for region_name in region_names:
        # log("Connecting to %s" % region_name)
        elb_con = boto.ec2.elb.connect_to_region(region_name,
                                                  aws_access_key_id=CREDS['akey'], 
                                                  aws_secret_access_key=CREDS['skey'])
        if not elb_con:
            continue
        reg_elbs = elb_con.get_all_load_balancers()
        for elb in reg_elbs:
            if not elb.name in ELB_NAMES:
                continue
            cur_inst_list = elb_con.describe_instance_health(elb.name)
            inst_id_list = [inst.instance_id for inst in cur_inst_list]
            if region_name not in instances:
                instances[region_name] = []
            instances[region_name].extend(inst_id_list)
    return instances

def validate_enr_ident(s):
    return all(c in ascii_letters + digits for c in s)

def validate_enr_colname(s):
    # TODO
    # This should properly check that everything is allowed
    # but for now it's ok
    return all(c in ascii_letters + "_" + digits for c in s)

def log(s):
    from datetime import datetime
    msg = "%s %s" % (datetime.now(), s)
    print msg 
    log_fname = os.path.join(LOG_DIR, "misc.log")
    f = open(log_fname, "a")
    f.write(msg)
    f.write("\n")
    f.close()

AWS_INSTANCE_ID = None

def get_instance_id():
    import urllib2
    global AWS_INSTANCE_ID
    #  wget -q -O - 
    if not AWS_INSTANCE_ID:
        response = urllib2.urlopen('http://169.254.169.254/latest/meta-data/instance-id')
        inst_id = response.read()
        inst_id = inst_id.strip()
        AWS_INSTANCE_ID = inst_id
    return AWS_INSTANCE_ID

