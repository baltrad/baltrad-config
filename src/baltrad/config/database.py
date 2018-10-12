'''
Copyright (C) 2018- Swedish Meteorological and Hydrological Institute (SMHI)

This file is part of baltrad-config.

baltrad-config is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

baltrad-config is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with baltrad-config.  If not, see <http://www.gnu.org/licenses/>.
'''
import sys, os, subprocess, tempfile, re
#import shutil
#import jprops
import psycopg2, psycopg2.extensions
import traceback

##
# The class that provides support for creating, upgrading and dropping all
# tables associated with baltrad
#
class baltrad_database(object):
  #_prefix = None
  #_propertyfile = None
  #_username=None
  #_password=None
  #_hostname=None
  #_dbname=None

  ##
  # Constructor
  # @param prefix: bdb-binary-folder root
  # @param propertyfile: the property file used by baltrad-bdb-client
  # @param hostname: the host name of the database
  # @param dbname: the name of the database
  # @param username: the user owning the database
  # @param password: the password for the user
  def __init__(self, propertyfile, hostname, dbname, username, password, bdbbins="/usr/bin", beast_sql="/opt/baltrad/baltrad-beast/sql", dex_sql="/opt/baltrad/baltrad-dex/sql"):
    self._propertyfile = propertyfile
    self._hostname = hostname
    self._dbname = dbname
    self._username = username
    self._password = password
    self._bdb_binaries = bdbbins
    self._beast_sql = beast_sql
    self._dex_sql = dex_sql

  ##
  # Creates the database tables
  #
  def create(self):
    try:
      self._create_bdb()
    except Exception as e:
      traceback.print_exc(e)
    try:
      self._create_beast()
    except Exception as e:
      traceback.print_exc(e)
    try:
      self._create_dex()
    except Exception as e:
      traceback.print_exc(e)

  ##
  # Upgrades the database tables
  #
  def upgrade(self):
    try:
      self._upgrade_bdb()
    except Exception as e:
      traceback.print_exc(e)
    try:
      self._upgrade_beast()
    except Exception as e:
      traceback.print_exc(e)
    try:
      self._upgrade_dex()
    except Exception as e:
      traceback.print_exc(e)

  ##
  # Updates the admin users password
  def update_admin_password(self, password):
    connection = psycopg2.connect("host=%s dbname=%s user=%s password=%s"%(self._hostname,self._dbname,self._username,self._password))
    try:
      dbcursor = connection.cursor()
      dbcursor.execute("UPDATE dex_users SET PASSWORD=MD5('"+password+"') WHERE name='admin'")
      connection.commit()
    except psycopg2.DatabaseError as e:
      raise Exception("Failed to run baltrad %s db scheme, e: %s"%(id, e.__str__()))
    finally:
      if dbcursor:
        dbcursor.close()
      if connection:
        connection.close()
    
  ##
  # Creates the bdb tables
  def _create_bdb(self):
    cmd = "%s/baltrad-bdb-create"%self._bdb_binaries
    conf = "--conf=%s"%self._propertyfile
    ocode = subprocess.call([cmd, conf])
    if ocode != 0:
      raise Exception("Failed to create baltrad bdb")
  
  ##
  # Upgrades the bdb tables
  def _upgrade_bdb(self):
    cmd = "%s/baltrad-bdb-upgrade"%self._bdb_binaries
    conf = "--conf=%s"%self._propertyfile
    ocode = subprocess.call([cmd, conf])
    if ocode != 0:
      raise Exception("Failed to create baltrad bdb")
  
  ##
  # Creates the beast tables
  def _create_beast(self):
    self._run_sql_script("%s/create_db.sql"%self._beast_sql, "create beast")

  ##
  # Upgrades the beast tables
  def _upgrade_beast(self):
    self._run_sql_script("%s/upgrade_db.sql"%self._beast_sql, "upgrade beast")

  ##
  # Creates the dex tables
  def _create_dex(self):
    self._run_sql_script("%s/create_dex_schema.sql"%self._dex_sql, "create dex")
    self._run_sql_script("%s/insert_default_dex_data.sql"%self._dex_sql, "create dex data")

  ##
  # Upgrades the dex tables 
  def _upgrade_dex(self):
    self._run_sql_script("%s/upgrade_dex_schema.sql"%self._dex_sql, "upgrade dex")
  
  ##
  # Runs the specified sql script. The id is just used for identifying what is beeing run
  # @param scriptname: The filename of the sql script to be executed
  # @param id: The id to be used in the error messages
  def _run_sql_script(self, scriptname, id):
    sql = open(scriptname, 'r').read()
    hostname=self._hostname
    portnr="5432"
    if self._hostname.find(":") > 0:
      hostname = self._hostname[0:self._hostname.find(":")]
      portnr = self._hostname[self._hostname.find(":")+1:]
      
    connection = psycopg2.connect("host=%s port=%s dbname=%s user=%s password=%s"%(hostname,portnr,self._dbname,self._username,self._password))
    try:
      dbcursor = connection.cursor()
      dbcursor.execute(sql)
      connection.commit()
    except psycopg2.DatabaseError as e:
      raise Exception("Failed to run baltrad %s db scheme, e: %s"%(id, e.__str__()))
    finally:
      if dbcursor:
        dbcursor.close()
      if connection:
        connection.close()
