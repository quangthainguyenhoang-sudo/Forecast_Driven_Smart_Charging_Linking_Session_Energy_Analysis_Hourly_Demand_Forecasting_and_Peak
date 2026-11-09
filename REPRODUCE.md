# Hướng dẫn tái lập — Forecast-Driven Smart Charging: Linking Session Energy Analysis, Hourly Demand Forecasting and Peak Reduction on ACN-Data

> Trạng thái tài liệu: bản nháp v1.1 (9/11/2026). Chỗ ghi **[CẦN BỔ SUNG]** là thông tin chưa có trong dữ liệu dự án; không điền bằng số ước đoán. Mục 5.4 dùng quy tắc làm sạch suy ra từ dữ liệu, nhóm cần xác nhận. Tên notebook trong tài liệu là tên file trong repo GitHub; trên Kaggle tên notebook có thể khác.

## 0. Thông tin chung

| Hạng mục | Nội dung |
|---|---|
| Tên đề tài | Forecast-Driven Smart Charging: Linking Session Energy Analysis, Hourly Demand Forecasting and Peak Reduction on ACN-Data |
| Nhóm / học phần / học kỳ | Group 25 · DAP391m · Fall 2026, FPT University |
| GVHD | Lê Nhật Tùng |
| Thành viên (họ tên – vai trò) | Nguyễn Hoàng Quang Thái – ML Engineer · Nguyễn Minh Phương – Data Analyst |
| Repo | https://github.com/quangthainguyenhoang-sudo/Forecast_Driven_Smart_Charging_Linking_Session_Energy_Analysis_Hourly_Demand_Forecasting_and_Peak · tag/commit: `v1.0` / `8fe9586cda451d8d2d82b70c8d332de7fbcdb9f7` |
| Dữ liệu đã xử lý | Kaggle Dataset `quangthai0406/acn-cleaned-sessions-dap391m`, hiện là Version 4, 17.9 MB (2 file: `acn_data(cleaned)_fixed.xlsx` 8.78 MB và `acn_data_full_original.xlsx`; bản cleaned trên Kaggle đang tên `_fixed`, khác tên `acn_data(cleaned).xlsx` mà các lệnh trong tài liệu và glob của notebook dùng, cần kiểm tra lại cho khớp **[CẦN XÁC NHẬN]**). Hiện ở chế độ **Private** (người ngoài nhóm mở link sẽ thấy lỗi 404), nên người chấm không tải được; cần chuyển sang công khai hoặc cho người chấm quyền truy cập trước khi nộp **[CẦN QUYẾT ĐỊNH]**. |
| Checkpoint | Không có. Dự án không phát hành checkpoint; mọi kết quả được tạo lại bằng notebook (xem Mục 8). |
| Cập nhật / phiên bản tài liệu | 9/11/2026 · v1.1 |

## 1. Quick Start

Dự án chạy hoàn toàn bằng notebook trên Kaggle (không có CLI). Các bước từ máy trống:

1. Tạo tài khoản Kaggle, mở Dataset `acn-cleaned-sessions-dap391m` (link ở Mục 0) và chọn **New Notebook**, hoặc upload các notebook (`.ipynb` ở thư mục gốc của repo) rồi **Add Input** là Dataset này.
2. Bật Internet; chọn accelerator **None (CPU)** cho notebook RQ1, RQ2 baseline, aggregate, RQ3 và **GPU T4** cho `lstm` và `hybrid`.
3. Chạy theo thứ tự ở Mục 7 (mỗi notebook: Restart & Run All). Notebook tự tìm file dữ liệu bằng `glob` trong `/kaggle/input/**/acn_data(cleaned).xlsx`, đọc sheet `full_data`, và ghi kết quả vào `/kaggle/working`.
4. Kiểm tra nhanh pipeline: đặt `FAST_MODE = True` ở cell đầu mỗi notebook (smoke test, số trial/epoch/seed giảm mạnh; kết quả không dùng để so với báo cáo).
5. So số trong output với bảng ở Mục 8 và Mục 10.

Kết quả mong đợi của lần chạy đầy đủ (Test, trích từ báo cáo):

- RQ1: Linear regression MAE 6.011 / RMSE 7.898 / R² 0.160; XGBoost 6.011 / 7.868 / 0.167; LightGBM 6.017 / 7.866 / 0.167 (Table 2).
- RQ2: Hybrid MAE site 1, H=1 là 2.44 (run 1) và 2.67 (run 2) kWh/giờ (Table 4).
- RQ3: Hybrid giảm đỉnh trung bình theo ngày 24.35% ở site 1 và 28.97% ở site 2 (Table 6).

Thời gian dự kiến: chưa có đủ số liệu cho toàn bộ pipeline, xem Mục 3.

## 2. Cấu trúc thư mục

Repo (GitHub, thẻ v1.0):

```
Forecast_Driven_Smart_Charging_.../
├── README.md                    # mô tả dự án, bảng notebook, quy tắc chia tập và làm sạch
├── REPRODUCE.md                 # tài liệu này (chưa thêm vào repo)
├── linear_regression.ipynb      # RQ1: Linear regression (elastic net), baseline tra bảng
├── xgboost.ipynb                # RQ1: XGBoost
├── lightgbm.ipynb               # RQ1: LightGBM
├── persistence.ipynb            # RQ2: persistence
├── seasonal_naive.ipynb         # RQ2: seasonal naive
├── lstm.ipynb                   # RQ2: LSTM (GPU)
├── hybrid.ipynb                 # RQ2: XGBoost + LightGBM + GRU, stacking (GPU)
├── ridge_meta_learner.ipynb     # RQ2: bóc tách cách kết hợp
├── rq2_aggregate.ipynb          # RQ2: gom kết quả, bootstrap theo tuần, xuất siêu tham số
├── rq3_smart_charging.ipynb     # RQ3: mô phỏng lập lịch sạc
└── scripts/
    ├── rq1_group_importance_v3.py   # Table 3: permutation theo nhóm
    ├── rq1_oof_importance.py        # Table 3: out-of-fold
    ├── clean_acn_sessions.py        # tạo lại bản cleaned từ dữ liệu gốc
    └── make_fig2_fig3.py            # Fig. 2 và Fig. 3
```

Hai script cho Table 3 nằm trong thư mục `scripts/` của repo: `rq1_group_importance_v3.py` (permutation theo nhóm, drop, only) và `rq1_oof_importance.py` (permutation out-of-fold, bootstrap theo ngày, hoán vị có điều kiện). Đặt biến môi trường `ACN_XLSX` là đường dẫn file `acn_data(cleaned).xlsx` (mặc định là file cùng tên trong thư mục hiện tại) và `RQ1_OUT` là thư mục ghi kết quả (mặc định là thư mục hiện tại). Chạy `rq1_group_importance_v3.py` trước, rồi `rq1_oof_importance.py`; script thứ hai đọc script thứ nhất trong cùng thư mục. Ngoài ra `scripts/clean_acn_sessions.py` tạo lại bản cleaned từ dữ liệu gốc (Mục 5.4) và `scripts/make_fig2_fig3.py` vẽ Fig. 2 và Fig. 3 (Mục 10).

Các notebook `rq1-session-factors` và `rq2-comparison-figures` của phiên bản cũ không có trong repo GitHub và không dùng để tái lập kết quả hiện tại.

## 3. Yêu cầu phần cứng và phần mềm

| Hạng mục | Môi trường đã dùng (Kaggle) | Tối thiểu khuyến nghị |
|---|---|---|
| Hệ điều hành | Linux x86_64, glibc 2.39 (kernel 6.18.x theo log) | Linux/Windows/macOS, chạy trên Kaggle là đơn giản nhất |
| CPU / RAM | Kaggle CPU session, **chưa ghi số nhân/RAM** | Máy chạy được `pandas`, `xgboost`, `lightgbm` với 60,105 dòng |
| GPU | Tesla T4 cho `lstm` và `hybrid` (theo metadata notebook) | GPU ≥ 8 GB hoặc Colab T4; các notebook còn lại không cần GPU |
| CUDA / cuDNN / driver | **Chưa ghi** | — |
| Python | 3.13.15 (theo log) | 3.13.x |
| Thư viện đã ghi trong log | scikit-learn 1.6.1, XGBoost 3.4.1, LightGBM 4.6.0, Optuna 5.0.0, TensorFlow 2.20.0 (lstm, hybrid) | Dùng đúng các bản này |
| Thư viện chưa ghi | numpy, pandas, scipy, matplotlib, seaborn, Keras, openpyxl | Xem Mục 4 để in phiên bản |
| Thời gian chạy đã ghi | XGBoost: giai đoạn 1 (60 trial) 16.2 phút, giai đoạn 2 (40 trial) 16.0 phút; Linear regression: 17.2 và 10.4 phút | — |
| Thời gian chưa ghi | LightGBM (RQ1), toàn bộ RQ2 và RQ3 | — |

## 4. Cài đặt môi trường

Môi trường đã dùng là image mặc định của Kaggle tại thời điểm chạy (2/11/2026); notebook không cài thêm gói bằng `pip` (không có `!pip install`). Dự án **chưa có** `requirements.txt` hoặc `environment.yml` khóa phiên bản.

Để tái lập chính xác, chạy cell sau ở đầu một notebook trên Kaggle và lưu kết quả vào `requirements_kaggle.txt` trong repo:

```python
import sys, importlib.metadata as m
print(sys.version.split()[0])
for p in ["numpy","pandas","scipy","scikit-learn","xgboost","lightgbm","optuna",
          "tensorflow","keras","matplotlib","seaborn","openpyxl"]:
    try: print(p, m.version(p))
    except m.PackageNotFoundError: print(p, "not installed")
```

Mong đợi: Python 3.13.15, scikit-learn 1.6.1, XGBoost 3.4.1, LightGBM 4.6.0, Optuna 5.0.0, TensorFlow 2.20.0 (khớp log). Phiên bản các thư viện mà log notebook không ghi, lấy bằng cách chạy cell trên Kaggle ngày 9/11/2026 (image mặc định lúc đó: Python 3.13.18, TensorFlow 2.21.0): numpy 2.1.3, pandas 2.3.3, scipy 1.16.3, matplotlib 3.10.0, seaborn 0.13.2, Keras 3.13.2, openpyxl 3.1.5. Cùng lần chạy đó scikit-learn 1.6.1, XGBoost 3.4.1, LightGBM 4.6.0, Optuna 5.0.0 trùng với log ngày 2/11, nhưng Python và TensorFlow đã đổi (log 2/11: Python 3.13.15, TensorFlow 2.20.0). Vì vậy bảy số trên là của image ngày 9/11, nên có thể lệch patch so với image ngày chạy thí nghiệm **[CẦN XÁC NHẬN]** (cách chắc chắn: chạy cell in phiên bản ở cuối mỗi notebook khi chạy lại). Không có API key hay biến môi trường nào cần thiết.

## 5. Dữ liệu

### 5.1 Nguồn và giấy phép
- Nguồn: ACN-Data (Caltech và JPL), https://ev.caltech.edu/dataset ; bài cần trích dẫn: Lee, Z. J., Li, T., Low, S. H. (2019), *ACN-Data: Analysis and Applications of an Open EV Charging Dataset*, Proc. 10th Int. Conf. on Future Energy Systems (e-Energy '19).
- Trang nguồn (https://ev.caltech.edu/dataset, kiểm tra ngày 9/11/2026) không nêu giấy phép; chỉ yêu cầu người dùng đăng ký để dùng API và trích dẫn bài trên khi công bố. Dataset Kaggle của nhóm đang để License = Unknown. Vì trang nguồn không cấm cũng không cho phép rõ ràng việc phân phối lại, đề xuất: công khai chỉ bản cleaned (kèm trích dẫn Lee, Li và Low 2019, ghi rõ nguồn Caltech/JPL/PowerFlex và chọn License = "Other (specified in description)"), hoặc để Private và cho người chấm truy cập; nếu muốn chắc chắn thì hỏi ban quản trị ACN-Data (địa chỉ liên hệ trên trang nguồn). Quyết định thuộc nhóm **[CẦN QUYẾT ĐỊNH]**.
- Ngày tải dữ liệu gốc: 30/9/2026 (nhóm khai báo). File gốc trong thư mục dự án được lưu ngày 1/10/2026 và dữ liệu kết thúc ngày 13/9/2021.

### 5.2 Mô tả dữ liệu (đo trực tiếp từ hai file)
| | Dữ liệu gốc (`acn_data_full_original.xlsx`) | Dữ liệu cleaned v3 (`acn_data(cleaned).xlsx`) |
|---|---|---|
| Số phiên | 66,745 | 60,105 |
| Theo site | 1: 33,638 · 2: 31,424 · 19: 1,683 | 1: 29,482 · 2: 29,206 · 19: 1,417 |
| Số cột | 13 | 21 (sheet `full_data`) |
| Giá trị thiếu | `userInputs` 18,313; `userID` 18,313; `doneChargingTime` 4,146 | không có |
| Khoảng thời gian | 25/4/2018 – 13/9/2021 | cùng khoảng |

Cột của bản cleaned: sessionID, stationID, siteID, connectionTime, disconnectTime, kWhDelivered, doneChargingTime, hour, day_of_week, month, month_sin, month_cos, is_weekend, seasonal, hour_sin, hour_cos, day_of_year, week_of_year, is_holiday, charging_duration, parking_duration. `is_holiday` đánh dấu ngày lễ liên bang Mỹ, chiếm 1.23% số phiên.

### 5.3 Cách lấy dữ liệu và checksum
Tải từ Dataset Kaggle ở Mục 0 (hoặc nút **Add Input** trong notebook). Checksum SHA-256 của file trong Dataset (đã kiểm tra khớp với file trong thư mục dự án):

```
sha256sum "acn_data(cleaned).xlsx"
# d19ea1b37cf7b8de8f4a4314a8bffffd9b2d7b79558f99acc2049c1f62334c0b
sha256sum acn_data_full_original.xlsx
# 6345ed9347ce0d48a3a6cc9e9352ac4168935d1767b7629f9cf4d1095d942cae
```

### 5.4 Tiền xử lý
Bản cleaned v3 được tạo bằng các quy tắc dưới đây. Đây là quy tắc suy ra bằng cách so sánh bản gốc với bản cleaned, không phải mã gốc của nhóm **[CẦN XÁC NHẬN]**. Script scripts/clean_acn_sessions.py áp dụng chúng lên file gốc và tạo lại đúng bản cleaned: cùng 60,105 phiên và cùng 21 cột (sai khác về thời gian dưới 1 ms; thứ tự các phiên kết nối cùng một giây có thể khác). Lệnh chạy và kiểm tra: `python scripts/clean_acn_sessions.py acn_data_full_original.xlsx out.xlsx --verify "acn_data(cleaned).xlsx"`. Số phiên dưới đây là số còn lại sau mỗi bước, áp dụng lần lượt.

| Bước | Quy tắc | Phiên còn lại | Bị loại |
|---|---|---|---|
| 0 | Dữ liệu gốc | 66,745 | – |
| 1 | kWhDelivered trong khoảng (0.5; 40) | 64,761 | 1,984 |
| 2 | Thời gian đỗ (disconnect − connection) từ 5 phút đến 48 giờ | 64,654 | 107 |
| 3 | Phiên thiếu doneChargingTime được gán = connection + kWh / 3.1504 kW; sau đó thời gian sạc phải từ 5 phút đến 24 giờ | 64,591 | 63 |
| 4 | Bỏ phiên có doneChargingTime muộn hơn disconnect trên 61 giây; các phiên còn lại cắt doneChargingTime về disconnect | 62,883 | 1,708 |
| 5 | Bỏ phiên kết nối từ 1/4/2020 đến 31/1/2021 (ngày địa phương) | 60,105 | 2,778 |

Ghi chú về các quy tắc:

1. Bước 5 loại 3,157 phiên có thật của bản gốc (site 1: 2,363; site 2: 599; site 19: 195; trong đó 2,778 phiên còn lại sau các bước 1–4). Vì vậy khoảng "mất dữ liệu" từ 31/3/2020 đến 1/2/2021 trong chuỗi theo giờ do bước làm sạch này tạo ra, không phải do thiết bị ngừng ghi. Lý do loại theo nhóm: giai đoạn đại dịch COVID-19. Paper hiện viết đây là "outage" của việc thu thập dữ liệu, cần sửa lại cho khớp (xem Mục 11).
2. Hằng số 3.1504 kW (3.150423511) là giá trị quan sát được trong bản cleaned: mọi phiên được gán doneChargingTime (2,129 phiên) có kWh / charging_duration bằng đúng giá trị này. Đã kiểm tra trên bản gốc (9/11/2026): tổng kWh / tổng giờ sạc của các phiên có doneChargingTime và kWh trong (0.5; 40) là 3.15005 (60,784 phiên), lệch 0.012% so với 3.150423511; thử mọi tổ hợp các bộ lọc còn lại cũng không ra đúng giá trị. Vậy hằng số này xấp xỉ "tổng kWh / tổng giờ sạc sau khi lọc kWh", nhưng tập phiên chính xác để tính ra nó không tái tạo được. Với tập dữ liệu hiện tại, giá trị chỉ dùng để gán 2,129 phiên thiếu doneChargingTime, nên script dùng đúng hằng số này.
3. Các cột thời gian của bản cleaned dùng đồng hồ UTC−7 cố định, không chuyển sang UTC−8 vào mùa đông. Trong các tháng mùa đông, giờ trong bảng muộn hơn đồng hồ thực 1 giờ so với chuỗi thời gian có kèm múi giờ của bản gốc. Các cột hour, hour_sin, hour_cos, day_of_week, is_holiday… đều tính từ đồng hồ này, và chuỗi theo giờ cũng dựng từ các cột thời gian đó.
4. Mô tả làm sạch trong README cũ (bỏ trùng theo (stationID, connectionTime), kWh ≤ 0, ngắt kết nối trước khi cắm) chỉ loại 1 phiên trên dữ liệu gốc, nên không giải thích được 6,640 phiên bị loại; README được sửa theo bảng trên.

Các bước còn lại của tiền xử lý:

5. Với RQ2 và RQ3 chỉ giữ site 1 và 2: 29,482 + 29,206 = 58,688 phiên; bỏ 1 bản ghi trùng (stationID, connectionTime) còn 58,687.
6. Chuỗi theo giờ cho mỗi site: năng lượng của phiên được trải đều trên các giờ từ lúc cắm đến lúc sạc xong, tổng năng lượng được bảo toàn. Không xóa giờ nào, chỉ gắn cờ và không dùng làm mục tiêu: mất dữ liệu (`in_gap`: ≥ 7 ngày liên tiếp bằng 0), 672 giờ sau mỗi đợt mất dữ liệu (`post_gap`), 672 giờ đầu của mỗi chuỗi (warm-up).
7. 16 đặc trưng chung của RQ2: lag_H, lag_D, lag_168, roll_mean_24, roll_max_24, seasonal_mean_4w, n_plugged_lagH, n_charging_lagH, n_arrivals_lagH, charging_share_lagH, hour_sin, hour_cos, dow_sin, dow_cos, is_weekend, is_holiday; mỗi giá trị chỉ dùng thông tin đến giờ t−H.
8. RQ1 dùng 9 đặc trưng thuộc 5 nhóm: hour (hour_sin, hour_cos), day of week (day_of_week, is_weekend), location (siteID, stationID), month (month, seasonal), holiday (is_holiday).

Phần dựng chuỗi theo giờ và các đặc trưng nằm trong từng notebook (cell đọc dữ liệu); phần làm sạch phiên nằm trong scripts/clean_acn_sessions.py.

### 5.5 Chia tập
Chia theo thời gian, dùng chung cho cả ba câu hỏi: Train đến 31/10/2019 23:00; Validation đến 15/1/2020 23:00; Test từ 16/1/2020 đến hết dữ liệu (13/9/2021). Không có file chỉ số riêng; ranh giới được cố định trong notebook (`TRAIN_END`, `VAL_END`).

| | Train | Val | Test |
|---|---|---|---|
| RQ1 (phiên, site 1, 2, 19) | 42,945 | 5,173 | 11,987 |
| RQ2/RQ3, giờ mục tiêu hợp lệ, site 1 | 9,452 | 1,824 | 5,686 |
| RQ2/RQ3, giờ mục tiêu hợp lệ, site 2 | 12,644 | 1,824 | 6,526 |

Chọn siêu tham số của RQ1 bằng 5 fold expanding window (mỗi fold validation 2 tháng) trên phần Train+Val; Test chỉ dùng một lần để báo cáo.

## 6. Cấu hình và siêu tham số

Siêu tham số nằm trong cell cấu hình của từng notebook (chưa có file YAML). Giá trị tốt nhất đã chọn được xuất ra file:

| Mô hình | Phương pháp tìm | Chọn trên | File kết quả |
|---|---|---|---|
| Linear regression, XGBoost, LightGBM (RQ1) | Optuna TPE hai giai đoạn: 60 + 40 trial; top 5 cấu hình chạy lại với 3 seed (42, 202, 1337) | CV RMSE trung bình trên 5 fold expanding window | `{tag}_best_hyperparameters.json`, `{tag}_tuning_trials.csv` |
| Seasonal naive (RQ2) | Grid đầy đủ: m ∈ {24, 48, 72, 96, 120, 144, 168, 336} × gộp ∈ {last, mean2, mean3, median3} | Val MAE (run 1), Train+Val (run 2) | `rq2_all_hyperparameters.json` |
| Persistence (RQ2) | Grid: gộp (mean, median, ewm) × hệ số λ (0.6–1.2), thực hiện trong notebook riêng `persistence-tune` (nguồn ghi trong `rq2_all_hyperparameters.json`); `persistence.ipynb` dán cấu hình đã chọn vào để chạy | Val MAE | `rq2_all_hyperparameters.json` |
| LSTM (RQ2) | Optuna TPE 20 trial, 25 epoch tune; 3 seed (42, 43, 44) | Val MAE | `rq2_all_hyperparameters.json` |
| Hybrid (RQ2) | Optuna TPE: XGBoost 40, LightGBM 40, GRU 15 trial; stacking bằng Ridge không âm | Val MAE | `rq2_all_hyperparameters.json` |
| Lập lịch RQ3 | κ ∈ [0.5, 1.0] chọn trên Val cho từng nguồn dự báo | Val | `rq3_kappa_selection.csv` |

Giá trị tốt nhất của RQ1 (từ log):
- XGBoost: n_estimators 950, learning_rate 0.007065, max_depth 8, min_child_weight 2, subsample 0.8170, colsample_bytree 0.9556, colsample_bylevel 0.6452, gamma 1.24e-08, reg_alpha 0.001471, reg_lambda 0.006304, grow_policy lossguide, max_leaves 13, max_cat_to_onehot 13, max_bin 256, enable_categorical True, random_state 42.
- LightGBM: n_estimators 350, learning_rate 0.016457, num_leaves 10, max_depth 5, min_child_samples 39, subsample 0.608259, colsample_bytree 0.910422, reg_alpha 0.00074, reg_lambda 7.897344, min_split_gain 0.23136, cat_smooth 3.7989, cat_l2 1.27738, max_cat_threshold 31.
- Linear regression: elastic net, alpha 0.001121, l1_ratio 0.6867, station_level True (dùng stationID), giờ bằng (hour_sin, hour_cos), có tương tác site × giờ, chuẩn hoá biến số, drop_first True.

Toàn bộ siêu tham số RQ2 theo từng site, horizon và run nằm trong `rq2_all_hyperparameters.json` (do `rq2_aggregate` xuất; fingerprint benchmark 4b6e6ce304c1) và trong bảng siêu tham số của bài báo (Table 1).

## 7. Huấn luyện

Thứ tự chạy (mỗi notebook độc lập trừ các phụ thuộc ghi ở cột cuối). Mọi notebook ghi kết quả vào `/kaggle/working`.

| # | Notebook | Máy | Đầu ra chính | Phụ thuộc |
|---|---|---|---|---|
| 1 | `linear_regression` | CPU | `linear-regression_best_hyperparameters.json`, `_test_tuned.csv`, `_cv_folds_tuned.csv`, `_tuning_trials.csv` | Dataset |
| 2 | `xgboost` | CPU | cùng bộ file với tag `xgboost` | Dataset |
| 3 | `lightgbm` | CPU | cùng bộ file với tag `lightgbm` | Dataset |
| 4 | `seasonal_naive` | CPU | `*_predictions.csv`, `*_results_long.csv`, `*_grid.csv` | Dataset |
| 5 | `persistence` | CPU | `*_predictions.csv`, `*_results_long.csv` | Dataset |
| 6 | `lstm` | GPU T4 | `lstm_tuning_trials.csv`, `lstm_hp_importance.csv`, dự báo | Dataset |
| 7 | `hybrid` | GPU T4 | `hybrid_base_predictions.csv`, `hybrid_stacking_weights.csv`, `hybrid_tuning_trials.csv` | Dataset |
| 8 | `ridge_meta_learner` | CPU | `*_comparison_test.csv`, `*_weights.csv` | Output của #7 (Add Input) |
| 9 | `rq2_aggregate` | CPU | `rq2_combined_predictions.csv`, `rq2_results_all_models_test.csv`, `rq2_paired_vs_hybrid.csv`, `rq2_all_hyperparameters.json` | Output của #4–#7 |
| 10 | `rq3_smart_charging` | CPU | `rq3_results.csv`, `rq3_kappa_selection.csv`, `rq3_summary.json`, `paper_figures/` | `rq2_combined_predictions.csv` từ #9 |

Table 3 (RQ1, mức quan trọng của yếu tố): chạy `rq1_group_importance_v3.py` (permutation theo nhóm, drop, only), rồi `rq1_oof_importance.py` (out-of-fold, 5 fold expanding window, 20 hoán vị, bootstrap 1,000 lần theo ngày). Kết quả ghi ở `table3_oof.json` và `group_importance_v3.csv`.

Chế độ rút gọn: đặt `FAST_MODE = True` (mọi notebook có cờ này). Với LSTM và Hybrid, chế độ này đổi sang 2 trial, 2 epoch, 1 seed và N_BOOT = 100. Kết quả rút gọn **không** khớp báo cáo; mục đích chỉ là kiểm tra code chạy được trong thời gian ngắn.

Huấn luyện lại (run 2): ở RQ2, run 2 huấn luyện lại trên Train+Val với cấu hình của run 1 (với Seasonal Naive và Persistence thì tìm lại trên Train+Val), đánh giá trên cùng Test. Không có cơ chế `--resume`; notebook phải chạy một mạch.

## 8. Đánh giá và suy luận

Không có checkpoint để đánh giá riêng. Mỗi notebook huấn luyện và đánh giá trong cùng một lần chạy; bước “đánh giá” là cell cuối của notebook (RQ1: “Benchmark cuối trên Test”; RQ2: cell xuất `results_long`/`results_wide`; RQ3: cell xuất `rq3_results.csv`). Dự báo Test của RQ2 được lưu trong `rq2_combined_predictions.csv` nên RQ3 chạy lại được mà không cần huấn luyện lại RQ2.

Metric: MAE, RMSE, R², WAPE, MASE, Bias, P90F1, PeakMAE (RQ2 và RQ1); khoảng tin cậy 95% bằng bootstrap theo tuần (1,000 lần) cho RQ2 và RQ3, theo ngày cho Table 3. RQ3 báo cáo mức giảm đỉnh trung bình theo ngày so với sạc không điều khiển.

Kết quả mong đợi (Test):

**RQ1 — Table 2** (RMSE, MAE tính bằng kWh mỗi phiên; 11,987 phiên Test)

| Mô hình | CV RMSE (±std) | CV mặc định | Test MAE | Test RMSE | Test R² |
|---|---|---|---|---|---|
| Linear regression | 8.074 ± 0.253 | 8.263 | 6.011 | 7.898 | 0.160 |
| XGBoost | 8.046 ± 0.253 | 8.482 | 6.011 | 7.868 | 0.167 |
| LightGBM | 8.090 ± 0.252 | 8.120 | 6.017 | 7.866 | 0.167 |

**RQ2 — Table 4** (MAE, kWh mỗi giờ, run 1 / run 2)

| | Hybrid | LSTM | Persistence | Seasonal naive |
|---|---|---|---|---|
| Site 1, H=1 | 2.44 / 2.67 | 2.65 / 2.80 | 4.47 / 4.47 | 6.81 / 6.78 |
| Site 1, H=24 | 5.92 / 6.84 | 7.58 / 7.72 | 9.27 / 9.41 | 6.81 / 6.78 |
| Site 2, H=1 | 1.34 / 1.26 | 1.61 / 1.64 | 1.81 / 1.84 | 2.61 / 2.61 |
| Site 2, H=24 | 2.55 / 2.22 | 2.79 / 2.65 | 2.81 / 2.94 | 2.61 / 2.61 |

**RQ3 — Table 6** (giảm đỉnh trung bình theo ngày, %, run 1, κ chọn trên Val)

| Nguồn đỉnh | Site 1 | Site 2 |
|---|---|---|
| Hybrid | 24.35 [20.95, 27.10] (κ 0.7) | 28.97 [23.85, 33.02] (κ 0.6) |
| LSTM | 18.61 [13.76, 22.36] | 26.70 [22.24, 30.22] |
| Seasonal naive | 19.83 [14.73, 24.27] | 22.98 [19.57, 25.68] |
| Persistence (tuned) | 11.26 [7.93, 14.34] | 22.73 [19.11, 25.77] |
| Đỉnh tuần trước | 16.51 [12.16, 20.72] | 24.58 [21.00, 27.60] |
| Đỉnh thật (oracle) | 34.40 [31.91, 36.14] | 37.74 [33.32, 40.90] |

Mọi phiên đều nhận đủ năng lượng và không trễ giờ rời đi trong các trường hợp trên.

Không có suy luận trên dữ liệu mới và không có demo.

## 9. Kiểm soát ngẫu nhiên và tính tất định

- Seed cơ sở: `SEED = 42` ở mọi notebook; đặt `random.seed`, `np.random.seed` và `keras.utils.set_random_seed` (notebook LSTM, Hybrid).
- RQ1: top 5 cấu hình tốt nhất chạy lại với 3 seed (42, 202, 1337); Linear regression là tất định (std 0). Bootstrap dùng `numpy.random.default_rng`.
- LSTM và GRU: 3 seed cho mỗi lần huấn luyện cuối (`SEED + 0, 1, 2` tức 42, 43, 44), lấy trung bình dự báo. XGBoost và LightGBM trong Hybrid dùng `random_state = 42`.
- Bootstrap RQ2 và RQ3: 1,000 lần, khối theo tuần.
- Notebook **không** bật `tf.config.experimental.enable_op_determinism` hay `torch.use_deterministic_algorithms`; XGBoost chạy bằng GPU (`device='cuda'`) trong Hybrid. Kết quả trên GPU khác loại hoặc khác phiên bản CUDA/TensorFlow có thể lệch nhẹ.
- Không có file `seeds_summary.csv`; kết quả theo từng seed của top 5 cấu hình RQ1 nằm trong `{tag}_stability_check.csv`.
- **[CẦN XÁC NHẬN] Ngưỡng sai số chấp nhận (đề xuất):** phần tất định (Seasonal naive, Persistence, Linear regression, RQ3 khi dùng đúng `rq2_combined_predictions.csv`) phải khớp đến 3 chữ số thập phân; XGBoost và LightGBM chạy CPU lệch tối đa 0.5% tương đối trên MAE/RMSE; LSTM và Hybrid chạy GPU lệch tối đa 1% tương đối trên MAE. Các ngưỡng này do nhóm khai báo; mình chưa kiểm chứng bằng nhiều lần chạy.

## 10. Ánh xạ kết quả ↔ báo cáo

Số thứ tự bảng và hình theo thứ tự xuất hiện trong bài báo; đối chiếu lại với bản PDF cuối trước khi nộp.

| Bảng/Hình | Nội dung | Notebook hoặc script | File output | Ghi chú |
|---|---|---|---|---|
| Table 1 (`tab:hyper`) | Siêu tham số đã chọn | RQ1: 3 notebook RQ1; RQ2: `rq2_aggregate` | `*_best_hyperparameters.json`, `rq2_all_hyperparameters.json` | — |
| Table 2 (`tab:rq1`) | Mô hình cấp phiên và baseline tra bảng | `linear_regression`, `xgboost`, `lightgbm` | `*_test_tuned.csv`, `*_cv_folds_tuned.csv`, `*_gain_vs_default.csv` | Các dòng tra bảng (Global mean, Site mean, Site and weekday, Site and hour, Site, hour and weekday) nằm trong `linear_regression` |
| Table 3 (`tab:imp`) | Mức quan trọng của yếu tố, out-of-fold | `rq1_group_importance_v3.py`, `rq1_oof_importance.py` | `table3_oof.json`, `group_importance_v3.csv` | Script nằm trong `scripts/` của repo; hoán vị có điều kiện là cách cài đặt của nhóm |
| Table 4 (`tab:rq2`) | Dự báo theo giờ | `rq2_aggregate` | `rq2_results_all_models_test.csv`, `rq2_paired_vs_hybrid.csv` | — |
| Table 5 (`tab:abl`) | Base learner và bốn cách kết hợp | `hybrid`, `ridge_meta_learner` | `hybrid_base_vs_hybrid_test.csv`, `*_comparison_test.csv` | — |
| Table 6 (`tab:rq3`) | Giảm đỉnh khi sạc thông minh | `rq3_smart_charging` | `rq3_results.csv`, `rq3_results_full.csv`, `rq3_summary.json` | — |
| Fig. 1 (`fig:pipeline`) | Sơ đồ pipeline | Vẽ tay bằng draw.io (`fig_project_pipeline_v2.drawio`, Google Drive) | `fig_pipeline_v3.png` | Xuất PNG ở giao diện sáng |
| Fig. 2 (`fig:eda`) | Mô tả dữ liệu | `scripts/make_fig2_fig3.py` (mã ô vẽ hình lấy từ notebook phiên bản 23/10) | `fig2_data_description.png` | Chạy lại trên bản cleaned v3 cho ảnh trùng từng byte với ảnh trong bài. |
| Fig. 3 (`fig:rq2`) | Tải và sai số theo giờ trong ngày | `scripts/make_fig2_fig3.py` (đọc `rq2_combined_predictions.csv`: Test, run 1, H = 24) | `fig4_rq2_hour_profile.png` | Số liệu vẽ hình trùng số liệu tính lại từ `rq2_combined_predictions.csv` (sai khác dưới 5e-5). Ảnh trong bài vẽ bằng matplotlib thường (`make_figs.py`); script vẽ lại theo kiểu seaborn nên khác kiểu dáng, cùng số liệu. |
| Fig. 4 (`fig:plrr`) | PLRR của đỉnh trung bình theo ngày | `rq3_smart_charging` | `paper_figures/fig5_rq3_plrr.png` | — |
| Fig. 5 (`fig:overload`) | Giảm năng lượng vượt giới hạn lưới | `rq3_smart_charging` | `paper_figures/fig6_rq3_overload.png` | — |

## 11. Hạn chế và xử lý sự cố

**Phần chưa tái lập hoàn toàn:**
- Các quy tắc làm sạch dữ liệu (66,745 → 60,105 phiên) được suy ra từ dữ liệu, không phải mã gốc của nhóm; script tái tạo khớp 100% với bản cleaned (xem 5.4). Lý do loại các phiên từ 1/4/2020 đến 31/1/2021 chưa được ghi lại.
- Cấu hình Persistence được tìm trong notebook `persistence-tune`, hiện chưa nằm trong repo (đang ở thư mục chờ xóa của dự án); cần đưa vào repo hoặc ghi lại cách tìm.
- Dataset Kaggle đang Private và chưa có License (xem Mục 5.1).
- Chưa có `requirements.txt`; phiên bản numpy, pandas, TensorFlow chưa ghi.
- Fig. 2 tạo lại khớp từng byte bằng scripts/make_fig2_fig3.py; Fig. 3 tạo lại cùng số liệu nhưng khác kiểu vẽ (xem Mục 10).
- Các cột thời gian của bản cleaned dùng đồng hồ UTC−7 cố định (xem 5.4); tác động lên kết quả chưa được kiểm tra.
- Table 3 được tính lại ngày 3/11/2026 với siêu tham số tuned hiện hành của cả ba mô hình (trước đó script còn dùng cấu hình cũ của Linear và XGBoost). Lần chạy này dùng XGBoost 3.4.1, LightGBM 4.7.0, scikit-learn 1.9.1 (khác môi trường Kaggle: LightGBM 4.6.0, scikit-learn 1.6.1). Kiểm tra chéo: RMSE test của Linear (7.8983) và XGBoost (7.8678) khớp đến 4 chữ số với notebook Kaggle; LightGBM 7.8669 so với 7.8663.
- Dự án cung cấp notebook, không có CLI hay `Makefile`; kết quả RQ2 và RQ3 phụ thuộc chuỗi output giữa các notebook trên Kaggle.
- Ba notebook RQ1 (`linear_regression`, `xgboost`, `lightgbm`) đã được chạy lại trên dữ liệu cleaned v3 (60,105 phiên); Table 2 của bài lấy từ lần chạy này.
- Kết quả có thể lệch nhẹ khi đổi phần cứng GPU hoặc phiên bản thư viện (Mục 9).
- Giới hạn lưới của RQ3 là giả định của nghiên cứu (phân vị 95 của tải theo giờ trong Train), không phải thông số thật của máy biến áp.

**Lỗi thường gặp:**

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| Notebook không tìm thấy dữ liệu | Chưa Add Input Dataset, hoặc Dataset đang Private với tài khoản khác | Add Input đúng Dataset ở Mục 0; kiểm tra file `acn_data(cleaned).xlsx` nằm dưới `/kaggle/input/` |
| `ridge_meta_learner`, `rq2_aggregate` hoặc `rq3_smart_charging` báo thiếu file dự báo | Chưa thêm output của notebook trước làm Input | Chạy và lưu (Save Version) notebook trước, rồi Add Input là output đó |
| Hết bộ nhớ GPU khi chạy LSTM/Hybrid | GPU nhỏ hơn T4 | Dùng GPU T4 hoặc giảm `batch_size` trong cell cấu hình (không có giá trị đã kiểm chứng) |
| Kết quả không khớp bảng | Khác phiên bản thư viện, quên `FAST_MODE = False`, hoặc dùng dữ liệu cleaned bản cũ | Kiểm tra checksum (Mục 5.3), `FAST_MODE`, phiên bản (Mục 4) |

## 12. Giấy phép, trích dẫn, khai báo AI

- Giấy phép mã nguồn của nhóm: MIT (file `LICENSE` ở gốc repo, bản quyền 2026 Nguyễn Hoàng Quang Thái, Nguyễn Minh Phương). Dữ liệu ACN-Data không thuộc giấy phép này; xem Mục 5.1.
- Dữ liệu: ACN-Data (xem 5.1); cần trích dẫn Lee, Li và Low (2019). Thư viện dùng: scikit-learn, XGBoost, LightGBM, Optuna, TensorFlow/Keras, pandas, numpy, scipy, matplotlib, seaborn; giấy phép theo từng dự án gốc.
- Khai báo công cụ AI: nhóm đã dùng Claude (Anthropic) để hỗ trợ viết và chạy lại mã, đối chiếu số liệu trong bài với đầu ra của notebook, soạn bài báo và tài liệu này. Các thí nghiệm trong bài do nhóm chạy trên notebook Kaggle; nhóm chịu trách nhiệm về nội dung. Mức độ nhóm tự rà soát từng phần (mã, thí nghiệm, bài báo) ghi trong nhật ký sử dụng AI của nhóm **[CẦN XÁC NHẬN]**.
- Cách trích dẫn dự án (khi chưa có bài công bố), dạng BibTeX; thứ tự tác giả và việc có ghi GVHD hay không là **[CẦN XÁC NHẬN]**; khi bài được công bố thì thay bằng bài báo: 

```bibtex
@misc{group25_dap391m_2026,
  author = {Nguyễn, Hoàng Quang Thái and Nguyễn, Minh Phương},
  title = {Forecast-Driven Smart Charging: Linking Session Energy Analysis, Hourly Demand Forecasting and Peak Reduction on ACN-Data},
  year = {2026},
  howpublished = {GitHub repository, version v1.0, commit 8fe9586},
  url = {https://github.com/quangthainguyenhoang-sudo/Forecast_Driven_Smart_Charging_Linking_Session_Energy_Analysis_Hourly_Demand_Forecasting_and_Peak}
}
```
