要將 DICOM 轉換為 FHIR 格式，可以使用 Python 並依賴一些現有的開源工具，如 **pydicom** 來處理 DICOM 資料，以及 **FHIR libraries** (例如 `fhir.resources` 或 `FHIR Client`) 來生成 FHIR 格式。以下是如何進行 DICOM 轉 FHIR 的步驟示範：

安裝相關套件：
```bash
pip install pydicom fhir.resources
```

步驟：

1. **讀取 DICOM 檔案**：使用 `pydicom` 來讀取 DICOM 檔案。
2. **解析 DICOM**：將 DICOM 資料提取並轉換成 FHIR 相應的屬性。
3. **生成 FHIR 資源**：使用 `fhir.resources` 或其他 FHIR 庫來建立 FHIR 資源，如 `Patient`, `Observation`, `ImagingStudy` 等。

代碼範例：

```python
import pydicom
from fhir.resources.patient import Patient
from fhir.resources.imagingstudy import ImagingStudy, ImagingStudySeries

# 讀取 DICOM 檔案
ds = pydicom.dcmread("path_to_dicom_file.dcm")

# 創建 FHIR Patient 資源
patient = Patient()
patient.id = ds.PatientID
patient.name = [{
    "family": ds.PatientName.family_name,
    "given": [ds.PatientName.given_name]
}]
patient.gender = ds.PatientSex.lower()
patient.birthDate = ds.PatientBirthDate

# 創建 ImagingStudy 資源
imaging_study = ImagingStudy()
imaging_study.subject = {"reference": f"Patient/{patient.id}"}
imaging_study.started = ds.StudyDate
imaging_study.series = [
    ImagingStudySeries({
        "uid": ds.SeriesInstanceUID,
        "number": ds.SeriesNumber,
        "modality": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": ds.Modality},
    })
]

# 輸出 FHIR JSON
print(patient.json(indent=4))
print(imaging_study.json(indent=4))
```

說明：

1. **讀取 DICOM 檔案**：`pydicom.dcmread()` 用來讀取 DICOM 檔案。
2. **生成 Patient 資源**：使用 `fhir.resources.patient.Patient()` 來生成 FHIR 的病患資料。
3. **生成 ImagingStudy 資源**：這對應到影像學研究資料，其中包括 `SeriesInstanceUID`, `SeriesNumber` 等資料。

你可以依據 DICOM 檔案的結構提取更多資料，並轉換為不同的 FHIR 資源，如 `Observation`, `DiagnosticReport` 等。

這樣，你就能將 DICOM 資料轉換成符合 FHIR 標準的 JSON 形式。
