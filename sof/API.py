#1.3 創建 CRUD API 實現 FHIR 的 CRUD 操作，並確保需要授權的端點只允許經過授權的用戶訪問。

# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from models import Patient
from auth import get_current_user

app = FastAPI()

# 模擬的數據庫
patients_db = {}

@app.post("/Patient", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: Patient, user: dict = Depends(get_current_user)):
    patients_db[patient.id] = patient
    return patient

@app.get("/Patient/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str, user: dict = Depends(get_current_user)):
    patient = patients_db.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.put("/Patient/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, updated_patient: Patient, user: dict = Depends(get_current_user)):
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    patients_db[patient_id] = updated_patient
    return updated_patient

@app.delete("/Patient/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: str, user: dict = Depends(get_current_user)):
    if patient_id in patients_db:
        del patients_db[patient_id]
    else:
        raise HTTPException(status_code=404, detail="Patient not found")
