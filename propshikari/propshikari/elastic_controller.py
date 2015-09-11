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

	def search_document(self, type_list, search_body, page_no, no_of_records=40):
		
		""" 
			Search document in given type_list for given search criteria 
	   		with no of records to be returned.
		"""		

		response = self.es.search(index=["propshikari"], doc_type=type_list, body=search_body, from_=(page_no - 1) * no_of_records, size=no_of_records)
		total_records = response["hits"]["total"]
		return [response["_source"] for response in response["hits"]["hits"]] , total_records


	
	def search_document_for_given_id(self, type_list, search_id, exclude_list=[], include_list=[]):

		""" Get document of given ids from elasticsearch """

		response = self.es.get(index="propshikari", doc_type=type_list, id=search_id, _source_exclude=exclude_list ,_source_include=include_list)
		return response.get("_source")


	def update_docuemnt(self, type_name, search_id, search_body):

		"""  Update Document based on given id i elasticsearch """

		response = self.es.update(index="propshikari", doc_type=type_name ,id=search_id, body=search_body)
		return response			