import logging
import logging.handlers
import os
import sys
import argparse
import socket
import string
import subprocess
import shutil
import pwd, grp

from baltrad.config import propertyhandler
from baltrad.config import database

if sys.version_info < (3,):
  import urlparse
else:
  import urllib.parse as urlparse

def read_input(msg, defaultvalue=None):
  if defaultvalue != None:
    msg = msg + " [default: %s]: "%defaultvalue
  if sys.version_info < (3,):
    d = raw_input(msg)
  else:
    d = input(msg)
  if len(d)==0 and defaultvalue != None:
    d = defaultvalue

  return d

logger = logging.getLogger("baltrad.config")

SYSLOG_ADDRESS = "/dev/log"
SYSLOG_FACILITY = "local3"

def excepthook(*exc_info):
  logger.error("unhandled exception", exc_info=exc_info)
  sys.exit(1)

def create_argparse(descr):
  return argparse.ArgumentParser(description=descr)

##
# Checks if the provided dir exists and if not creates it
# @param dir: the dir name
def createdir(dir):
  if not os.path.exists(dir):
    os.mkdir(dir)
  elif not os.path.isdir(dir):
    raise Exception("%s exists but is not a directory"%dir)
    
def create_keystore(keystore):
  kpwd=None
  while kpwd == None:
    kpwd=read_input("Keystore password: ")
    if len(kpwd) < 1:
      print("Must specify a keystore password")
      kpwd = None

  args = ["keytool", "-genkey", "-alias", "baltrad", "-keyalg", "RSA", "-validity", "3650", "-keypass", kpwd, "-storepass", kpwd, "-keystore", keystore]
  ocode = subprocess.call(args)
  if ocode != 0:
    raise Exception("keytool command failed for keystore creation")


def keyczar_tool(*module_args):
  python_bin = "python"
  keytool = "keyczar.keyczart"
  if (sys.version_info > (3,0)):
    python_bin = "python3"
    keytool = "keyczar.tool.keyczart"
  args = [python_bin, "-m", keytool]
  args.extend(module_args)
  ocode = subprocess.call(args)
  if ocode != 0:
    raise Exception("keytool command failed")

      
def create_priv_pub_keys(keys_root, nodename):
  priv_nodekey = "%s/%s.priv"%(keys_root, nodename)
  pub_nodekey = "%s/%s.pub"%(keys_root, nodename)
  if not os.path.exists(priv_nodekey):
    createdir(priv_nodekey)
    keyczar_tool("create",
                 "--location=%s" % priv_nodekey,
                 "--purpose=sign",
                 "--name=%s" % nodename,
                 "--asymmetric=dsa")
    keyczar_tool("addkey",
                 "--location=%s" % priv_nodekey,
                 "--status=primary")
  
  if not os.path.exists(pub_nodekey):
    createdir(pub_nodekey)
    keyczar_tool("pubkey",
                 "--location=%s" % priv_nodekey,
                 "--destination=%s" % pub_nodekey)               

def create_initial_config(args):
  a=propertyhandler.propertyhandler()
  
  uid = pwd.getpwnam("root").pw_uid
  baltrad_uid = pwd.getpwnam(a.baltrad_user).pw_uid
  baltrad_gid = grp.getgrnam(a.baltrad_group).gr_gid
    
  if not args.create_keys and not args.create_config:
    print("Must specify either --create-keys or --create-config when initializing configuration")
    sys.exit(127)
  
  if args.questions:
    a.nodename = read_input("Node name", socket.gethostname())
    a.db_dbname = read_input("Database name", "baltrad")
    a.db_username = read_input("Database username", "baltrad")
    a.db_password = read_input("Database password", "baltrad")
    a.db_hostname = read_input("Database hostname", "localhost")

  if args.create_keys:
    if not os.path.exists(args.keys_root):
      os.makedirs(args.keys_root)
      if get_current_user() == "root":
        os.chown(args.keys_root, baltrad_uid, baltrad_gid)

    if os.path.exists(args.keystore_jks):
      x = read_input("%s already exists, overwrite (y/n)?"%args.keystore_jks, "n")
      if x=="y":
        os.unlink(args.keystore_jks)

    if not os.path.exists(args.keystore_jks):
      create_keystore(args.keystore_jks)

    do_unlink_pub = False
    
    if os.path.exists("%s/%s.priv"%(args.keys_root, a.nodename)):
      x = read_input("%s/%s.priv already exists, overwrite (y/n)?"%(args.keys_root, a.nodename))
      if x=="y":
        shutil.rmtree("%s/%s.priv"%(args.keys_root, a.nodename), True)
        do_unlink_pub = True

    if os.path.exists("%s/%s.pub"%(args.keys_root, a.nodename)):
      if do_unlink_pub:
        x="y"
      else: 
        x = read_input("%s/%s.pub already exists, overwrite (y/n)?"%(args.keys_root, a.nodename))
      if x=="y":
        shutil.rmtree("%s/%s.pub"%(args.keys_root, a.nodename), True)

    create_priv_pub_keys(args.keys_root, a.nodename)

  a.keystore_jks = args.keystore_jks
  a.keystore_root = args.keys_root
  
  if args.create_config:
    a.write_config_file(args.conf)  

def get_current_user():
  return pwd.getpwuid(os.getuid())[0]

def execute_post_config(args):
  a=propertyhandler.propertyhandler()
  a.open_config_file(args.conf)
  
  a.write_bltnode_properties(args.bltnodefile)
  a.write_dex_properties(args.dexfile)
  a.write_dex_db_properties(args.dexdbfile)
  a.write_dex_fc_properties(args.dexfcfile)
  if not args.no_rave_config:
    a.update_rave_defines(args.ravedefinesfile, args.bltnodefile)
  os.chmod(args.bltnodefile, 0o660)
  os.chmod(args.dexfile, 0o660)
  os.chmod(args.dexdbfile, 0o660)
  os.chmod(args.dexfcfile, 0o660)
  
  # Change owner to root:baltrad
  uid = pwd.getpwnam("root").pw_uid
  baltrad_uid = pwd.getpwnam(a.baltrad_user).pw_uid
  baltrad_gid = grp.getgrnam(a.baltrad_group).gr_gid
  if get_current_user() == "root":
    os.chown(args.bltnodefile, uid, baltrad_gid)
    os.chown(args.dexfile, uid, baltrad_gid)
    os.chown(args.dexdbfile, uid, baltrad_gid)
    os.chown(args.dexfcfile, uid, baltrad_gid)
    if not args.no_rave_config:
      os.chown(args.ravedefinesfile, baltrad_uid, baltrad_gid)
  else:
    print("WARNING! Could not change ownership of configuration files:")
    print("%s"%args.bltnodefile)
    print("%s"%args.dexfile)
    print("%s"%args.dexdbfile)
    print("%s"%args.dexfcfile)
    if not args.no_rave_config:
      print("%s"%args.ravedefinesfile)
  
  if args.install_database or args.update_database:
    db = database.baltrad_database(args.bltnodefile, a.db_hostname, a.db_dbname, a.db_username, a.db_password, a.bdb_binaries, a.beast_sql_file_dir, a.dex_sql_file_dir)
    if args.install_database:
      db.create()
    if args.update_database:
      db.upgrade()

  #print(str(a))
  #print("execute_post_config")

def run():
  parser = create_argparse("Creates initial configuration for the baltrad node packages")

  subparsers = parser.add_subparsers(help='the allowed commands')
  
  parser_init = subparsers.add_parser('init', help='creates initial configuration')
  parser_setup = subparsers.add_parser('setup', help='runs the setup of a node')

  #parser.add_argument("init", help="creates initial configuration")
  
  #parser.add_argument("setup", help="Uses the setup configuration file to configure the node")

  parser_init.add_argument(
    "--conf=", dest="conf", default="/etc/baltrad/localhost.properties", help="the name of the configuration file to be created"
  )

  parser_init.add_argument(
    "--questions", dest="questions", action="store_true", help="if a number of questions should be asked, otherwise default values will be set at most places",
  )
  
  parser_init.add_argument(
    "--create-keys", dest="create_keys", action="store_true", help="if the keystore and keyzcar keys should be generated",
  )

  parser_init.add_argument(
    "--create-config", dest="create_config", action="store_true", help="if the default configuration file should be created",
  )

  parser_init.add_argument(
    "--keys-root=", dest="keys_root", default="/etc/baltrad/bltnode-keys", help="location of all keys used during exchange"
  )
    
  parser_init.add_argument(
    "--keystore=", dest="keystore_jks", default="/etc/baltrad/bltnode-keys/keystore.jks", help="location of the keystore"
  )
  
  parser_setup.add_argument(
    "--conf=", dest="conf", default="/etc/baltrad/localhost.properties", help="the name of the configuration file to be read"
  )

  parser_setup.add_argument(
    "--bltnodefile=", dest="bltnodefile", default="/etc/baltrad/bltnode.properties", help="Where the properties for bltnode should be written"
  )

  parser_setup.add_argument(
    "--dexfile=", dest="dexfile", default="/etc/baltrad/dex.properties", help="Where the properties for dex should be written"
  )

  parser_setup.add_argument(
    "--dexdbfile=", dest="dexdbfile", default="/etc/baltrad/db.properties", help="Where the properties for dex db should be written"
  )

  parser_setup.add_argument(
    "--dexfcfile=", dest="dexfcfile", default="/etc/baltrad/dex.fc.properties", help="Where the properties for dex fc should be written"
  )
  
  parser_setup.add_argument(
    "--ravedefinesfile=", dest="ravedefinesfile", default="/etc/baltrad/rave/Lib/rave_defines.py", help="Where rave_defines.py is located"
  )
  
  parser_setup.add_argument(
    "--no-rave-config", dest="no_rave_config", action="store_true", help="if rave defines file should be updated",
  )
  
  parser_setup.add_argument(
    "--install-database", dest="install_database", action="store_true", help="if the database install routines should be executed"
  )

  parser_setup.add_argument(
    "--upgrade-database", dest="update_database", action="store_true", help="if the database upgrade routines should be executed"
  )
  
  parser_init.set_defaults(func=create_initial_config)
  parser_setup.set_defaults(func=execute_post_config)
  
  args = parser.parse_args()
  
  args.func(args)
  

if __name__=="__main__":
  run()
  
# def create_backend(config):
#     type_ = config.get("baltrad.bdb.server.backend.type")
#     try:
#         backend_cls = backend.Backend.get_impl(type_)
#     except LookupError:
#         raise LookupError(
#             "unknown baltrad.bdb.server.backend.type: %s" % type_
#         )
#     return backend_cls.from_conf(config)
# 
# def read_config(conffile):
#     if not conffile:
#         raise SystemExit("configuration file not specified")
#     try:
#         return config.Properties.load(conffile)
#     except IOError:
#         raise SystemExit("failed to read configuration from " + conffile)
#    
# def run_create():
#     optparser = create_optparser()
# 
#     opts, args = optparser.parse_args()
#     config = read_config(opts.conffile)
# 
#     backend = create_backend(config)
#     backend.create()
# 
# def run_drop():
#     optparser = create_optparser()
# 
#     opts, args = optparser.parse_args()
# 
#     conf = read_config(opts.conffile)
# 
#     backend = create_backend(conf)
#     backend.drop()
# 
# def run_upgrade():
#     optparser = create_optparser()
# 
#     opts, args = optparser.parse_args()
# 
#     conf = read_config(opts.conffile)
# 
#     backend = create_backend(conf)
#     backend.upgrade()
# 
# def run_migrate_db():
#     optparser = create_optparser()
#     optparser.add_option(
#         "--from-storage", type="string", dest="from_storage", default="db", help="the from storage type (default db)",
#     )
#     optparser.add_option(
#         "--to-storage", type="string", dest="to_storage", default="fs", help="the storage type (default fs)",
#     )
#     
#     opts, args = optparser.parse_args()
#     
#     conf = read_config(opts.conffile)
#     
#     if conf.get("baltrad.bdb.server.backend.type") != "sqla":
#         raise Exception("current backend.type in configuration not set to sqla")
#     if opts.from_storage == opts.to_storage:
#         raise Exception("Cannot use same from and to storage type (%s)"%opts.from_storage)
#     
#     b = create_backend(conf)
# 
#     b.change_storage(conf, opts.from_storage, opts.to_storage)

# def get_logging_level(conf):
#     v = conf.get("baltrad.bdb.server.log.level", "INFO")
#     if v == "DEBUG":
#         return logging.DEBUG
#     elif v == "INFO":
#         return logging.INFO
#     elif v == "WARN":
#         return logging.WARN
#     elif v == "WARNING":
#         return logging.WARNING
#     elif v == "ERROR":
#         return logging.ERROR
#     else:
#         return logging.INFO
# 
# def configure_logging(opts, logtype, logid, level=logging.INFO):
#     logger = logging.getLogger()
#     logger.setLevel(level)
# 
#     default_formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
#     if opts.foreground or logtype == 'stdout':
#         handler = logging.StreamHandler(sys.stdout)
#         add_loghandler(logger, handler, default_formatter)
#     if opts.logfile:
#         handler = logging.FileHandler(opts.logfile)
#         add_loghandler(logger, handler, default_formatter)
#     if logtype == "syslog":
#         handler = logging.handlers.SysLogHandler(SYSLOG_ADDRESS, facility=SYSLOG_FACILITY)
#         formatter = logging.Formatter('python[' + logid + ']: %(name)s: %(message)s')
#         add_loghandler(logger, handler, formatter)
# 
#     
# def add_loghandler(logger, handler, formatter=None):   
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)

## Checks if the process with provided pid is running
# by checking the /proc directory.
# @param pid - the pid to check for
# @return True if a process with provided pid is running, otherwise False
# def isprocessrunning(pid):
#     return os.path.exists("/proc/%d"%pid)

# def run_server():
#     optparser = create_optparser()
#     optparser.add_option(
#         "--foreground", action="store_true",
#         default=False,
#         help="don't detach the process"
#     )
#     optparser.add_option(
#         "--logfile", type="path", action="store",
#         help="location of the log file",
#     )
#     optparser.add_option(
#         "--pidfile", type="path", action="store",
#         default="/var/run/baltrad-bdb-server.pid",
#         help="location of the pid file"
#     )
# 
#     opts, args = optparser.parse_args()
#     conf = read_config(opts.conffile)
# 
#     pidfile=TimeoutPIDLockFile(opts.pidfile, acquire_timeout=1.0)
# 
#     daemon_ctx = daemon.DaemonContext(
#         working_directory="/",
#         chroot_directory=None,
#         stdout=sys.stdout if opts.foreground else None,
#         stderr=sys.stderr if opts.foreground else None,
#         detach_process=not opts.foreground,
#         pidfile=pidfile
#     )
#     
#     server_type = conf["baltrad.bdb.server.type"]
#     if server_type not in ["cherrypy", "werkzeug"]:
#         raise SystemExit("invalid server type in config %s" % server_type)
#     
#     server_uri = conf["baltrad.bdb.server.uri"]
#     
#     # try locking the pidfile to report possible errors to the user
#     tryagain = False
#     try:
#         with pidfile:
#             pass
#     except lockfile.AlreadyLocked:
#         tryagain = True
#     except lockfile.LockFailed:
#         tryagain = True
#     except lockfile.LockTimeout:
#         tryagain = True
# 
#     if tryagain:
#         pid = lockfile.pidlockfile.read_pid_from_pidfile(opts.pidfile)
#         if pid != None and not isprocessrunning(pid):
#             try:
#                 message = "pidfile exists but it seems like process is not running, probably due to an uncontrolled shutdown. Resetting.\n"
#                 sys.stderr.write(message)
#                 os.remove(opts.pidfile)
#             except:
#                 pass
#     
#         try:
#             with pidfile:
#                 pass
#         except lockfile.AlreadyLocked:
#             raise SystemExit("pidfile already locked: %s" % opts.pidfile)
#         except lockfile.LockFailed:
#             raise SystemExit("failed to lock pidfile: %s" % opts.pidfile)
#         except lockfile.LockTimeout:
#             raise SystemExit("lock timeout on pidfile: %s" % opts.pidfile)
#             
#     with daemon_ctx:
#         logtype = conf.get("baltrad.bdb.server.log.type", "logfile")
#         logid = conf.get("baltrad.bdb.server.log.id", "baltrad.bdb.server")
#         configure_logging(opts, logtype, logid, get_logging_level(conf))
#         sys.excepthook = excepthook
#         application = app.from_conf(conf)
#         if server_type == "werkzeug":
#             app.serve(server_uri, application)
#         elif server_type == "cherrypy":
#             from cherrypy import wsgiserver
#             parsedurl = urlparse.urlsplit(server_uri)
#             cherryconf = conf.filter("baltrad.bdb.server.cherrypy.")
#             nthreads = cherryconf.get_int("threads", 10)
#             nbacklog = cherryconf.get_int("backlog", 5)
#             ntimeout = cherryconf.get_int("timeout", 10)            
#             server = wsgiserver.CherryPyWSGIServer((parsedurl.hostname, parsedurl.port), application,
#                 numthreads=nthreads, request_queue_size=nbacklog, timeout=ntimeout)
#             try:
#                 server.start()
#             finally:
#                 server.stop()

