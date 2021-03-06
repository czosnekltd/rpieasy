#!/usr/bin/env python3
#############################################################################
##################### INA219 plugin for RPIEasy #############################
#############################################################################
#
# Plugin based on library:
#  https://github.com/chrisb2/pi_ina219/
#
# Copyright (C) 2019 by Alexander Nagy - https://bitekmindenhol.blog.hu/
#
import plugin
import webserver
import rpieGlobals
import rpieTime
import misc
import gpios
from ina219 import INA219

class Plugin(plugin.PluginProto):
 PLUGIN_ID = 27
 PLUGIN_NAME = "Energy (DC) - INA219"
 PLUGIN_VALUENAME1 = "Voltage"
 PLUGIN_VALUENAME2 = "Current"
 PLUGIN_VALUENAME3 = "Power"

 def __init__(self,taskindex): # general init
  plugin.PluginProto.__init__(self,taskindex)
  self.dtype = rpieGlobals.DEVICE_TYPE_I2C
  self.vtype = rpieGlobals.SENSOR_TYPE_TRIPLE
  self.readinprogress = 0
  self.valuecount = 3
  self.senddataoption = True
  self.timeroption = True
  self.timeroptional = False
  self.formulaoption = True
  self._nextdataservetime = 0
  self.lastread = 0
  self.ina = None
  self.decimals = [3,3,3,0]

 def plugin_init(self,enableplugin=None):
  plugin.PluginProto.plugin_init(self,enableplugin)
  self.initialized = False
  if self.enabled:
   i2cport = -1
   try:
    for i in range(0,2):
     if gpios.HWPorts.is_i2c_usable(i) and gpios.HWPorts.is_i2c_enabled(i):
      i2cport = i
      break
   except:
    i2cport = -1
   if i2cport>-1:
    if self.interval>2:
      nextr = self.interval-2
    else:
      nextr = self.interval
    self._lastdataservetime = rpieTime.millis()-(nextr*1000)
    self.lastread = 0
    try:
     shunt = 0.1
     amps = int(self.taskdevicepluginconfig[1])
     if amps<1:
      amps = None
     vrange = int(self.taskdevicepluginconfig[2])
     if vrange not in [0,1]:
      vrange = 1
     if int(self.taskdevicepluginconfig[0])>0x39:
      self.ina = INA219(shunt,busnum=i2cport, address=int(self.taskdevicepluginconfig[0]), max_expected_amps=amps)
      self.ina.configure(voltage_range=vrange)
      self.initialized = True
    except Exception as e:
     misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"INA219 can not be initialized: "+str(e))
     self.ina = None
     self.initialized = False

 def webform_load(self): # create html page for settings
  choice1 = self.taskdevicepluginconfig[0]
  options = ["0x40","0x41","0x44","0x45"]
  optionvalues = [0x40,0x41,0x44,0x45]
  webserver.addFormSelector("I2C address","plugin_027_addr",len(options),options,optionvalues,None,int(choice1))
  webserver.addFormNote("Enable <a href='pinout'>I2C bus</a> first, than <a href='i2cscanner'>search for the used address</a>!")

  choice2 = self.taskdevicepluginconfig[1]
  options = ["AUTO","200","400","800","1000","1600","2000","3200"]
  optionvalues = [0,200,400,800,1000,1600,2000,3200]
  webserver.addFormSelector("Maximum current","plugin_027_amp",len(options),options,optionvalues,None,int(choice2))
  webserver.addUnit("mA")

  choice3 = self.taskdevicepluginconfig[2]
  options = ["32","16"]
  optionvalues = [1,0]
  webserver.addFormSelector("Max voltage","plugin_027_volt",len(options),options,optionvalues,None,int(choice3))
  webserver.addUnit("V")

  choice4 = self.taskdevicepluginconfig[3]
  options = ["None","Voltage","Current","Power"]
  optionvalues = [0,1,2,3]
  webserver.addFormSelector("Param1","plugin_027_p1",len(options),options,optionvalues,None,int(choice4))
  choice5 = self.taskdevicepluginconfig[4]
  webserver.addFormSelector("Param2","plugin_027_p2",len(options),options,optionvalues,None,int(choice5))
  choice6 = self.taskdevicepluginconfig[5]
  webserver.addFormSelector("Param3","plugin_027_p3",len(options),options,optionvalues,None,int(choice6))
  return True

 def webform_save(self,params): # process settings post reply
  par = webserver.arg("plugin_027_addr",params)
  if par == "":
    par = 0x40
  self.taskdevicepluginconfig[0] = int(par)

  par = webserver.arg("plugin_027_amp",params)
  if par == "":
    par = 0
  self.taskdevicepluginconfig[1] = int(par)

  par = webserver.arg("plugin_027_volt",params)
  if par == "":
    par = 1
  self.taskdevicepluginconfig[2] = int(par)

  par = webserver.arg("plugin_027_p1",params)
  if par == "":
    par = 1
  self.taskdevicepluginconfig[3] = int(par)
  par = webserver.arg("plugin_027_p2",params)
  if par == "":
    par = 0
  self.taskdevicepluginconfig[4] = int(par)
  par = webserver.arg("plugin_027_p3",params)
  if par == "":
    par = 0
  self.taskdevicepluginconfig[5] = int(par)

  self.vtype = rpieGlobals.SENSOR_TYPE_TRIPLE
  if self.taskdevicepluginconfig[5]==0:
   self.vtype = rpieGlobals.SENSOR_TYPE_DUAL
  if self.taskdevicepluginconfig[4]==0:
   self.vtype = rpieGlobals.SENSOR_TYPE_SINGLE

  return True

 def plugin_read(self): # deal with data processing at specified time interval
  result = False
  if self.enabled and self.initialized and self.readinprogress==0:
   self.readinprogress = 1
   try:
    v1 = None
    if self.ina is not None:
     for i in range(0,3):
      vtype = self.taskdevicepluginconfig[3+i]
      if vtype==1:
       self.set_value(i+1,self.ina.supply_voltage(),False)
      elif vtype==2:
       self.set_value(i+1,float(self.ina.current()/1000),False)
       v1 = 1
      elif vtype==3:
       self.set_value(i+1,float(self.ina.power()/1000),False)
       v1 = 1
   except Exception as e:
    v1 = None
    misc.addLog(rpieGlobals.LOG_LEVEL_ERROR,"INA219: "+str(e))
   if v1 is not None:
    self.plugin_senddata()
   self._lastdataservetime = rpieTime.millis()
   result = True
   self.readinprogress = 0
  return result

