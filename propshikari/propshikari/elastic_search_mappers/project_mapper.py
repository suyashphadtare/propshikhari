
project_mapper = {
  "project": {
    "properties": {
      "project_id": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "project_name": {
        "type": "string",
        "store": "true"
      },
      "project_type": {
        "type": "string",
        "store": "true"
      },
      "project_subtype": {
        "type": "string",
        "store": "true"
      },
      "project_by": {
        "type": "string",
        "store": "true"
      },
      "project_for": {
        "type": "string",
        "store": "true"
      },
      "email_id": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "website": {
        "type": "string",
        "store": "true"
      },
      "full_size_images": {
        "type": "string",
        "store": "true"
      },
      "thumbnails": {
        "type": "string",
        "store": "true"
      },
      "project_photo": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "property_details": {
        "type": "nested",
        "properties": {
          "property_subtype_option": {
            "type": "string",
            "store": "true"
          },
          "min_area": {
            "type": "double",
            "store": "true"
          },
          "max_area": {
            "type": "double",
            "store": "true"
          },
          "min_price": {
            "type": "double",
            "store": "true"
          },
          "max_price": {
            "type": "double",
            "store": "true"
          },
          "unit_of_area": {
           "type": "string",
           "store": "true"
          },
          "no_of_bathroom": {
            "type": "integer",
            "store": "true"
          },
          "count": {
            "type": "integer",
            "store": "true"
          }
        }
      },
      "location": {
        "type": "multi_field",
        "fields": {
          "location": {
            "type": "string",
            "store": "true"
          },
          "original": {
            "type": "string",
            "index": "not_analyzed",
            "store": "true"
          }
        }
      },
      "address": {
        "type": "multi_field",
        "fields": {
          "address": {
            "type": "string",
            "store": "true"
          },
          "original": {
            "type": "string",
            "index": "not_analyzed",
            "store": "true"
          }
        }
      },
      "state": {
        "type": "string",
        "store": "true"
      },
      "city": {
        "type": "string",
        "store": "true"
      },
      "pincode": {
        "type": "long",
        "store": "true"
      },
      "amenities": {
        "type": "nested",
        "properties": {
          "name": {
            "type": "string",
            "store": "true"
          },
          "image": {
            "type": "string",
            "index": "not_analyzed",
            "store": "true"
          },
          "status": {
            "type": "string",
            "store": "true"
          }
        }
      },
      "fees_in_percent": {
        "type": "float",
        "store": "true"
      },
      "project_tieup_by": {
        "type": "string",
        "store": "true"
      },
      "property_age": {
        "type": "string",
        "store": "true"
      },
      "tag": {
        "type": "string",
        "store": "true"
      },
      "no_of_floors": {
        "type": "integer",
        "store": "true"
      },
      "furnishing_type": {
        "type": "string",
        "store": "true"
      },
      "price_per_sq_ft": {
        "type": "double",
        "store": "true"
      },
      "possession": {
        "type": "integer",
        "store": "true"
      },
      "posting_date": {
        "type": "date",
        "format": "dd-MM-YYYY",
        "store": "true"
      },
      "overview": {
        "type": "string",
        "store": "true"
      },
      "contact_no": {
        "type": "long",
        "store": "true"
      },
      "contact_person": {
        "type": "string",
        "store": "true"
      },
      "percent_completion": {
        "type": "float",
        "store": "true"
      },
      "distance_from_imp_locations": {
        "type": "object",
        "properties": {
          "central_bus_stand": {
            "type": "float",
            "store": "true"
          },
          "railway_station": {
            "type": "float",
            "store": "true"
          },
          "airport": {
            "type": "float",
            "store": "true"
          }
        }
      },
      "geo_location_lat": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "geo_location_lon":{
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "posted_by": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "created_by": {
        "type": "string",
        "store": "true"
      },
      "modified_by": {
        "type": "string",
        "store": "true"
      },
      "posted_datetime": {
        "type": "date",
        "store": "true",
        "format": "yyyy-MM-dd HH:mm:ss"
      },
      "modified_datetime": {
        "type": "date",
        "store": "true",
        "format": "yyyy-MM-dd HH:mm:ss"
      },
      "modified_date": {
        "type": "date",
        "format": "dd-MM-YYYY",
        "store": "true"
      },
      "creation_date": {
        "type": "date",
        "format": "dd-MM-YYYY",
        "store": "true"
      },
      "possession_date": {
        "type": "date",
        "format": "MM-YYYY",
        "store": "true"
      },
      "status": {
        "type": "string",
        "store": "true"
       },
       "transaction_type":{
        "type": "string",
        "store": "true"
       }
    }
  }
}