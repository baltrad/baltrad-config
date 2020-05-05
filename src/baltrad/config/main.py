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
  python_bin = sys.executable
  keytool = "keyczar.keyczart"
  if (sys.version_info > (3,0)):
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
  
  if args.questions:
    a.nodename = read_input("Node name", socket.gethostname())
    a.db_dbname = read_input("Database name", "baltrad")
    a.db_username = read_input("Database username", "baltrad")
    a.db_password = read_input("Database password", "baltrad")
    a.db_hostname = read_input("Database hostname", "localhost")

  a.write_config_file(args.conf)  

def get_current_user():
  return pwd.getpwuid(os.getuid())[0]

def execute_post_config(args):
  a=propertyhandler.propertyhandler()
  a.open_config_file(args.conf)

  uid = pwd.getpwnam("root").pw_uid

  if args.create_keys:
    if not os.path.exists(args.keys_root):
      os.makedirs(args.keys_root)
      if get_current_user() == "root":
        baltrad_uid = pwd.getpwnam(a.baltrad_user).pw_uid
        baltrad_gid = grp.getgrnam(a.baltrad_group).gr_gid
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
  
  a.write_bltnode_properties(args.bltnodefile)
  a.write_dex_properties(args.dexfile)
  a.write_dex_db_properties(args.dexdbfile)
  a.write_dex_fc_properties(args.dexfcfile)
  a.write_dex_beast_properties(args.dexbeastfile)
  a,write_tomcat_server_file(args.tomcatserverfile)
  if not args.no_rave_config:
    a.update_rave_defines(args.ravedefinesfile, args.bltnodefile)
  os.chmod(args.bltnodefile, 0o660)
  os.chmod(args.dexfile, 0o660)
  os.chmod(args.dexdbfile, 0o660)
  os.chmod(args.dexfcfile, 0o660)
  os.chmod(args.dexbeastfile, 0o660)
  os.chmod(args.tomcatserverfile, 0o660)
  
  # Change owner to root:baltrad
  uid = pwd.getpwnam("root").pw_uid
  baltrad_uid = pwd.getpwnam(a.baltrad_user).pw_uid
  baltrad_gid = grp.getgrnam(a.baltrad_group).gr_gid
  if get_current_user() == "root":
    os.chown(args.bltnodefile, uid, baltrad_gid)
    os.chown(args.dexfile, uid, baltrad_gid)
    os.chown(args.dexdbfile, uid, baltrad_gid)
    os.chown(args.dexfcfile, uid, baltrad_gid)
    os.chown(args.dexbeastfile, uid, baltrad_gid)
    os.chown(args.tomcatserverfile, uid, baltrad_gid)
    
    if not args.no_rave_config:
      os.chown(args.ravedefinesfile, baltrad_uid, baltrad_gid)
  else:
    print("WARNING! Could not change ownership of configuration files:")
    print("%s"%args.bltnodefile)
    print("%s"%args.dexfile)
    print("%s"%args.dexdbfile)
    print("%s"%args.dexfcfile)
    print("%s"%args.dexbeastfile)
    print("%s"%args.tomcatserverfile)
    if not args.no_rave_config:
      print("%s"%args.ravedefinesfile)
  
  if args.install_database or args.update_database:
    db = database.baltrad_database(args.bltnodefile, a.db_hostname, a.db_dbname, a.db_username, a.db_password, a.bdb_binaries, a.beast_sql_file_dir, a.dex_sql_file_dir)
    if args.install_database:
      db.create()
    if args.update_database:
      db.upgrade()

  if args.run_scripts:
    execute_post_config_scripts(a, args.conf)
  
def execute_post_config_scripts(ph, configfile):
  for script in ph.post_config_scripts:
    code = subprocess.call([sys.executable, script, configfile])
    if code != 0:
      print("Failed to run post script: %s"%script)

def run():
  parser = create_argparse("Creates initial configuration for the baltrad node packages")

  subparsers = parser.add_subparsers(help='the allowed commands')
  
  parser_init = subparsers.add_parser('init', help='creates initial configuration')
  parser_setup = subparsers.add_parser('setup', help='runs the setup of a node')

  parser_init.add_argument(
    "--conf=", dest="conf", default="/etc/baltrad/localhost.properties", help="the name of the configuration file to be created"
  )

  parser_init.add_argument(
    "--questions", dest="questions", action="store_true", help="if a number of questions should be asked, otherwise default values will be set at most places",
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
    "--dexbeastfile=", dest="dexbeastfile", default="/etc/baltrad/dex.beast.properties", help="Where the properties for dex beast should be written"
  )
  
  parser_setup.add_argument(
    "--ravedefinesfile=", dest="ravedefinesfile", default="/etc/baltrad/rave/Lib/rave_defines.py", help="Where rave_defines.py is located"
  )
  
  parser_setup.add_argument(
    "--tomcatserverfile=", dest="tomcatserverfile", default="/etc/baltrad/baltrad-node-tomcat/server.xml", help="Where the tomcat server.xml file is located"
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
  parser_setup.add_argument(
    "--create-keys", dest="create_keys", action="store_true", help="if the keystore and keyzcar keys should be generated",
  )

  parser_setup.add_argument(
    "--keys-root=", dest="keys_root", default="/etc/baltrad/bltnode-keys", help="location of all keys used during exchange"
  )
    
  parser_setup.add_argument(
    "--keystore=", dest="keystore_jks", default="/etc/baltrad/bltnode-keys/keystore.jks", help="location of the keystore"
  )
  
  parser_setup.add_argument(
    "--runscripts", dest="run_scripts", action="store_true", help="if the scripts should be executed")
  
  parser_init.set_defaults(func=create_initial_config)
  parser_setup.set_defaults(func=execute_post_config)
  
  args = parser.parse_args()
  
  args.func(args)
  

if __name__=="__main__":
  run()

