#步驟 3：使用 Streamlit 開發前端應用 Streamlit 可以用來創建一個用於展示 FHIR 資源的前端。這裡展示如何訪問並展示 Patient 資源：

# streamlit_app.py
from streamlit import title, text_input, button
from stUtil import rndrCode
from requests import get as rqstGET

API_URL = "http://localhost:8000"
token = st.text_input("Enter your token:", type="password")

title("FHIR Patient Resource Viewer")

headers = {"Authorization": f"Bearer {token}"}

if st.button("Fetch Patients"):
    response = rqstGET(f"{API_URL}/Patient", headers=headers)
    if response.status_code == 200:
        patients = response.json()
        for patient in patients:
          rndrCode([f"ID: {patient['id']}", f"Name: {patient['name']}", f"Gender: {patient.get('gender', 'N/A')}", f"Birth Date: {patient.get('birthDate', 'N/A')}"])
    else:
        st.error("Failed to fetch patients.")
"""
測試與運行 啟動 Tornado 伺服器來運行 FastAPI 應用：

python tornado_server.py
啟動 Streamlit 應用：

streamlit run streamlit_app.py
使用瀏覽器訪問 http://localhost:8501 來查看 Streamlit 前端，並通過輸入 token 來獲取患者資料。

這樣的一個架構包含了符合 SMART on FHIR 和 FHIR 規範的認證和資源訪問設計，並通過 FastAPI、Tornado 和 Streamlit 的結合構建了一個完整的 FHIR Server。
"""
