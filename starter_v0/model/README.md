# Hồ sơ prompt và tool theo phiên bản

Thư mục này lưu tài liệu để kể câu chuyện cải tiến `v1 → v2 → v3` khi demo.

| Phiên bản | Prompt | Tool | Nguồn đối chiếu |
|---|---|---|---|
| v1 | [v1.md](v1.md) | Giữ bộ tool v0, bổ sung quy tắc trong prompt | `runs/v1_B_base_gemini_20260729T152818925363.json`, `artifacts/version_log.csv` |
| v2 | [v2.md](v2.md) | Viết lại mô tả tool và quy ước tham số | `runs/v2_B_base_gemini_20260729T153116045600.json`, `artifacts/version_log.csv` |
| v3 | [v3.md](v3.md) | Thêm `source_check`, siết schema và ràng buộc routing | `artifacts/system_prompt.md`, `artifacts/tools.yaml` |

Lưu ý về độ chính xác: v1 và v2 không được commit thành file snapshot riêng. Nội dung trong `v1.md` và `v2.md` được tái dựng từ `version_log.csv`, hash artifact và các case eval; không khẳng định là bản sao từng ký tự. v3 là bản artifact hiện hành, có thể kiểm tra trực tiếp.
