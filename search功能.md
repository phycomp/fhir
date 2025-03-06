FHIR服務器添加這些進階搜索功能
FHIR Server with Advanced Search 已經增強了搜索功能，新增了以下特性：
    1. 模糊匹配： 
curl "http://localhost:8888/Patient?name:contains=Jo" # 使用 contains 修飾符進行模糊匹配
curl "http://localhost:8888/Patient?name=Jo"  # 使用默認的模糊匹配
    2. 數值範圍搜索： 
# 大於
curl "http://localhost:8888/Observation?value:gt=100"

# 小於等於
curl "http://localhost:8888/Observation?value:le=200"
    3. 日期範圍搜索： 
# 在特定日期之後
curl "http://localhost:8888/Procedure?date:gt=2024-01-01"

# 在日期範圍內
curl "http://localhost:8888/Procedure?date:ge=2024-01-01&date:le=2024-12-31"
    4. 複合搜索條件： 
curl "http://localhost:8888/Patient?name:contains=Jo&birthDate:gt=1990-01-01"		# 組合多個條件
    5. _include 和 _revinclude： 
curl "http://localhost:8888/Patient?_include=Patient:organization" 	# 包含相關資源

curl "http://localhost:8888/Organization?_revinclude=Patient:organization"	# 包含反向參照
新增的搜索功能支援：
    1. 修飾符： 
        ◦ :exact - 精確匹配 
        ◦ :contains - 包含匹配 
        ◦ :missing - 缺失值查詢 
        ◦ :gt, :ge, :lt, :le - 範圍比較 
        ◦ :below - 層級編碼查詢 
    2. 特殊參數： 
        ◦ _include - 包含相關資源 
        ◦ _revinclude - 包含反向參照 
        ◦ _count - 分頁大小 
        ◦ _page - 頁碼 
    3. 值處理： 
        ◦ 數值比較 
        ◦ 日期比較 
        ◦ 字符串模糊匹配 
        ◦ 代碼系統匹配 
使用示例：
    1. 創建測試資源： 
# 創建病人
patient = {
    "resourceType": "Patient",
    "name": [{"given": ["John"], "family": "Doe"}],
    "birthDate": "1990-01-01",
    "organization": {"reference": "Organization/1"}
}

# 創建組織
organization = {
    "resourceType": "Organization",
    "id": "1",
    "name": "General Hospital"
}
    2. 複雜搜索： 
curl "http://localhost:8888/Patient?birthDate:gt=1990-01-01&_include=Patient:organization"	# 搜索1990年後出生的病人，包含其所屬組織

curl "http://localhost:8888/Organization/1?_revinclude=Patient:organization"	# 搜索特定組織的所有病人
您需要我解釋任何特定功能的實現細節嗎？或者您想要添加其他搜索功能？
