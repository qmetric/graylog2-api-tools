#!/usr/bin/python
import sys
import yaml
import pprint 
import argparse
import logging
import json
import jsonpickle
import cgi
import os
import requests

	
def insert_alert_recipient(receiver_url,receiver,r_type):
	new_recipient = { 'entity': receiver, 'type': r_type }
	headers = {'Content-type': 'application/json'}
	response = requests.post(receiver_url)
	status = False
	if response.status_code is requests.codes.created:
		status = True
	return status

def insert_stream_cond(cond_url,condition):
	headers = {'Content-type': 'application/json'}
	response = requests.post(cond_url, data=json.dumps(condition), headers=headers)
	id = 0
	if response.status_code is requests.codes.created:
		json_response = response.text
		new_condition = json.loads(json_response)
	return id

def insert_rule(rule_url,rule):
	headers = {'Content-type': 'application/json'}
	response = requests.post(rule_url, data=json.dumps(rule), headers=headers)
	id = 0
	if response.status_code is requests.codes.created:
		json_response = response.text
		new_rule = json.loads(json_response)
		id = new_rule['streamrule_id']
	return id

def insert_stream(api_url,stream):
	rules = []
	alert_receivers = []
	alert_conditions = []
	if 'alert_conditions' in stream:
		alert_conditions = stream['alert_conditions']
		del stream['alert_conditions']
	if 'alert_receivers' in stream:
		alert_receivers = stream['alert_receivers']
		del stream['alert_receivers']
	if 'rules' in stream:
		rules = stream['rules']
		del stream['rules']
	headers = {'Content-type': 'application/json'}
	response = requests.post(api_url, data=json.dumps(stream), headers=headers)
	id = 0
	if response.status_code is requests.codes.created:
		json_response = response.text
		new_stream = json.loads(json_response)
		id = new_stream['stream_id']
		for rule in rules:
			rule_url = api_url + "/{0}/rules".format(id)
			rule_id = insert_rule(rule_url,rule)
		for condition in alert_conditions:
			cond_url = api_url + "/{0}/alerts/conditions".format(id)
			cond_id = insert_stream_cond(cond_url,condition)
		for r_type in alert_receivers:
			for receiver in alert_receivers[r_type]:
				receiver_url = api_url + "/{0}/alerts/receivers?entity={1}&type={2}".format(id,receiver,r_type)
				rule_id = insert_alert_recipient(receiver_url,receiver,r_type)
	return id
	

def create_stream(api_url,stream):
	current_streams = get_streams(api_url,[])
	id = 0
	for current_stream in current_streams['streams']:
		if current_stream['title'] == stream['title']:
			return 0
	id = insert_stream(api_url,stream)
	return id

def resume_stream(api_url,stream_id):
	resume_url = api_url + "/" + stream_id + "/resume"
	response = requests.post(resume_url)
	status = False
	if response.status_code is requests.codes.ok:
		status = True
	return status

def facility_stream(api_url,facility_name):
	regex = facility_name + "*"
	fac_stream = {   
		'description': "Application: {0}".format(facility_name),
		"creator_user_id" : "admin",
		'title': facility_name,
		'rules': [ 
			{	"field" : "facility",
				"value" : regex,
				"type" : 2,
				"inverted" : False
			} ]
	}
	id = create_stream(api_url,fac_stream)
	if id:
		message = "created {0} stream".format(facility_name)
		resume_stream(api_url,id)
	else:
		message = "stream {0} already exists".format(facility_name)
	logging.debug(message)
	return (message,id)


def load_streams(api_url,streams):
	try:	
		conflicts = 0
		message = ""
		for stream in streams['streams']:
			id = create_stream(api_url,stream)
			title = stream['title']
			if id:
				message += "stream {0} created. ".format(title)
				resume_stream(api_url,id)
			else:
				message += "stream {0} already exists. ".format(title)
				conflicts = conflicts + 1
		logging.debug("Load Stream: %s",message)
		return (message,conflicts)
	except:
		message = "Load streams failed"
		logging.debug("Load streams failed")
		return (message,False)

def save_streams(api_url,filename,title_list):
	logging.debug("Streams save begins")
	try:
		f = open(filename, 'w')
		f.write(json.dumps(get_streams(api_url,title_list)))
	except Exception, e:
		print "HELP {0}".format(e)
		logging.debug("Stream save failed - none?")
		sys.exit(1)

# get the streams and sanitize out ids and timestamps
def get_streams(api_url,title_list):
	headers = {'Content-type': 'application/json'}
	response = requests.get(api_url, headers=headers)
	if response.status_code is requests.codes.ok:
		json_response = response.text
		data = json.loads(json_response)
		if title_list:
			data['streams'] = [stream for stream in data['streams'] if stream.get('title') in title_list]
			data['total'] = len(data['streams'])
		for stream in data['streams']:
			del stream['created_at'] 
			del stream['id'] 
			del stream['disabled'] 
			if 'rules' in stream:
				for rule in stream['rules']:
					del rule['id']
					del rule['stream_id']
			if 'alert_conditions' in stream:
				for condition in stream['alert_conditions']:
					del condition['id']
					del condition['created_at']
		return data
	return {}
	
def convert(input):
	if isinstance(input, dict):
		return dict([(convert(key), convert(value)) for key, value in input.iteritems()])
	elif isinstance(input, list):
		return [convert(element) for element in input]
	elif isinstance(input, unicode):
		return input.encode('utf-8')
	else:
		return input

def main():

	api_url = 'http://admin:password@127.0.0.1:12900/streams'
	logfile = '/tmp/stream_script.log'
	#log_level = logging.INFO
	log_level = logging.DEBUG
	logging.basicConfig(
		filename = logfile,
		filemode = 'a',
		level = log_level,
		format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	)

	result = {}
	result['error'] = False
	logging.debug("Streams Init")
	if "REQUEST_METHOD" in os.environ:
		logging.debug("Streams in CGI")
		if os.environ['REQUEST_METHOD'] == 'POST':
			logging.debug("Streams in POST CGI")
			print "Content-Type: application/json"
			print
			streamed_json = sys.stdin.read()
			result['message'] = "Successfully uploaded Streams"
			result['payload'] = streamed_json
			result['error'] = False
			# check if its a fac or full
			streams = convert(json.loads(streamed_json))
			stream_count = len(streams['streams'])
			conflicts = 0
			message = ""
			if 'new_facility_stream' in streams:
				(message,conflicts) = facility_stream(api_url,streams['new_facility_stream'])
			else:
				(message,conflicts) = load_streams(api_url,streams)
			if not conflicts:
				logging.debug("Stream upload SUCCESS: C:{0} N:{1}".format(conflicts,stream_count))
				print "Status: 201 Created"
			elif conflicts < stream_count:
				logging.debug("Stream upload Clashes: C:{0} N:{1}".format(conflicts,stream_count))
				print "Status: 201 Created"
				result['message'] = "Failed to create {0} stream(s) due to conflict, others good".format(conflicts)
			elif conflicts == stream_count:
				# 409 with good status and how to fix
				print "Status: 409 Conflict"
				result['poyload'] = message
				result['message'] = "Failed to upload stream(s)"
				result['error'] = True
			print                               # blank line, end of headers
			print jsonpickle.encode(result,unpicklable=False)
		elif os.environ['REQUEST_METHOD'] == 'GET':
			logging.debug("Streams in GET CGI")
			form = cgi.FieldStorage()
			title_list = []
			if 'titles' in form:
				for i in form['titles'].value.split(','):
					title_list.append(i)
			result['payload'] = get_streams(api_url,title_list)
			if 'total' in result['payload'] and result['payload']['total'] == 0:
				result['message'] = "No Streams to get!"
			else:
				result['message'] = "Successfully got Streams"
			result['error'] = False
			if "pretty" not in form:
				print "Content-Type: application/json"
				print                               
				if "save" in form:
					print jsonpickle.encode(result['payload'],unpicklable=False)
				else:
					print jsonpickle.encode(result,unpicklable=False)
			else:
				print "Content-Type: text/html;charset=utf-8"
				print
				print "<html><body><pre><code>"
				jsonpickle.set_encoder_options('simplejson', indent=4)
				print jsonpickle.encode(result,unpicklable=False)
				print "</code></pre></body></html>"
			logging.debug("Stream get success")
		else:
			result['message'] = "Use a GET or POST Method  - COME ONNNN"
			result['payload'] = None
			result['error'] = True
			print "Status: 405 Method Not Allowed"
			print "Allow: POST"
			print "Content-Type: application/json"
			print                               # blank line, end of headers
			print jsonpickle.encode(result,unpicklable=False)
			logging.debug("Streams CGI - not a POST or GET")
		sys.exit(0)

	else:
		logging.debug("Steams in CLI")
		parser = argparse.ArgumentParser(description='Needs a stream name. at least')
		parser.add_argument('-d', action="store_true", default=False, help='debug a bit')
		parser.add_argument('-s', help='save Title/All streams as json dump to filename"')
		parser.add_argument('-l', help='load streams from "filename" made from -s')
		parser.add_argument('-f', help='create facility stream "name"')
		parser.add_argument('-g', help='the graylog2 host for the api')
		parser.add_argument('-t', help='get only this list of screen titles')
		parser.add_argument('-i', action="store_true", help='display all streams')
		args = parser.parse_args()

		title_list = []
		if args.t:
			for i in args.t.split(','):
				title_list.append(i)
		if args.g:
			api_url = "http://admin:password@{0}:12900/streams".format(args.g)

		if args.f:
			(message,id) = facility_stream(api_url,args.f)
			print "M:{0} I:{1}".format(message,id)

		if args.l:
			f = open(args.l,'r')
			streamed_json = f.read()
			streams = convert(json.loads(streamed_json))
			message,load_ok = load_streams(api_url,streams)
			if not load_ok:
				print message
				sys.exit(1)

		if args.i:
			pp = pprint.PrettyPrinter(indent=4)
			pp.pprint(get_streams(api_url,title_list))
		
		if args.s:
			save_streams(api_url,args.s,title_list)
		

if __name__ == "__main__":
	main()


