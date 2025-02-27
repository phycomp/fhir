from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler
import json
from datetime import datetime
import uuid
from urllib.parse import parse_qs
import re
from dateutil import parser as date_parser
from concurrent.futures import ThreadPoolExecutor
import asyncio

class BatchOperation:
    def __init__(self, fhir_resource):
        self.fhir_resource = fhir_resource
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def process_batch(self, batch_data):
        """處理批量請求"""
        if batch_data["resourceType"] != "Bundle":
            raise ValueError("Batch request must be a Bundle")

        if batch_data.get("type") not in ["batch", "transaction"]:
            raise ValueError("Bundle type must be 'batch' or 'transaction'")

        is_transaction = batch_data["type"] == "transaction"
        
        # 交易模式下的預檢查
        if is_transaction:
            try:
                self._validate_transaction(batch_data["entry"])
            except ValueError as e:
                return self._create_error_response(str(e))

        responses = []
        
        try:
            # 使用線程池處理每個請求
            loop = asyncio.get_event_loop()
            futures = []
            
            for entry in batch_data["entry"]:
                request = entry["request"]
                method = request["method"]
                url = request["url"]
                
                if method == "POST":
                    futures.append(loop.run_in_executor(
                        self.executor,
                        self._process_create,
                        entry["resource"]
                    ))
                elif method == "PUT":
                    resource_type, resource_id = self._parse_url(url)
                    futures.append(loop.run_in_executor(
                        self.executor,
                        self._process_update,
                        resource_type,
                        resource_id,
                        entry["resource"]
                    ))
                elif method == "DELETE":
                    resource_type, resource_id = self._parse_url(url)
                    futures.append(loop.run_in_executor(
                        self.executor,
                        self._process_delete,
                        resource_type,
                        resource_id
                    ))
                elif method == "GET":
                    resource_type, resource_id = self._parse_url(url)
                    futures.append(loop.run_in_executor(
                        self.executor,
                        self._process_read,
                        resource_type,
                        resource_id
                    ))
                else:
                    responses.append({
                        "status": "400",
                        "outcome": self._create_operation_outcome(
                            f"Unsupported method: {method}"
                        )
                    })
                    continue

            # 等待所有操作完成
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # 處理結果
            for result in results:
                if isinstance(result, Exception):
                    responses.append({
                        "status": "400",
                        "outcome": self._create_operation_outcome(str(result))
                    })
                else:
                    responses.append(result)

        except Exception as e:
            if is_transaction:
                # 交易模式下，任何錯誤都會導致整個操作回滾
                return self._create_error_response(
                    "Transaction failed, all changes have been rolled back"
                )
            responses.append({
                "status": "400",
                "outcome": self._create_operation_outcome(str(e))
            })

        # 創建回應Bundle
        return {
            "resourceType": "Bundle",
            "type": "batch-response",
            "entry": responses
        }

    def _validate_transaction(self, entries):
        """驗證交易請求的有效性"""
        # 檢查是否有衝突的操作
        resources = {}
        for entry in entries:
            request = entry["request"]
            url = request["url"]
            method = request["method"]
            
            if method in ["PUT", "DELETE", "GET"]:
                resource_type, resource_id = self._parse_url(url)
                key = f"{resource_type}/{resource_id}"
                
                if key in resources:
                    raise ValueError(
                        f"Conflict: Multiple operations on resource {key}"
                    )
                resources[key] = method

    def _process_create(self, resource):
        """處理創建操作"""
        try:
            result = self.fhir_resource.create(
                resource["resourceType"],
                resource
            )
            return {
                "status": "201",
                "location": f"{resource['resourceType']}/{result['id']}",
                "resource": result
            }
        except Exception as e:
            return {
                "status": "400",
                "outcome": self._create_operation_outcome(str(e))
            }

    def _process_update(self, resource_type, resource_id, resource):
        """處理更新操作"""
        try:
            result = self.fhir_resource.update(
                resource_type,
                resource_id,
                resource
            )
            if result:
                return {
                    "status": "200",
                    "resource": result
                }
            else:
                return {
                    "status": "404",
                    "outcome": self._create_operation_outcome(
                        f"Resource {resource_type}/{resource_id} not found"
                    )
                }
        except Exception as e:
            return {
                "status": "400",
                "outcome": self._create_operation_outcome(str(e))
            }

    def _process_delete(self, resource_type, resource_id):
        """處理刪除操作"""
        try:
            result = self.fhir_resource.delete(resource_type, resource_id)
            if result:
                return {"status": "204"}
            else:
                return {
                    "status": "404",
                    "outcome": self._create_operation_outcome(
                        f"Resource {resource_type}/{resource_id} not found"
                    )
                }
        except Exception as e:
            return {
                "status": "400",
                "outcome": self._create_operation_outcome(str(e))
            }

    def _process_read(self, resource_type, resource_id):
        """處理讀取操作"""
        try:
            result = self.fhir_resource.read(resource_type, resource_id)
            if result:
                return {
                    "status": "200",
                    "resource": result
                }
            else:
                return {
                    "status": "404",
                    "outcome": self._create_operation_outcome(
                        f"Resource {resource_type}/{resource_id} not found"
                    )
                }
        except Exception as e:
            return {
                "status": "400",
                "outcome": self._create_operation_outcome(str(e))
            }

    def _parse_url(self, url):
        """解析資源URL"""
        parts = url.strip('/').split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid resource URL: {url}")
        return parts[0], parts[1]

    def _create_operation_outcome(self, message):
        """創建操作結果"""
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "error",
                "code": "processing",
                "diagnostics": message
            }]
        }

    def _create_error_response(self, message):
        """創建錯誤回應"""
        return {
            "resourceType": "Bundle",
            "type": "batch-response",
            "entry": [{
                "status": "400",
                "outcome": self._create_operation_outcome(message)
            }]
        }

class BatchHandler(tornado.web.RequestHandler):
    def initialize(self, fhir_resource):
        self.fhir_resource = fhir_resource
        self.batch_processor = BatchOperation(fhir_resource)
    
    def set_default_headers(self):
        self.set_header("Content-Type", "application/fhir+json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
    
    def options(self):
        self.set_status(204)
        self.finish()
    
    async def post(self):
        try:
            batch_data = json.loads(self.request.body)
            result = await self.batch_processor.process_batch(batch_data)
            self.write(result)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(self.batch_processor._create_operation_outcome(
                "Invalid JSON"
            ))
        except Exception as e:
            self.set_status(400)
            self.write(self.batch_processor._create_operation_outcome(
                str(e)
            ))

def make_app():
    fhir_resource = FHIRResource()
    return Application([
        (r"/([^/]+)/([^/]+)", FHIRResourceHandler, dict(fhir_resource=fhir_resource)),
        (r"/([^/]+)", FHIRTypeHandler, dict(fhir_resource=fhir_resource)),
        (r"/_batch", BatchHandler, dict(fhir_resource=fhir_resource)),
    ])

if __name__ == "__main__":
    trndApp = make_app()
    trndApp.listen(8888)
    print("FHIR Server running on http://localhost:8888")
    IOLoop.current().start()    #tornado.ioloop.
