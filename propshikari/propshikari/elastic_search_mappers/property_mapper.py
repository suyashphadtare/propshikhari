
property_mapper = {  
  "property": {
    "properties": {
      "property_id": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "property_title": {
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
      "price": {
        "type": "double",
        "store": "true"
      },
      "email_id": {
        "type": "string",
        "store": "true"
      },
      "amenities": {
        "type": "nested",
        "properties": {
         "name": {
           "type": "string",
           "index": "not_analyzed",
           "store": "true"
         },
         "image": {
           "type": "string",
           "store": "true"
         },
         "status": {
           "type": "string",
           "store": "true"
         },
         "property_subtype": {
           "type": "string",
           "index": "not_analyzed",
           "store": "true"
         }
       }
      },
      "description": {
        "type": "string",
        "store": "true"
      },
      "price_per_sq_ft": {
        "type": "double",
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
      "floor_no": {
        "type": "integer",
        "store": "true"
      },
      "posting_date": {
        "type": "date",
        "format": "dd-MM-YYYY",
        "store": "true"
      },
      "no_of_bathroom": {
        "type": "integer",
        "store": "true"
      },
      "property_type": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "property_subtype_option": {
        "type": "string",
        "store": "true"
      },
      "property_subtype": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "property_age": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "furnishing_type": {
        "type": "string",
        "store": "true"
      },
      "possession": {
        "type": "integer",
        "store": "true"
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
      "carpet_area": {
        "type": "double",
        "store": "true"
      },
      "pincode": {
        "type": "long",
        "store": "true"
      },
      "property_ownership": {
        "type": "string",
        "store": "true"
      },
      "flat_facilities": {
        "type": "nested",
        "properties": {
          "name": {
            "type": "string",
            "index": "not_analyzed",
            "store": "true"
          },
          "image": {
            "type": "string",
            "store": "true"
          },
          "status": {
            "type": "string",
            "store": "true"
          }
        }
      },
      "transaction_type": {
        "type": "string",
        "store": "true"
      },
      "security_deposit": {
        "type": "double",
        "store": "true"
      },
      "maintainance_charges": {
        "type": "double",
        "store": "true"
      },
      "lease_type": {
        "type": "string",
        "store": "true"
      },
      "listed_by": {
        "type": "string",
        "store": "true"
      },
      "agent_name": {
        "type": "string",
        "store": "true"
      },
      "agent_no": {
        "type": "long",
        "store": "true"
      },
      "contact_no": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "contact_person": {
        "type": "string",
        "store": "true"
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
      "percent_completion": {
        "type": "float",
        "store": "true"
      },
      "society_name": {
        "type": "string",
        "store": "true"
      },
      "project_id": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "project_title": {
        "type": "string",
        "store": "true"
      },
      "project_type": {
        "type": "string",
        "store": "true"
      },
      "project_by": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "project_sub_type": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "status": {
        "type": "string",
        "store": "true"
      },
      "operation": {
        "type": "string",
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
      "posted_by": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "user_email":{
        "type": "string",
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
      "unit_of_area":{
        "type": "string",
        "store": "true"
      },
      "possession_date": {
        "type": "date",
        "format": "MM-YYYY",
        "store": "true"
      },
      "property_photo": {
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "property_owner":{
        "type": "string",
        "store": "true"
      },
      "possession_status":{
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "published_status":{
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      },
      "project_name":{
        "type": "string",
        "index": "not_analyzed",
        "store": "true"
      }
    }
  }
}