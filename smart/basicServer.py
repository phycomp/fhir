import tornado.ioloop
import tornado.web
import json
from datetime import datetime
import uuid

class FHIRResource:
    def __init__(self):
        self.resources = {}
    
    def create(self, resource_type, data):
        resource_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        resource = {
            "resourceType": resource_type,
            "id": resource_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": timestamp
            }
        }
        resource.update(data)
        
        self.resources[f"{resource_type}/{resource_id}"] = resource
        return resource
    
    def read(self, resource_type, resource_id):
        key = f"{resource_type}/{resource_id}"
        return self.resources.get(key)
    
    def update(self, resource_type, resource_id, data):
        key = f"{resource_type}/{resource_id}"
        if key not in self.resources:
            return None
            
        resource = self.resources[key]
        version = int(resource["meta"]["versionId"])
        timestamp = datetime.now().isoformat()
        
        updated_resource = {
            "resourceType": resource_type,
            "id": resource_id,
            "meta": {
                "versionId": str(version + 1),
                "lastUpdated": timestamp
            }
        }
        updated_resource.update(data)
        
        self.resources[key] = updated_resource
        return updated_resource
    
    def delete(self, resource_type, resource_id):
        key = f"{resource_type}/{resource_id}"
        return self.resources.pop(key, None)

class FHIRHandler(tornado.web.RequestHandler):
    def initialize(self, fhir_resource):
        self.fhir_resource = fhir_resource
    
    def set_default_headers(self):
        self.set_header("Content-Type", "application/fhir+json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
    
    def options(self, resource_type, resource_id=None):
        self.set_status(204)
        self.finish()

class FHIRResourceHandler(FHIRHandler):
    def get(self, resource_type, resource_id):
        resource = self.fhir_resource.read(resource_type, resource_id)
        if resource:
            self.write(resource)
        else:
            self.set_status(404)
            self.write({"resourceType": "OperationOutcome",
                       "issue": [{"severity": "error",
                                "code": "not-found",
                                "diagnostics": f"Resource {resource_type}/{resource_id} not found"}]})
    
    def put(self, resource_type, resource_id):
        try:
            data = json.loads(self.request.body)
            resource = self.fhir_resource.update(resource_type, resource_id, data)
            if resource:
                self.write(resource)
            else:
                self.set_status(404)
                self.write({"resourceType": "OperationOutcome",
                           "issue": [{"severity": "error",
                                    "code": "not-found",
                                    "diagnostics": f"Resource {resource_type}/{resource_id} not found"}]})
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"resourceType": "OperationOutcome",
                       "issue": [{"severity": "error",
                                "code": "invalid",
                                "diagnostics": "Invalid JSON"}]})
    
    def delete(self, resource_type, resource_id):
        resource = self.fhir_resource.delete(resource_type, resource_id)
        if resource:
            self.set_status(204)
        else:
            self.set_status(404)
            self.write({"resourceType": "OperationOutcome",
                       "issue": [{"severity": "error",
                                "code": "not-found",
                                "diagnostics": f"Resource {resource_type}/{resource_id} not found"}]})

class FHIRTypeHandler(FHIRHandler):
    def post(self, resource_type):
        try:
            data = json.loads(self.request.body)
            resource = self.fhir_resource.create(resource_type, data)
            self.set_status(201)
            self.set_header("Location", f"/{resource_type}/{resource['id']}")
            self.write(resource)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"resourceType": "OperationOutcome",
                       "issue": [{"severity": "error",
                                "code": "invalid",
                                "diagnostics": "Invalid JSON"}]})

def make_app():
    fhir_resource = FHIRResource()
    return tornado.web.Application([
        (r"/([^/]+)/([^/]+)", FHIRResourceHandler, dict(fhir_resource=fhir_resource)),
        (r"/([^/]+)", FHIRTypeHandler, dict(fhir_resource=fhir_resource)),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("FHIR Server running on http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()
