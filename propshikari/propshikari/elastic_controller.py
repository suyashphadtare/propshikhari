from __future__ import unicode_literals
import frappe
from elasticsearch import Elasticsearch
from datetime import datetime


class ElasticSearchController():
	
	""" 
	    This is elastic search handler designed to cater all 
	    elastic search operations like search,indexing,update. 	
	"""
	
	def __init__(self):
		self.es = Elasticsearch()


	def index_document(self,type_name, data, custom_id):
		response = self.es.index(index="propshikari", doc_type=type_name, body=data, id=custom_id)	
		return response

	def search_document(self, type_list, search_body, page_no, no_of_records=20):
		
		""" 
			Search document in given type_list for given search criteria 
	   		with no of records to be returned.
		"""		
		
		response = self.es.search(index=["propshikari"], doc_type=type_list, body=search_body, from_=(page_no - 1) * 20, size=no_of_records)
		return [response["_source"] for response in response["hits"]["hits"]]		