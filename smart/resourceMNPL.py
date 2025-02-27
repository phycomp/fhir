import tornado.ioloop
from tornado.web import ApplyModel
import json
from datetime import datetime, timedelta
import uuid
from urllib.parse import parse_qs
import re
from dateutil import parser as date_parser

class FHIRResource:
    def __init__(self):
        self.resources = {}
        # 存儲資源之間的參照關係
        self.references = {}
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
        
        key = f"{resource_type}/{resource_id}"
        self.resources[key] = resource
        
        # 存儲參照關係
        self._store_references(resource_type, resource_id, data)
        
        return resource
    
    def _store_references(self, resource_type, resource_id, data):
        """存儲資源之間的參照關係"""
        def extract_references(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "reference" and isinstance(v, str):
                        # 存儲正向參照
                        referenced_type, referenced_id = v.split("/")
                        if referenced_type not in self.references:
                            self.references[referenced_type] = {}
                        if referenced_id not in self.references[referenced_type]:
                            self.references[referenced_type][referenced_id] = set()
                        self.references[referenced_type][referenced_id].add(f"{resource_type}/{resource_id}")
                    elif isinstance(v, (dict, list)):
                        extract_references(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for item in obj:
                    extract_references(item, path)
        
        extract_references(data)

    def search(self, resource_type, params):
        """增強的搜索功能"""
        try:
            page = int(params.get('_page', ['1'])[0])
            count = int(params.get('_count', ['10'])[0])
        except ValueError:
            page = 1
            count = 10

        # 處理 _include 和 _revinclude
        include_params = params.get('_include', [])
        revinclude_params = params.get('_revinclude', [])

        # 首先過濾主要資源
        matching_resources = [
            resource for key, resource in self.resources.items()
            if key.startswith(f"{resource_type}/")
        ]

        # 應用搜索條件
        filtered_resources = self._apply_search_filters(matching_resources, params)
        
        # 收集包含的資源
        included_resources = []
        if include_params or revinclude_params:
            included_resources = self._get_included_resources(
                filtered_resources,
                include_params,
                revinclude_params
            )

        # 計算分頁
        start_index = (page - 1) * count
        end_index = start_index + count
        
        # 準備分頁後的主要資源
        paged_resources = filtered_resources[start_index:end_index]
        
        # 創建Bundle資源
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(filtered_resources),
            "link": self._create_pagination_links(resource_type, params, page, count, len(filtered_resources)),
            "entry": [{"resource": resource} for resource in paged_resources] +
                    [{"resource": resource} for resource in included_resources]
        }

    def _get_included_resources(self, resources, include_params, revinclude_params):
        """處理 _include 和 _revinclude 參數"""
        included = set()
        
        # 處理 _include
        for include_param in include_params:
            # 格式: ResourceType:search-parameter
            try:
                resource_type, search_param = include_param.split(':')
                for resource in resources:
                    # 遍歷資源中的參照
                    references = self._extract_references(resource, search_param)
                    for ref in references:
                        if ref in self.resources:
                            included.add(ref)
            except ValueError:
                continue

        # 處理 _revinclude
        for revinclude_param in revinclude_params:
            # 格式: ResourceType:search-parameter
            try:
                resource_type, search_param = revinclude_param.split(':')
                for resource in resources:
                    resource_ref = f"{resource['resourceType']}/{resource['id']}"
                    if resource_type in self.references and resource_ref in self.references[resource_type]:
                        for ref in self.references[resource_type][resource_ref]:
                            if ref in self.resources:
                                included.add(ref)
            except ValueError:
                continue

        return [self.resources[ref] for ref in included]

    def _extract_references(self, resource, search_param):
        """從資源中提取參照"""
        references = set()
        
        def extract(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == search_param and "reference" in v:
                        references.add(v["reference"])
                    elif isinstance(v, (dict, list)):
                        extract(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item, path)
        
        extract(resource)
        return references

    def _apply_search_filters(self, resources, params):
        """應用搜索過濾器"""
        filtered = resources.copy()
        
        # 移除特殊參數
        special_params = {'_page', '_count', '_include', '_revinclude'}
        search_params = {k: v for k, v in params.items() if k not in special_params}
        
        for param, values in search_params.items():
            filtered = self._filter_by_param(filtered, param, values[0])
            
        return filtered

    def _filter_by_param(self, resources, param, value):
        """根據參數過濾資源"""
        filtered = []
        
        # 解析搜索修飾符
        param_parts = param.split(':')
        base_param = param_parts[0]
        modifier = param_parts[1] if len(param_parts) > 1 else None
        
        for resource in resources:
            if self._match_param(resource, base_param, value, modifier):
                filtered.append(resource)
                
        return filtered

    def _match_param(self, resource, param, value, modifier=None):
        """匹配參數值"""
        if '.' in param:
            # 處理複雜參數
            base, sub_param = param.split('.', 1)
            return self._match_complex_param(resource, base, sub_param, value, modifier)
        else:
            # 處理簡單參數
            return self._match_simple_param(resource, param, value, modifier)

    def _match_complex_param(self, resource, base, sub_param, value, modifier=None):
        """匹配複雜參數"""
        if base not in resource:
            return False
            
        if isinstance(resource[base], list):
            for item in resource[base]:
                if self._match_value(item.get(sub_param), value, modifier):
                    return True
        elif isinstance(resource[base], dict):
            return self._match_value(resource[base].get(sub_param), value, modifier)
            
        return False

    def _match_simple_param(self, resource, param, value, modifier=None):
        """匹配簡單參數"""
        if param not in resource:
            return False
        return self._match_value(resource[param], value, modifier)

    def _match_value(self, field_value, search_value, modifier=None):
        """根據不同的修飾符匹配值"""
        if field_value is None:
            return False

        # 處理不同的修飾符
        if modifier == 'exact':
            return str(field_value) == search_value
        elif modifier == 'contains':
            return search_value.lower() in str(field_value).lower()
        elif modifier == 'missing':
            return (search_value.lower() == 'true') == (field_value is None)
        elif modifier in ['gt', 'ge', 'lt', 'le']:
            return self._compare_values(field_value, search_value, modifier)
        elif modifier == 'below':
            # 處理層級式編碼
            return str(field_value).startswith(search_value)
        else:
            # 默認使用模糊匹配
            try:
                pattern = f".*{re.escape(search_value)}.*"
                return re.match(pattern, str(field_value), re.IGNORECASE) is not None
            except (TypeError, AttributeError):
                return False

    def _compare_values(self, field_value, search_value, modifier):
        """比較數值或日期"""
        try:
            # 嘗試作為數值比較
            field_num = float(field_value)
            search_num = float(search_value)
            
            if modifier == 'gt':
                return field_num > search_num
            elif modifier == 'ge':
                return field_num >= search_num
            elif modifier == 'lt':
                return field_num < search_num
            elif modifier == 'le':
                return field_num <= search_num
                
        except (ValueError, TypeError):
            try:
                # 嘗試作為日期比較
                field_date = date_parser.parse(str(field_value))
                search_date = date_parser.parse(search_value)
                
                if modifier == 'gt':
                    return field_date > search_date
                elif modifier == 'ge':
                    return field_date >= search_date
                elif modifier == 'lt':
                    return field_date < search_date
                elif modifier == 'le':
                    return field_date <= search_date
                    
            except (ValueError, TypeError):
                return False
