from common import *
import MySQLdb

class EnrDb(object):
    def __init__(self):
        d = parse_creds(CRED_FILE)
        self.host = d['mysql_host']
        self.db = d['mysql_db']
        self.user = d['mysql_user']
        self.passwd = d['mysql_passwd']
        self.con = None
        
    def connect(self, **kwargs):
        self.con = MySQLdb.connect(host=self.host,
                                   db=self.db,
                                   user=self.user,
                                   passwd=self.passwd,
                                   **kwargs)
        return self.con

    def runSql(self, sql):
        cur = self.con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return rows
    
    def getBucketForUser(self, user):
        # Internal things are always enremmeta
        return "s0.enremmeta.com"

    def getColsInfo(self):
        sql = """
             SELECT u.url_prefix, t.name tbl, 
             IF(ISNULL(c.name), CONCAT(mt.prefix, m.name), CONCAT(mt.prefix, c.name)) col
             FROM cols c
             JOIN tbls t ON c.tbl = t.id
             JOIN users u ON t.user = u.id
             LEFT JOIN macro_types mt ON mt.id = c.macro_type 
             LEFT JOIN macros m ON c.macro_type = m.macro_type AND c.macro = m.id
             ORDER BY u.id ASC, t.id ASC, c.id ASC;
             """
        cur = self.con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        retval = {}
        cur_url_prefix = None
        cur_tbl = None
        cur_cols = []
        for row in rows:
            prefix = row[0]
            tbl = row[1]
            col = row[2]
            if prefix == cur_url_prefix:
                # Same prefix as before
                if tbl == cur_tbl:
                    # Same table
                    cur_cols.append(col)
                    continue
                else:
                    # New table
                    if cur_tbl:
                        cur_prefix_dict[cur_tbl] = cur_cols
                    cur_cols = [col]
                    cur_tbl = tbl
                    continue
            else:
                # New prefix
                cur_cols.append(col)
                retval[prefix] = {}
                cur_url_prefix = prefix
                cur_prefix_dict = retval[prefix]
                continue
        if cur_tbl:
            cur_prefix_dict[cur_tbl] = cur_cols
        return retval
            
                
            
    

