from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler
import json
from datetime import datetime
import uuid
from urllib.parse import parse_qs

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

    def search(self, resource_type, params):
        """
        搜索指定類型的資源
        支援分頁和基本搜索參數
        """
        # 獲取分頁參數
        try:
            page = int(params.get('_page', ['1'])[0])
            count = int(params.get('_count', ['10'])[0])
        except ValueError:
            page = 1
            count = 10

        # 過濾指定類型的資源
        matching_resources = [
            resource for key, resource in self.resources.items()
            if key.startswith(f"{resource_type}/")
        ]

        # 應用搜索條件
        filtered_resources = self._apply_search_filters(matching_resources, params)

        # 計算分頁
        start_index = (page - 1) * count
        end_index = start_index + count

        # 準備搜索結果
        paged_resources = filtered_resources[start_index:end_index]

        # 創建Bundle資源
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(filtered_resources),
            "link": self._create_pagination_links(resource_type, params, page, count, len(filtered_resources)),
            "entry": [{"resource": resource} for resource in paged_resources]
        }

    def _apply_search_filters(self, resources, params):
        """應用搜索過濾器"""
        filtered = resources.copy()

        # 移除分頁參數
        search_params = {k: v for k, v in params.items() if not k.startswith('_')}

        for param, values in search_params.items():
            filtered = self._filter_by_param(filtered, param, values[0])

        return filtered

    def _filter_by_param(self, resources, param, value):
        """根據參數過濾資源"""
        filtered = []

        for resource in resources:
            # 處理不同類型的搜索參數
            if '.' in param:
                # 處理複雜的搜索參數 (如 name.given)
                base, sub_param = param.split('.', 1)
                if self._match_complex_param(resource, base, sub_param, value):
                    filtered.append(resource)
            else:
                # 處理簡單的搜索參數
                if self._match_simple_param(resource, param, value):
                    filtered.append(resource)

        return filtered

    def _match_complex_param(self, resource, base, sub_param, value):
        """匹配複雜參數"""
        if base not in resource:
            return False

        if isinstance(resource[base], list):
            # 處理陣列類型的參數 (如 name[])
            for item in resource[base]:
                if sub_param in item and str(item[sub_param]).lower() == value.lower():
                    return True
        elif isinstance(resource[base], dict):
            # 處理物件類型的參數
            return sub_param in resource[base] and str(resource[base][sub_param]).lower() == value.lower()

        return False

    def _match_simple_param(self, resource, param, value):
        """匹配簡單參數"""
        return param in resource and str(resource[param]).lower() == value.lower()

    def _create_pagination_links(self, resource_type, params, current_page, count, total_resources):
        """創建分頁連結"""
        links = []
        base_url = f"/{resource_type}?"

        # 移除現有的分頁參數
        query_params = {k: v[0] for k, v in params.items() if k not in ['_page']}

        # 計算總頁數
        total_pages = (total_resources + count - 1) // count

        # 自連結
        links.append({
            "relation": "self",
            "url": f"{base_url}_page={current_page}&" + "&".join([f"{k}={v}" for k, v in query_params.items()])
        })

        # 首頁連結
        if current_page > 1:
            links.append({
                "relation": "first",
                "url": f"{base_url}_page=1&" + "&".join([f"{k}={v}" for k, v in query_params.items()])
            })

        # 下一頁連結
        if current_page < total_pages:
            links.append({
                "relation": "next",
                "url": f"{base_url}_page={current_page + 1}&" + "&".join([f"{k}={v}" for k, v in query_params.items()])
            })

        # 上一頁連結
        if current_page > 1:
            links.append({
                "relation": "previous",
                "url": f"{base_url}_page={current_page - 1}&" + "&".join([f"{k}={v}" for k, v in query_params.items()])
            })

        return links
class FHIRHandler(RequestHandler):
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
    def get(self, resource_type): # 處理搜索請求
        search_params = {k: v for k, v in parse_qs(self.request.query).items()}
        result = self.fhir_resource.search(resource_type, search_params)
        self.write(result)

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
    return Application([
        (r"/([^/]+)/([^/]+)", FHIRResourceHandler, dict(fhir_resource=fhir_resource)),
        (r"/([^/]+)", FHIRTypeHandler, dict(fhir_resource=fhir_resource)),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("FHIR Server running on http://localhost:8888")
    IOLoop.current().start()
