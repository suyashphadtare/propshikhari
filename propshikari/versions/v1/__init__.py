from __future__ import unicode_literals
import api_handler
import frappe

@frappe.whitelist(allow_guest=True)
def postproperty(data):
	#raise api_handler.AuthenticationError('Unauthorized User')
	print data
	return {"operation":"search","message":"Property Found","data":{"name":"hshsh"}}