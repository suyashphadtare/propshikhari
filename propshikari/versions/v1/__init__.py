from __future__ import unicode_literals
import api_handler
import propshikari.propshikari.propshikari_api as api
import propshikari.propshikari.property_masters as masters
from frappe.utils import cstr, cint
import frappe
import time
import json
import random
from frappe.utils.file_manager import  save_file



@frappe.whitelist()
def post_property(data):
	return api.post_property(data)


@frappe.whitelist(allow_guest=True)
def search_property(data):
	return api.search_property(data)



@frappe.whitelist(allow_guest=True)
def register_user(data):
	return api.register_user(data)


@frappe.whitelist(allow_guest=True)
def forgot_password(data):
	return api.forgot_password(data)



@frappe.whitelist()
def update_password(data):
	return api.update_password(data)



@frappe.whitelist()
def get_user_profile(data):
	return api.get_user_profile(data)


@frappe.whitelist()
def update_user_profile(data):
	return api.update_user_profile(data)


@frappe.whitelist()
def logout(data):
	return api.log_out_from_propshikari(data)	


@frappe.whitelist(allow_guest=True)
def get_state_city_location_list(data):
	return api.get_states_cities_locations_from_propshikari(data)



@frappe.whitelist(allow_guest=True)
def store_image_to_propshikari(data):
	return api.store_image_to_propshikari(data)

	

@frappe.whitelist(allow_guest=True)
def get_property_types(data):
	return masters.get_property_types(data)


@frappe.whitelist(allow_guest=True)
def get_amenities(data):
	return masters.get_amenities(data)

@frappe.whitelist(allow_guest=True)
def get_flat_facilities(data):
	return masters.get_flat_facilities(data)


@frappe.whitelist()
def create_group(data):
	return masters.create_group_in_hunterscamp(data)


@frappe.whitelist()
def join_group(data):
	return masters.join_user_with_group_id(data)


@frappe.whitelist()
def search_group(data):
	return api.search_group_with_given_criteria(data)




		