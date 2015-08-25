import frappe
import json
from api_handler.response import report_error

@frappe.whitelist(allow_guest=True)
def login(data):
	user_data = json.loads(data)
	try: 
		loginmgr = frappe.auth.LoginManager()
		frappe.clear_cache(user = user_data["user"])
		loginmgr.authenticate(user_data["user"],user_data["password"])
		loginmgr.post_login()
		frappe.response["sid"] = frappe.session.sid	
	
	except frappe.AuthenticationError,e:
		http_status_code = getattr(e, "http_status_code", 500)
		frappe.response["code"] = http_status_code
	
	finally:
		import time
		ts = int(time.time())
		frappe.response["timestamp"] = ts


	

