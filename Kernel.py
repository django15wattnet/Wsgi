import traceback
from importlib import import_module
from sqlobject import *
from .Request import Request
from .Response import Response


class Kernel(object):
	"""
		Handles the complete request to response cycle.
	"""
	__routes   = {}
	__config   = {}
	__env      = {}
	__request  = None
	__response = None


	def __init__(self):
		self.__loadConfig()
		self.__connectToDatabase()
		self.__loadRoutes()


	def run(self, env: dict, startResponse):
		"""
			Handles to whole request
		"""
		self.__env = env

		# Create a request instance
		self.__request = Request(env=env)

		# Create a response instance
		self.__response = Response(
			startResponse=startResponse,
			request=self.__request
		)

		self.__addAccessControlHeader()

		# Find the controller and method
		keyRoute = env.get('REQUEST_METHOD') + '_' + env.get('PATH_INFO')

		if keyRoute in self.__routes:
			# Found, so I call the controller method
			try:
				self.__routes[keyRoute].methodToCall(
					request=self.__request,
					response=self.__response
				)
			except Exception as e:
				if 'debug' in self.__config and self.__config['debug'] is True:
					tb = traceback.format_exc()
				else:
					tb = ''

				self.__response.returnCode = 500
				self.__response.stringContent = 'Internal server error.\n{tb}'.format(tb=tb)
				self.__response.contentType = 'text/plain'
				self.__response.charset = 'utf-8'
		else:
			# todo Error-Controller erstellen
			self.__response.returnCode    = 404
			self.__response.stringContent = 'No controller method found for route: ' + keyRoute
			self.__response.contentType   = 'text/plain'
			self.__response.charset       = 'utf-8'

		return self.__response.getContent()


	def __loadConfig(self):
		"""
			Reads the variables from project root.config.py
		:return:
		"""
		config = import_module(name='config')
		for k in dir(config):
			if k.startswith('__'):
				continue

			self.__config[k] = getattr(config, k)

		return


	def __connectToDatabase(self):
		"""
			If the key uriDb is present in the config, a database connection
			will be established.
		:return:
		"""
		if 'uriDb' not in self.__config:
			self.__config['dbConnection'] = None
			return

		self.__config['dbConnection'] = connectionForURI(uri=self.__config['uriDb'])
		sqlhub.processConnection = self.__config['dbConnection']


	def __loadRoutes(self):
		"""
			Loads all routes and injects the configuration to them
		:return:
		"""
		module = import_module(name='routes')
		for route in getattr(module, 'routes'):
			route.setConfig(config=self.__config)
			k = route.httpMethod.name + '_' + route.path
			self.__routes[k] = route

	def __addAccessControlHeader(self):
		if 'accessControlAllowOrigin' not in self.__config:
			return

		accessControlAllowOrigin = []
		accessControlAllowOrigin = accessControlAllowOrigin + self.__config['accessControlAllowOrigin']

		if 0 == len(accessControlAllowOrigin) or False == self.__request.hasHeader('Origin'):
			return

		for url in accessControlAllowOrigin:
			if self.__request.getHeader('Origin') == url:
				self.__response.addHeader('Access-Control-Allow-Origin', url)


	def __str__(self):
		"""
			Just a dump string representation of the kernel
		"""
		ret = 'Config:\n'
		for k in self.__config:
			ret += '\t{key}={val}\n'.format(key=k, val=self.__config[k])

		ret += '\nRoutes:\n'

		for k in self.__routes:
			ret += '\t' + str(self.__routes[k]) + '\n'

		ret += '\nENV:\n'

		for k in self.__env:
			ret += '\t{key}={val}\n'.format(key=k, val=self.__env[k])

		return ret