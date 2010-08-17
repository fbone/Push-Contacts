#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Written by - NGO MINH NAM (emoinrp@gmail.com)
# Third-party application server for C2DM on Google App Engine rewritten from Java to Python
# Original implementation from ChromToPhone (http://code.google.com/p/chrometophone/source/browse/#svn/trunk/appengine)

# Features: - Store/remove C2DM registration_id in/from datastore
#           - Send POST request to C2DM server to be pushed to the Android phone
# Notes:    - delay_while_idle and sendWithRetry is not implemented

from os import path

from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import util
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.template import render
import urllib


class Info(db.Model):
    registration_id = db.StringProperty(multiline=True)

class MainHandler(webapp.RequestHandler):
    def get(self):
        tmpl = path.join(path.dirname(__file__), 'static/html/main.html')
        context = {"data": "something"}
        self.response.out.write(render(tmpl,context))

class RegisterHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        devregid = self.request.get('devregid')
        if not devregid:
            self.error(400)
            self.response.out.write('Must specify devregid')
        else:
	        user = users.get_current_user()
	        if user:
		        #Store registration_id and an unique key_name with email value
	            info = Info(key_name=user.email())
	            info.registration_id = devregid   
	            info.put()
	            self.response.out.write('OK')
	        else:
		        self.response.out.write('Not authorized')         	

class UnregisterHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        devregid = self.request.get('devregid')
        if not devregid:
            self.error(400)
            self.response.out.write('Must specify devregid')
        else:
	        user = users.get_current_user()
	        if user:
		        #Remove entry with the associated email value
	            info =  Info.get_by_key_name(user.email())
	            info.delete()
	            self.response.out.write('OK')
	        else:
		        self.response.out.write('Not authorized')
		
class SmsformHandler(webapp.RequestHandler):
    def get(self):
        phone_number = self.request.get('phone')
        if phone_number.isdigit():
	        self.response.out.write("""
			<html>
	          <body>
	            <form action="/sms" method="post">
	              Text to SMS:<br/>
                  <textarea name="sms" rows="4" cols="40" maxlength="250"></textarea><br/>
                  <input type="hidden" name="phone" value="%s" /><br/>
	              <input type="submit" value="Send SMS">
	            </form>
	          </body>
	        </html>
			""" % phone_number)
        else:
            self.response.out.write("Not a valid phone number")	    

class SmsHandler(webapp.RequestHandler):
    def post(self):
        phone_number = self.request.get('phone')
        sms = self.request.get('sms')
        user = users.get_current_user()
        data = {"data.sms" : sms,
                "data.phone_number" : phone_number}
        sendToPhone(self,data, user.email())

class SendHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        #URL decode params
        contact_name = urllib.unquote(self.request.get('name'))  
        phone_number = urllib.unquote(self.request.get('phone'))
        
        if not contact_name or not phone_number:
            self.error(400)
            self.response.out.write('error_params')
        else:
            user = users.get_current_user()
            if user:
	            #Send the message to C2DM server
                data = {"data.contact_name" : contact_name,
                        "data.phone_number" : phone_number}
                sendToPhone(self,data, user.email())
            else:
	            #User is not logged in
                self.response.out.write('error_login')

#Helper method to send params to C2DM server
def sendToPhone(self,data,email):
    info = Info.get_by_key_name(email)
    registration_id = info.registration_id

    #Get authentication token pre-stored on datastore with ID 1
    #Alternatively, it's possible to store your authToken in a txt file and read from it (CTP implementation)
    info = Info.get_by_id(1)
    authToken = info.registration_id
    form_fields = {
        "registration_id": registration_id,
        "collapse_key": hash(email), #collapse_key is an arbitrary string (implement as you want)
    }
    form_fields.update(data)
    form_data = urllib.urlencode(form_fields)
    url = "https://android.clients.google.com/c2dm/send"
    
    #Make a POST request to C2DM server
    result = urlfetch.fetch(url=url,
                            payload=form_data,
                            method=urlfetch.POST,
                            headers={'Content-Type': 'application/x-www-form-urlencoded',
                                     'Authorization': 'GoogleLogin auth=' + authToken})
    if result.status_code == 200:
	    self.response.out.write("OK")
    else:
	    self.response.out.write('error_c2dm')

	        
def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/register', RegisterHandler),
                                          ('/unregister', UnregisterHandler),
                                          ('/send', SendHandler),
                                          ('/smsform', SmsformHandler),
                                          ('/sms', SmsHandler)
                                          ],
                                          debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
