# Báo cáo phân tích thực nghiệm paper *Does parking matter? The impact of parking time on last-mile delivery optimization*

## 1. Mục tiêu của báo cáo

Tài liệu này tổng hợp và phân tích lại kết quả tái hiện thực nghiệm cho **base case của Fig. 3** trong paper, sử dụng **heuristic mode** thay vì lời giải exact MIP.  
Nguồn dữ liệu dùng để lập báo cáo:

- `parking_matter.txt`
- `fig3_avg_completion_times.csv`
- `fig3_values.csv`
- `fig3_instance_details.csv`

Trọng tâm của báo cáo là:

1. nhắc lại ý tưởng giải thuật và benchmark trong paper,
2. giải thích ý nghĩa các đại lượng trong file kết quả,
3. đối chiếu kết quả heuristic với lập luận trong paper,
4. đưa ra đánh giá cuối cùng bằng **công thức** và **lập luận định lượng**.

---

## 2. Bối cảnh bài toán và ý tưởng thuật toán

Paper xây dựng mô hình **CDPP (Capacitated Delivery Problem with Parking)** để mô hình hóa bài toán giao hàng chặng cuối khi tài xế phải quyết định:

- lái xe đến đâu,
- đỗ ở đâu,
- đi bộ phục vụ nhóm khách nào từ cùng một điểm đỗ.

Điểm khác biệt cốt lõi của CDPP so với nhiều mô hình trước đó là **parking time được đưa trực tiếp vào objective**, tức là thời gian tìm chỗ đỗ và đỗ xe được tính như một thành phần chi phí thật sự của tour.

Khi giải exact bị khó do số biến tăng mạnh, paper đề xuất heuristic hai tầng:

- **PA-R (Parking Assignment and Routing)**: chọn vị trí đỗ và route của xe giữa các điểm đỗ,
- **SSA (Service Set Assignment)**: chia khách đã gán cho từng điểm đỗ thành các service set để tối ưu phần đi bộ.

Trong lần chạy này, do môi trường chạy thực tế bị giới hạn license Gurobi, kết quả được sinh bằng **heuristic mode**.

---

## 3. Thiết lập thực nghiệm dùng trong báo cáo

Báo cáo này bám đúng **base case** của paper:

- số khách: `n = 50`,
- năng lực người giao hàng: `q = 3`,
- thời gian bốc 1 kiện: `f = 2.1`,
- parking time theo county:
  - `Cook = 9`,
  - `Adams = 5`,
  - `Cumberland = 1`.

Ba county đại diện cho ba kiểu địa lý:

- **Cook**: urban,
- **Adams**: suburban,
- **Cumberland**: rural.

Các benchmark được so sánh:

- **CDPP**
- **Modified TSP**
- **Relaxed M-S (alpha = 0.5)**
- **Relaxed M-S (alpha = 0.6)**
- **Relaxed M-S (alpha = 0.8)**

---

## 4. Ý nghĩa các cột trong file kết quả

Trong `fig3_instance_details.csv`, mỗi dòng tương ứng với một cặp `(instance, benchmark)`.

- `optimized_objective`: giá trị objective mà solver/heuristic thực sự tối ưu.
- `completion_time`: tổng thời gian hoàn thành tour dùng để so sánh giữa các mô hình.
- `num_parks`: số lần đỗ xe.
- `route_cost`: phần thời gian lái xe.
- `walking_cost`: phần thời gian đi bộ.
- `loading_cost`: phần thời gian bốc hàng. Với `n = 50` và `f = 2.1`, ta có:

  \[
  loading\_cost = n f = 50 \times 2.1 = 105.
  \]

- `parking_component = num_parks \times parking_time`.

### 4.1. Công thức completion time

Với cách lưu kết quả hiện tại, completion time thực được tách thành:

\[
T = D + W + L + s p
\]

trong đó:

- \(D\): route_cost,
- \(W\): walking_cost,
- \(L\): loading_cost,
- \(s\): num_parks,
- \(p\): parking_time.

### 4.2. Objective của từng benchmark

#### CDPP / Modified TSP
Hai mô hình này được so sánh trực tiếp theo completion time:

\[
z_{CDPP} = T = D + W + L + s p
\]

#### Relaxed M-S
Relaxed M-S chọn lời giải theo weighted objective:

\[
z_\alpha = \alpha D + (1-\alpha) W + L
\]

Nhưng khi **đánh giá chất lượng thật sự của tour**, phải dùng completion time thực:

\[
T_\alpha = D + W + L + s p
\]

### 4.3. Công thức percent reduction của Fig. 3

Với một benchmark \(b\), phần trăm giảm completion time của CDPP trên từng instance được tính bởi:

\[
R_i^{(b)} = \frac{T_i^{(b)} - T_i^{CDPP}}{T_i^{(b)}} \times 100\%
\]

Giá trị trong `fig3_values.csv` là trung bình theo instance:

\[
\bar{R}^{(b)} = \frac{1}{m} \sum_{i=1}^m R_i^{(b)}
\]

Lưu ý: đây **không nhất thiết** bằng tỉ lệ tính trực tiếp từ các completion time trung bình theo county.

---

## 5. Kết quả trung bình theo county

### 5.1. Completion time trung bình

| county     |    CDPP |   Modified TSP |   Relaxed M-S (alpha=0.5) |   Relaxed M-S (alpha=0.6) |   Relaxed M-S (alpha=0.8) |
|:-----------|--------:|---------------:|--------------------------:|--------------------------:|--------------------------:|
| Cook       | 290.025 |        373.677 |                   581.871 |                   580.073 |                   421.638 |
| Adams      | 293.135 |        310.09  |                   391.975 |                   387.997 |                   377.523 |
| Cumberland | 199.481 |        198.801 |                   201.141 |                   201.141 |                   201.593 |

### 5.2. Average percent reduction của CDPP so với benchmark

| county     |   Relaxed M-S (alpha=0.5) |   Relaxed M-S (alpha=0.6) |   Relaxed M-S (alpha=0.8) |   Modified TSP |
|:-----------|--------------------------:|--------------------------:|--------------------------:|---------------:|
| Cook       |                    50.17  |                    50.009 |                    28.767 |         22.37  |
| Adams      |                    25.348 |                    24.502 |                    21.943 |          5.776 |
| Cumberland |                     0.739 |                     0.739 |                     0.93  |         -0.358 |

### 5.3. Phân rã cấu trúc chi phí trung bình

| county     | benchmark               |   completion_mean |   parks_mean |   parking_mean |   route_mean |   walk_mean |   load_mean |   parking_share_pct |
|:-----------|:------------------------|------------------:|-------------:|---------------:|-------------:|------------:|------------:|--------------------:|
| Adams      | CDPP                    |           293.135 |         15.8 |           79   |       39.62  |      69.516 |         105 |              26.95  |
| Adams      | Modified TSP            |           310.09  |         24.6 |          123   |       39.777 |     147.313 |         105 |              39.666 |
| Adams      | Relaxed M-S (alpha=0.5) |           391.975 |         48.5 |          242.5 |       44.475 |       0     |         105 |              61.866 |
| Adams      | Relaxed M-S (alpha=0.6) |           387.997 |         47.7 |          238.5 |       44.122 |       0.375 |         105 |              61.469 |
| Adams      | Relaxed M-S (alpha=0.8) |           377.523 |         45.4 |          227   |       43.374 |       2.149 |         105 |              60.129 |
| Cook       | CDPP                    |           290.025 |          7.8 |           70.2 |       13.186 |     101.639 |         105 |              24.205 |
| Cook       | Modified TSP            |           373.677 |         18.7 |          168.3 |       20.13  |     185.247 |         105 |              45.039 |
| Cook       | Relaxed M-S (alpha=0.5) |           581.871 |         49.7 |          447.3 |       29.571 |       0     |         105 |              76.873 |
| Cook       | Relaxed M-S (alpha=0.6) |           580.073 |         49.5 |          445.5 |       29.555 |       0.019 |         105 |              76.801 |
| Cook       | Relaxed M-S (alpha=0.8) |           421.638 |         29.3 |          263.7 |       23.157 |      29.78  |         105 |              62.542 |
| Cumberland | CDPP                    |           199.48  |         32.3 |           32.3 |       49.678 |      12.503 |         105 |              16.192 |
| Cumberland | Modified TSP            |           198.801 |         38.6 |           38.6 |       50.104 |     110.097 |         105 |              19.416 |
| Cumberland | Relaxed M-S (alpha=0.5) |           201.141 |         45.6 |           45.6 |       50.169 |       0.373 |         105 |              22.671 |
| Cumberland | Relaxed M-S (alpha=0.6) |           201.141 |         45.6 |           45.6 |       50.169 |       0.373 |         105 |              22.671 |
| Cumberland | Relaxed M-S (alpha=0.8) |           201.593 |         43.6 |           43.6 |       48.763 |       4.23  |         105 |              21.628 |

---

## 6. Diễn giải nhanh từ kết quả heuristic

### 6.1. Cook County (urban)

Cook là nơi heuristic thể hiện rõ nhất kết luận cốt lõi của paper:

- CDPP tốt hơn rõ rệt so với mọi benchmark.
- Relaxed M-S với `alpha = 0.5` và `alpha = 0.6` rất tệ:
  - completion lần lượt khoảng `581.9` và `580.1`,
  - parking chiếm khoảng `76.9%` và `76.8%` tổng thời gian.
- CDPP chỉ đỗ trung bình `7.8` lần, tương ứng parking component `70.2`, nhỏ hơn rất nhiều so với:
  - Modified TSP: `18.7` lần đỗ,
  - Relaxed M-S 0.5/0.6: xấp xỉ `50` lần đỗ.

Điều này hoàn toàn phù hợp với luận điểm chính của paper:  
**bỏ qua parking time sẽ làm mô hình nghiêng về lái xe nhiều và đỗ quá nhiều**, dẫn tới tour dài bất thường ở môi trường đô thị.

### 6.2. Adams County (suburban)

Adams vẫn giữ đúng xu hướng paper mô tả:

- CDPP tiếp tục tốt nhất.
- Mức cải thiện tồn tại nhưng thấp hơn Cook:
  - khoảng `25.3%` so với Relaxed M-S 0.5,
  - khoảng `24.5%` so với Relaxed M-S 0.6,
  - khoảng `21.9%` so với Relaxed M-S 0.8,
  - khoảng `5.8%` so với Modified TSP.

Điều này phản ánh đúng trực giác paper:  
ở suburban, khách xa nhau hơn nên không thể đổi quá nhiều driving lấy walking như ở urban; vì vậy lợi ích của việc mô hình hóa parking vẫn có, nhưng yếu hơn Cook.

### 6.3. Cumberland County (rural)

Cumberland cho kết quả rất sát tinh thần của paper ở mức **định tính**:

- CDPP và Modified TSP gần như ngang nhau,
- mọi mức cải thiện của CDPP so với Relaxed M-S đều rất nhỏ, dưới `1%`,
- riêng so với Modified TSP, kết quả đang là `-0.358%`, tức là CDPP heuristic còn hơi kém hơn một chút.

Điểm này cho thấy:

- ở rural, parking time thấp (`p = 1`) và khoảng cách giữa khách lớn,
- driving gần như là hành vi hợp lý mặc định,
- lợi ích của việc gom khách thành các walking loops nhỏ đi rất nhiều.

Nói cách khác, **kết luận định tính của paper vẫn giữ**: trong rural, TSP/Modified TSP là một baseline rất mạnh.

---

## 7. Đối chiếu trực tiếp với lập luận của paper

### 7.1. Những điểm khớp với paper

1. **CDPP luôn thắng rõ trong môi trường đô thị (Cook).**  
   Đây là thông điệp mạnh nhất của paper và reproduction bằng heuristic vẫn giữ được.

2. **Relaxed M-S với alpha thấp dẫn đến quá nhiều điểm đỗ.**  
   Ở Cook, parking share của Relaxed M-S 0.6 là `76.801%`, gần như trùng với mô tả trong paper rằng tour dạng này dành khoảng `77%` thời gian cho việc đỗ xe.

3. **Lợi ích của CDPP giảm dần khi đi từ urban sang rural.**  
   Thứ tự mức cải thiện theo county là:
   - lớn nhất ở Cook,
   - trung bình ở Adams,
   - gần bằng 0 ở Cumberland.

4. **Ở rural, Modified TSP đủ mạnh để tiệm cận CDPP.**  
   Paper nói rằng ở rural, TSP có thể là đủ tốt; kết quả heuristic cũng cho thấy hai mô hình gần như trùng nhau.

### 7.2. Những điểm lệch so với paper

Paper nêu rõ ở **Cook County**:

- giảm khoảng `53%` so với Relaxed M-S `alpha = 0.5`,
- giảm khoảng `53%` so với Relaxed M-S `alpha = 0.6`,
- giảm khoảng `48%` so với Relaxed M-S `alpha = 0.8`,
- giảm khoảng `11%` so với Modified TSP.

Trong khi heuristic reproduction hiện tại cho Cook là:

| benchmark               |   paper_pct |   heuristic_pct |   diff_pct_point |
|:------------------------|------------:|----------------:|-----------------:|
| Relaxed M-S (alpha=0.5) |          53 |          50.17  |           -2.83  |
| Relaxed M-S (alpha=0.6) |          53 |          50.009 |           -2.991 |
| Relaxed M-S (alpha=0.8) |          48 |          28.767 |          -19.233 |
| Modified TSP            |          11 |          22.37  |           11.37  |

Nhận xét:

- với `alpha = 0.5` và `0.6`, reproduction vẫn khá gần paper (lệch khoảng `-2.8` đến `-3.0` điểm phần trăm),
- với `alpha = 0.8`, reproduction chỉ còn `28.8%`, thấp hơn paper tới khoảng `19.2` điểm phần trăm,
- với `Modified TSP`, reproduction cho `22.4%`, cao hơn paper khoảng `11.4` điểm phần trăm.

Điều này cho thấy độ lệch định lượng chủ yếu đến từ:

- benchmark `Relaxed M-S (alpha = 0.8)` trong bản tái hiện đang **mạnh hơn** so với paper,
- benchmark `Modified TSP` trong bản tái hiện đang **yếu hơn** so với paper,
- hoặc heuristic CDPP/benchmark chưa tái tạo đúng cấu trúc route như mã gốc của tác giả.

---

## 8. Chẩn đoán sâu hơn bằng công thức và cấu trúc lời giải

### 8.1. Chẩn đoán số lần đỗ ở Cook

Paper mô tả rằng khi `p > 0` ở Cook, tổng thời gian dành cho parking của CDPP tương đối ổn định trong khoảng `40` đến `47` phút.  
Với `p = 9`, số lần đỗ ngầm suy ra phải xấp xỉ:

\[
s^{paper}_{Cook,CDPP} \in \left[\frac{40}{9}, \frac{47}{9}\right] \approx [4.4, 5.2]
\]

Trong khi reproduction heuristic cho:

\[
\hat{s}_{Cook,CDPP} = 7.8
\]

và parking component trung bình:

\[
\hat{P}_{Cook,CDPP} = 70.2
\]

Tức là heuristic hiện tại đang **mở nhiều điểm đỗ hơn mức paper hàm ý**, và đây là một nguyên nhân rất mạnh giải thích vì sao cấu trúc lời giải chưa khớp hoàn toàn với kết quả gốc.

### 8.2. Chẩn đoán cho Modified TSP ở Cook

Paper nói CDPP chỉ tốt hơn Modified TSP khoảng `11%` ở Cook, nhưng reproduction cho:

\[
\hat{R}_{Cook,ModifiedTSP} = 22.370\%
\]

Điều này cho thấy bản Modified TSP hiện tại đang tạo ra các route kém hơn paper mong đợi.  
Khả năng cao là bước “route-first cluster-second” trong mã tái hiện chưa giữ được chất lượng route/phân cụm như benchmark trong bài báo.

### 8.3. Chẩn đoán cho Relaxed M-S với alpha = 0.8 ở Cook

Paper báo cáo mức giảm khoảng `48%`, còn reproduction chỉ cho:

\[
\hat{R}_{Cook,\alpha=0.8} = 28.767\%
\]

Tức là benchmark `alpha = 0.8` trong bản tái hiện đang **quá cạnh tranh** so với paper.  
Nguyên nhân thường thấy là heuristic hiện tại cho phép benchmark này giảm được nhiều điểm đỗ và walking hợp lý hơn mức tác giả ghi nhận.

### 8.4. Chẩn đoán cho rural

Paper nói rằng trong Cumberland:

- CDPP gần Modified TSP,
- và `alpha = 0.8` còn có thể tệ hơn `alpha = 0.6` do walking bị khuyến khích quá mức.

Reproduction hiện tại cho:

\[
\hat{R}_{Cumberland,ModifiedTSP} = -0.358\%
\]

và mức tăng completion time của Relaxed M-S từ `alpha = 0.6` lên `alpha = 0.8` là:

\[
\frac{T_{0.8} - T_{0.6}}{T_{0.6}} \times 100\% = 0.225\%
\]

Dấu của hai đại lượng này vẫn đúng với câu chuyện rural của paper:

- Modified TSP gần như ngang CDPP,
- `alpha = 0.8` vẫn tệ hơn `0.6`.

Tuy nhiên, biên độ đang nhỏ hơn paper khá nhiều, nghĩa là heuristic tái hiện chưa làm nổi bật hoàn toàn “rural walking penalty”.

---

## 9. Kết luận tổng hợp

### 9.1. Kết luận định tính

Về mặt **khoa học và xu hướng**, reproduction bằng heuristic **không đi ngược paper**.  
Các kết luận lớn vẫn giữ:

- **Parking matters**.
- **CDPP mạnh nhất ở urban**.
- **Bỏ parking khỏi objective gây ra quá nhiều lần đỗ**.
- **Ở rural, Modified TSP gần đủ tốt**.

### 9.2. Kết luận định lượng

Về mặt **con số**, reproduction hiện tại **chưa bám hoàn toàn Fig. 3 của paper**, đặc biệt ở Cook đối với:

- `Relaxed M-S (alpha = 0.8)`,
- `Modified TSP`.

Có thể tóm tắt sai khác bằng đại lượng:

\[
\varepsilon_b = \hat{R}_b - R_b^{paper}
\]

Trong Cook:

- \(\varepsilon_{0.5} \approx -2.83\) điểm %,
- \(\varepsilon_{0.6} \approx -2.99\) điểm %,
- \(\varepsilon_{0.8} \approx -19.23\) điểm %,
- \(\varepsilon_{ModifiedTSP} \approx +11.37\) điểm %.

### 9.3. Đánh giá cuối cùng

**Đánh giá cuối cùng của báo cáo này là:**

1. **Bản tái hiện bằng heuristic đã tái tạo đúng câu chuyện khoa học của paper**, đặc biệt là vai trò quyết định của parking time trong môi trường đô thị.
2. **Bản tái hiện chưa đạt độ khớp định lượng hoàn toàn với Fig. 3**, vì cấu trúc route/điểm đỗ của heuristic hiện tại khác paper, thể hiện rõ nhất qua số lần đỗ trung bình ở Cook:

   \[
   \hat{s}_{Cook,CDPP} = 7.8 \quad > \quad s^{paper}_{Cook,CDPP} \approx 4.4\text{–}5.2
   \]

3. **Sai khác lớn nhất nằm ở chất lượng benchmark**, không chỉ ở CDPP:
   - Modified TSP hiện tại đang yếu hơn paper,
   - Relaxed M-S với `alpha = 0.8` hiện tại đang mạnh hơn paper.

4. Nếu mục tiêu là **“đúng tinh thần paper”**, thì kết quả hiện tại đã đủ tốt để báo cáo phân tích.  
   Nếu mục tiêu là **“khớp gần Fig. 3 của paper”**, thì cần chỉnh tiếp:
   - logic Modified TSP,
   - logic Relaxed M-S `alpha = 0.8`,
   - và đặc biệt là heuristic chọn số điểm đỗ cho CDPP ở Cook.

---

## 10. Phụ lục A — Kết quả đầy đủ theo instance (Cook)

|   instance_id | benchmark               |   completion_time |   num_parks |   route_cost |   walking_cost |   parking_component |
|--------------:|:------------------------|------------------:|------------:|-------------:|---------------:|--------------------:|
|             1 | CDPP                    |           309.071 |           7 |       13.822 |        127.248 |                  63 |
|             1 | Modified TSP            |           396.622 |          20 |       24.695 |        191.927 |                 180 |
|             1 | Relaxed M-S (alpha=0.5) |           594.81  |          50 |       39.81  |          0     |                 450 |
|             1 | Relaxed M-S (alpha=0.6) |           594.81  |          50 |       39.81  |          0     |                 450 |
|             1 | Relaxed M-S (alpha=0.8) |           370.347 |          20 |       25.359 |         59.989 |                 180 |
|             2 | CDPP                    |           300.779 |          11 |       26.983 |         69.796 |                  99 |
|             2 | Modified TSP            |           363.118 |          20 |       30.173 |        152.945 |                 180 |
|             2 | Relaxed M-S (alpha=0.5) |           584.083 |          49 |       38.083 |          0     |                 441 |
|             2 | Relaxed M-S (alpha=0.6) |           584.083 |          49 |       38.083 |          0     |                 441 |
|             2 | Relaxed M-S (alpha=0.8) |           380.484 |          25 |       33.669 |         16.815 |                 225 |
|             3 | CDPP                    |           272.536 |           7 |       12.566 |         91.97  |                  63 |
|             3 | Modified TSP            |           348.706 |          20 |       19.255 |        149.451 |                 180 |
|             3 | Relaxed M-S (alpha=0.5) |           560.819 |          48 |       23.819 |          0     |                 432 |
|             3 | Relaxed M-S (alpha=0.6) |           542.842 |          46 |       23.655 |          0.187 |                 414 |
|             3 | Relaxed M-S (alpha=0.8) |           542.842 |          46 |       23.655 |          0.187 |                 414 |
|             4 | CDPP                    |           273.765 |           7 |        8.829 |         96.937 |                  63 |
|             4 | Modified TSP            |           371.266 |          16 |       11.327 |        215.939 |                 144 |
|             4 | Relaxed M-S (alpha=0.5) |           575.988 |          50 |       20.988 |          0     |                 450 |
|             4 | Relaxed M-S (alpha=0.6) |           575.988 |          50 |       20.988 |          0     |                 450 |
|             4 | Relaxed M-S (alpha=0.8) |           425.305 |          31 |       17.569 |         23.736 |                 279 |
|             5 | CDPP                    |           314.478 |           8 |       14.591 |        122.887 |                  72 |
|             5 | Modified TSP            |           384.84  |          20 |       23.879 |        180.961 |                 180 |
|             5 | Relaxed M-S (alpha=0.5) |           587.271 |          50 |       32.271 |          0     |                 450 |
|             5 | Relaxed M-S (alpha=0.6) |           587.271 |          50 |       32.271 |          0     |                 450 |
|             5 | Relaxed M-S (alpha=0.8) |           382.752 |          24 |       26.473 |         35.279 |                 216 |
|             6 | CDPP                    |           283.026 |           6 |       13.435 |        110.591 |                  54 |
|             6 | Modified TSP            |           375.278 |          17 |       21.086 |        201.192 |                 153 |
|             6 | Relaxed M-S (alpha=0.5) |           588.036 |          50 |       33.037 |          0     |                 450 |
|             6 | Relaxed M-S (alpha=0.6) |           588.036 |          50 |       33.037 |          0     |                 450 |
|             6 | Relaxed M-S (alpha=0.8) |           309.079 |          13 |       19.103 |         67.976 |                 117 |
|             7 | CDPP                    |           295.112 |          10 |       17.445 |         82.667 |                  90 |
|             7 | Modified TSP            |           368.114 |          18 |       19.91  |        186.204 |                 162 |
|             7 | Relaxed M-S (alpha=0.5) |           581.932 |          50 |       26.932 |          0     |                 450 |
|             7 | Relaxed M-S (alpha=0.6) |           581.932 |          50 |       26.932 |          0     |                 450 |
|             7 | Relaxed M-S (alpha=0.8) |           385.039 |          26 |       22.813 |         23.226 |                 234 |
|             8 | CDPP                    |           277.655 |           8 |        8.16  |         92.495 |                  72 |
|             8 | Modified TSP            |           382.604 |          17 |       19.692 |        209.912 |                 153 |
|             8 | Relaxed M-S (alpha=0.5) |           588.437 |          50 |       33.437 |          0     |                 450 |
|             8 | Relaxed M-S (alpha=0.6) |           588.437 |          50 |       33.437 |          0     |                 450 |
|             8 | Relaxed M-S (alpha=0.8) |           381.362 |          23 |       19.166 |         50.196 |                 207 |
|             9 | CDPP                    |           277.205 |           7 |        7.673 |        101.532 |                  63 |
|             9 | Modified TSP            |           361.779 |          19 |       13.393 |        177.386 |                 171 |
|             9 | Relaxed M-S (alpha=0.5) |           574.16  |          50 |       19.16  |          0     |                 450 |
|             9 | Relaxed M-S (alpha=0.6) |           574.16  |          50 |       19.16  |          0     |                 450 |
|             9 | Relaxed M-S (alpha=0.8) |           574.16  |          50 |       19.16  |          0     |                 450 |
|            10 | CDPP                    |           296.618 |           7 |        8.352 |        120.267 |                  63 |
|            10 | Modified TSP            |           384.441 |          20 |       17.891 |        186.55  |                 180 |
|            10 | Relaxed M-S (alpha=0.5) |           583.174 |          50 |       28.174 |          0     |                 450 |
|            10 | Relaxed M-S (alpha=0.6) |           583.174 |          50 |       28.174 |          0     |                 450 |
|            10 | Relaxed M-S (alpha=0.8) |           465.008 |          35 |       24.608 |         20.4   |                 315 |

---

## 11. Phụ lục B — Kết quả đầy đủ theo instance (Adams)

|   instance_id | benchmark               |   completion_time |   num_parks |   route_cost |   walking_cost |   parking_component |
|--------------:|:------------------------|------------------:|------------:|-------------:|---------------:|--------------------:|
|             1 | CDPP                    |           271.601 |          17 |       26.626 |         54.975 |                  85 |
|             1 | Modified TSP            |           290.151 |          23 |       22.016 |        153.134 |                 115 |
|             1 | Relaxed M-S (alpha=0.5) |           380.272 |          50 |       25.271 |          0     |                 250 |
|             1 | Relaxed M-S (alpha=0.6) |           380.272 |          50 |       25.271 |          0     |                 250 |
|             1 | Relaxed M-S (alpha=0.8) |           380.272 |          50 |       25.271 |          0     |                 250 |
|             2 | CDPP                    |           307.117 |          17 |       54.684 |         62.433 |                  85 |
|             2 | Modified TSP            |           333.15  |          27 |       58.923 |        139.227 |                 135 |
|             2 | Relaxed M-S (alpha=0.5) |           380.54  |          41 |       70.54  |          0     |                 205 |
|             2 | Relaxed M-S (alpha=0.6) |           370.565 |          39 |       70.28  |          0.285 |                 195 |
|             2 | Relaxed M-S (alpha=0.8) |           318.345 |          27 |       65.016 |         13.329 |                 135 |
|             3 | CDPP                    |           251.291 |          12 |       17.574 |         68.716 |                  60 |
|             3 | Modified TSP            |           273.474 |          22 |       19.297 |        144.177 |                 110 |
|             3 | Relaxed M-S (alpha=0.5) |           376.568 |          50 |       21.568 |          0     |                 250 |
|             3 | Relaxed M-S (alpha=0.6) |           376.568 |          50 |       21.568 |          0     |                 250 |
|             3 | Relaxed M-S (alpha=0.8) |           376.568 |          50 |       21.568 |          0     |                 250 |
|             4 | CDPP                    |           269.86  |          12 |       59.154 |         45.705 |                  60 |
|             4 | Modified TSP            |           310.53  |          23 |       60.113 |        135.417 |                 115 |
|             4 | Relaxed M-S (alpha=0.5) |           395.15  |          46 |       60.15  |          0     |                 230 |
|             4 | Relaxed M-S (alpha=0.6) |           395.15  |          46 |       60.15  |          0     |                 230 |
|             4 | Relaxed M-S (alpha=0.8) |           395.15  |          46 |       60.15  |          0     |                 230 |
|             5 | CDPP                    |           283.255 |          13 |       45.363 |         67.892 |                  65 |
|             5 | Modified TSP            |           296.298 |          22 |       44.645 |        141.654 |                 110 |
|             5 | Relaxed M-S (alpha=0.5) |           400.937 |          50 |       45.937 |          0     |                 250 |
|             5 | Relaxed M-S (alpha=0.6) |           400.937 |          50 |       45.937 |          0     |                 250 |
|             5 | Relaxed M-S (alpha=0.8) |           400.937 |          50 |       45.937 |          0     |                 250 |
|             6 | CDPP                    |           303.558 |          18 |       34.428 |         74.13  |                  90 |
|             6 | Modified TSP            |           321.639 |          26 |       34.512 |        157.127 |                 130 |
|             6 | Relaxed M-S (alpha=0.5) |           395.29  |          50 |       40.29  |          0     |                 250 |
|             6 | Relaxed M-S (alpha=0.6) |           395.29  |          50 |       40.29  |          0     |                 250 |
|             6 | Relaxed M-S (alpha=0.8) |           395.29  |          50 |       40.29  |          0     |                 250 |
|             7 | CDPP                    |           253.149 |          12 |       28.581 |         59.569 |                  60 |
|             7 | Modified TSP            |           281.034 |          22 |       28.312 |        142.721 |                 110 |
|             7 | Relaxed M-S (alpha=0.5) |           385.039 |          50 |       30.039 |          0     |                 250 |
|             7 | Relaxed M-S (alpha=0.6) |           385.039 |          50 |       30.039 |          0     |                 250 |
|             7 | Relaxed M-S (alpha=0.8) |           385.039 |          50 |       30.039 |          0     |                 250 |
|             8 | CDPP                    |           268.029 |          14 |       33.038 |         59.99  |                  70 |
|             8 | Modified TSP            |           293.077 |          21 |       33.85  |        154.228 |                 105 |
|             8 | Relaxed M-S (alpha=0.5) |           393.588 |          50 |       38.588 |          0     |                 250 |
|             8 | Relaxed M-S (alpha=0.6) |           378.712 |          47 |       38.323 |          0.389 |                 235 |
|             8 | Relaxed M-S (alpha=0.8) |           373.934 |          46 |       38.212 |          0.722 |                 230 |
|             9 | CDPP                    |           387.791 |          23 |       38.902 |        128.889 |                 115 |
|             9 | Modified TSP            |           373.165 |          35 |       45.08  |        153.085 |                 175 |
|             9 | Relaxed M-S (alpha=0.5) |           407.653 |          50 |       52.653 |          0     |                 250 |
|             9 | Relaxed M-S (alpha=0.6) |           392.727 |          47 |       49.649 |          3.078 |                 235 |
|             9 | Relaxed M-S (alpha=0.8) |           392.727 |          47 |       49.649 |          3.078 |                 235 |
|            10 | CDPP                    |           335.702 |          20 |       57.846 |         72.855 |                 100 |
|            10 | Modified TSP            |           328.38  |          25 |       51.021 |        152.359 |                 125 |
|            10 | Relaxed M-S (alpha=0.5) |           404.712 |          48 |       59.712 |          0     |                 240 |
|            10 | Relaxed M-S (alpha=0.6) |           404.712 |          48 |       59.712 |          0     |                 240 |
|            10 | Relaxed M-S (alpha=0.8) |           356.967 |          38 |       57.606 |          4.362 |                 190 |

---

## 12. Phụ lục C — Kết quả đầy đủ theo instance (Cumberland)

|   instance_id | benchmark               |   completion_time |   num_parks |   route_cost |   walking_cost |   parking_component |
|--------------:|:------------------------|------------------:|------------:|-------------:|---------------:|--------------------:|
|             1 | CDPP                    |           217.538 |          36 |       69.075 |          7.463 |                  36 |
|             1 | Modified TSP            |           219.412 |          39 |       70.465 |        109.948 |                  39 |
|             1 | Relaxed M-S (alpha=0.5) |           224.477 |          46 |       73.477 |          0     |                  46 |
|             1 | Relaxed M-S (alpha=0.6) |           224.477 |          46 |       73.477 |          0     |                  46 |
|             1 | Relaxed M-S (alpha=0.8) |           228.993 |          26 |       59.415 |         38.578 |                  26 |
|             2 | CDPP                    |           182.714 |          27 |       40.001 |         10.713 |                  27 |
|             2 | Modified TSP            |           184.929 |          32 |       40.001 |        112.928 |                  32 |
|             2 | Relaxed M-S (alpha=0.5) |           186.233 |          41 |       40.233 |          0     |                  41 |
|             2 | Relaxed M-S (alpha=0.6) |           186.233 |          41 |       40.233 |          0     |                  41 |
|             2 | Relaxed M-S (alpha=0.8) |           186.233 |          41 |       40.233 |          0     |                  41 |
|             3 | CDPP                    |           216.178 |          28 |       69.714 |         13.463 |                  28 |
|             3 | Modified TSP            |           214.939 |          34 |       70.296 |        110.644 |                  34 |
|             3 | Relaxed M-S (alpha=0.5) |           221.447 |          46 |       70.447 |          0     |                  46 |
|             3 | Relaxed M-S (alpha=0.6) |           221.447 |          46 |       70.447 |          0     |                  46 |
|             3 | Relaxed M-S (alpha=0.8) |           221.447 |          46 |       70.447 |          0     |                  46 |
|             4 | CDPP                    |           207.945 |          35 |       55.84  |         12.104 |                  35 |
|             4 | Modified TSP            |           206.009 |          41 |       55.912 |        109.097 |                  41 |
|             4 | Relaxed M-S (alpha=0.5) |           210.173 |          49 |       56.173 |          0     |                  49 |
|             4 | Relaxed M-S (alpha=0.6) |           210.173 |          49 |       56.173 |          0     |                  49 |
|             4 | Relaxed M-S (alpha=0.8) |           210.173 |          49 |       56.173 |          0     |                  49 |
|             5 | CDPP                    |           184.816 |          33 |       30.064 |         16.752 |                  33 |
|             5 | Modified TSP            |           183.121 |          41 |       29.866 |        112.255 |                  41 |
|             5 | Relaxed M-S (alpha=0.5) |           185.22  |          50 |       30.22  |          0     |                  50 |
|             5 | Relaxed M-S (alpha=0.6) |           185.22  |          50 |       30.22  |          0     |                  50 |
|             5 | Relaxed M-S (alpha=0.8) |           185.22  |          50 |       30.22  |          0     |                  50 |
|             6 | CDPP                    |           183.265 |          31 |       33.305 |         13.96  |                  31 |
|             6 | Modified TSP            |           182.325 |          39 |       33.483 |        109.842 |                  39 |
|             6 | Relaxed M-S (alpha=0.5) |           178.482 |          40 |       31.147 |          2.336 |                  40 |
|             6 | Relaxed M-S (alpha=0.6) |           178.482 |          40 |       31.147 |          2.336 |                  40 |
|             6 | Relaxed M-S (alpha=0.8) |           178.482 |          40 |       31.147 |          2.336 |                  40 |
|             7 | CDPP                    |           183.413 |          34 |       35.291 |          9.122 |                  34 |
|             7 | Modified TSP            |           183.249 |          40 |       35.451 |        107.798 |                  40 |
|             7 | Relaxed M-S (alpha=0.5) |           188.693 |          48 |       35.693 |          0     |                  48 |
|             7 | Relaxed M-S (alpha=0.6) |           188.693 |          48 |       35.693 |          0     |                  48 |
|             7 | Relaxed M-S (alpha=0.8) |           188.693 |          48 |       35.693 |          0     |                  48 |
|             8 | CDPP                    |           182.396 |          32 |       25.071 |         20.326 |                  32 |
|             8 | Modified TSP            |           179.091 |          42 |       26.067 |        111.023 |                  42 |
|             8 | Relaxed M-S (alpha=0.5) |           179.118 |          48 |       25.793 |          0.326 |                  48 |
|             8 | Relaxed M-S (alpha=0.6) |           179.118 |          48 |       25.793 |          0.326 |                  48 |
|             8 | Relaxed M-S (alpha=0.8) |           179.118 |          48 |       25.793 |          0.326 |                  48 |
|             9 | CDPP                    |           217.166 |          34 |       68.922 |          9.243 |                  34 |
|             9 | Modified TSP            |           217.136 |          38 |       70.012 |        109.123 |                  38 |
|             9 | Relaxed M-S (alpha=0.5) |           216.986 |          42 |       68.922 |          1.064 |                  42 |
|             9 | Relaxed M-S (alpha=0.6) |           216.986 |          42 |       68.922 |          1.064 |                  42 |
|             9 | Relaxed M-S (alpha=0.8) |           216.986 |          42 |       68.922 |          1.064 |                  42 |
|            10 | CDPP                    |           219.375 |          33 |       69.492 |         11.883 |                  33 |
|            10 | Modified TSP            |           217.803 |          40 |       69.492 |        108.311 |                  40 |
|            10 | Relaxed M-S (alpha=0.5) |           220.584 |          46 |       69.584 |          0     |                  46 |
|            10 | Relaxed M-S (alpha=0.6) |           220.584 |          46 |       69.584 |          0     |                  46 |
|            10 | Relaxed M-S (alpha=0.8) |           220.584 |          46 |       69.584 |          0     |                  46 |
