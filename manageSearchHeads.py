# *********************************************
#
# This python code is an example of managing remote Splunk Search Heads using the REST interface.
# It uses standard python config files to drive which search heads are managed and what endpoints
# to configure.  This represents a simple implementation of the concept and has minimal error
# handling and is definitely not ready for a production environment.
#
# Authors:  Jason Hupka & Kevin Kalmbach
#
# *********************************************
import urllib2;
from urllib import urlencode;
import base64;
import sys;
import socket;
import datetime;
import random;
import ConfigParser;
from xml.dom import minidom;


# Just a few global values for the logging format: 
Hostname = socket.gethostname();
TransactionId = str(  int ( random.random() * 10000000000000000 ) );

# Hardcoding splunk REST admin user/pw here and assuming all SH have the same user/pass.
# This could be added to the .cfg files for each SH, but we're keeping it simple:
SplunkUsername = 'admin';
SplunkPassword = 'changeme';



# Function:  writeLog is a simple function to write log data to out
def writeLog(state, message):
	print  str( datetime.datetime.now() ) + ' host=' + Hostname + ' transactionId=' + TransactionId + ' state=' + str(state) + ' message="' + str(message) + '"';



# Function:  processTargetConfigFile iterates over a search head target config file and calls
#            the configuration handler for each item to config for a search head
def processTargetConfigFile(filename):
	targetConfig = ConfigParser.ConfigParser();
	targetConfig.read(filename);
	
	# iterate over stanzas in config, assume they are Search Head host:port format.  Each stanza represents a search head with one or more REST endpoints to configure:
	for searchHead in targetConfig.sections():
		sessionKey = getRestSessionKey(searchHead);

		writeLog('INFO', searchHead + ' sessionKey is ' + sessionKey);

		# iterate over options for current searchHead.  Each option is a filename of a REST endpoint to configure:
		for configEndpoint in targetConfig.options(searchHead):
			performConfigurationEndpoint(searchHead, sessionKey, targetConfig.get(searchHead,configEndpoint) );



# Function:  performConfigurationEndpoint calls the appropriate handler for the endpoint 
#            type (user, searchpeer, etc):
def performConfigurationEndpoint(searchHead, sessionKey, filename):
	writeLog('INFO','Configuring ' + searchHead + ' ' + filename);
	
	endpointConfig = ConfigParser.ConfigParser();
        endpointConfig.read(filename);
	
	if (endpointConfig.has_option("Endpoint","type")):
		endpointType = endpointConfig.get('Endpoint', 'type');
	else:
		endpointType = '*not found*';
	
	if endpointType=='user':
		configureUserEndpoint(searchHead, sessionKey, endpointConfig);
	
	elif endpointType=='searchpeer':
		configureSearchPeerEndpoint(searchHead, sessionKey, endpointConfig);

	elif endpointType=='LDAP':
		configureLdapEndpoint(searchHead, sessionKey, endpointConfig);
			
	else:
		writeLog('ERROR','Unknown endpointType ' + endpointType);
	


# Function: configureUserEndpoint handles the delete/create of Splunk user accounts (non-LDAP)
def configureUserEndpoint(searchHead, sessionKey, userEndpointConfig):
	urlPath='/services/authentication/users';
	
	for userPasswordOption in userEndpointConfig.options('UserList'):
		userPasswordValue = userEndpointConfig.get('UserList',userPasswordOption).split('|');
		username = userPasswordValue[0];
		password = userPasswordValue[1];
		# To keep things simple we are only assuming one role - multiple roles means you send multiple 'roles' params to the REST endpoint
		role = userPasswordValue[2];

		# We'll now delete the user and then create the user to 'self-heal' the user based on our config files:

		userDeleteUrl = buildUrl(searchHead, urlPath + '/' + username);
		data = None;
		userDeleteResult = callRestEndpoint(userDeleteUrl, data, sessionKey, 'Delete');
		writeLog('DELETED','Deleted User ' + username);
		
		userCreateUrl = buildUrl(searchHead, urlPath);
	 	data = urlencode( {'name':username, 'password':password, 'roles':role} );
		userResult = callRestEndpoint(userCreateUrl, data, sessionKey);
		writeLog('CREATED','Created User ' + username);



# Function: configureSearchPeerEndpoint handles the delete/create of the Search Head's
#           search peers.   [This is just a stub]
def configureSearchPeerEndpoint(searchHead, sessionKey, endpointConfig):
	writeLog('PLACEHOLDER','SearchPeer Handler Placeholder...');
	# **Code to Delete/Update SearchPeers**



# Function: configureLdapEndpoint handles the delete/create of the Search Head's
#           LDAP configuration.  [This is just a stub]
def configureLdapEndpoint(searchHead, sessionKey, endpointConfig):
        writeLog('PLACEHOLDER','LDAP Handler Placeholder...');
        # **Code to Delete/Update Ldap**



# Function: getRestSessionKey handles obtaining a session key from the login
#           endpoint on the Search Head so we can re-use the session across
#           multiple calls to the Search Head's endpoints
def getRestSessionKey(searchHead):
	urlPath = '/services/auth/login';
	
	authenticateUrl = buildUrl(searchHead, urlPath);
	data = urlencode( {'username':SplunkUsername,'password':SplunkPassword} );
	authResults = callRestEndpoint(authenticateUrl, data);
	sessionKey = minidom.parseString(authResults).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue;
	return sessionKey;



# Function:  buildUrl is a helper function to concatenate our pieces together into a URL
def buildUrl(searchHead, urlPath):
	return 'https://' + searchHead + urlPath;



# Function: callRestEndpoint handles the HTTP request to a REST endpoint.  Give it a URL,
#           data, sessionKey, and if it is a DELETE method.
def callRestEndpoint(url, data=None, sessionKey=None, delete=None):
	try:
		restRequest = urllib2.Request(url,data);
		if sessionKey is not None:
			authHeader = 'Splunk ' + sessionKey;
			restRequest.add_header('Authorization', authHeader);

		if delete is not None:
			restRequest.get_method = lambda: 'DELETE';

		result = urllib2.urlopen(restRequest);
		r_string = result.read();
		result.close();
      		return r_string;
	except urllib2.HTTPError as e:
		writeLog('ERROR','REST endpoint error: ' + str(e.read()) );

	

# Main:

writeLog('BEGIN','Begin SH Configuration');

if (len(sys.argv)==1):
	# Default config file
	processTargetConfigFile('targetSearchHeads.cfg');
else:
	for configFile in sys.argv[1:]:
		# Assume arguement is actually a config file
		processTargetConfigFile(configFile);	

writeLog('END','End SH Configuration');

