# Giải thích chi tiết Fig. 2 và Fig. 3 trong paper

## Fig. 2: Ngưỡng parking time làm TSP không còn tối ưu

Fig. 2 trả lời câu hỏi: **khi nào cách làm TSP “đỗ ở từng khách hàng” còn tối ưu, và khi nào cần dùng CDPP?**

### 1. Các thông số trong Fig. 2

**Parking time `p` (minutes)**  
Là trục tung của hình. Đây là thời gian tài xế mất để tìm chỗ đỗ và đỗ xe tại một vị trí. Nếu `p` càng cao, việc đỗ xe nhiều lần càng tốn kém.

**Length of block `l̂` (miles)**  
Là trục hoành của hình. Nó biểu diễn khoảng cách giữa các khách hàng trong mô hình lưới. Bên trái là môi trường đô thị với `l̂ = 0.07`, bên phải là môi trường nông thôn với `l̂ = 0.26`. Khi `l̂` càng lớn, khách hàng càng xa nhau, nên việc đi bộ gom nhiều khách từ một điểm đỗ trở nên kém hấp dẫn hơn.

**Capacity `q`**  
Là sức chứa của người giao hàng, tính bằng số gói có thể mang trong một lần đi bộ. Paper xét hai trường hợp chính:

- `q ≤ 2`: người giao chỉ mang được tối đa 1 hoặc 2 gói.
- `q = 3`: người giao mang được 3 gói, là base case của thực nghiệm.

Khi `q = 3`, người giao có thể gom nhiều khách hơn trong một walking loop, nên CDPP bắt đầu có lợi hơn TSP ở mức parking time thấp hơn.

**Walking speed parameter `ŵ`**  
Là thời gian đi bộ trên một đơn vị khoảng cách. Paper dùng xấp xỉ:

```text
ŵ = 20.3 min/mile
```

**Driving speed parameter `d̂`**  
Là thời gian lái xe trên một đơn vị khoảng cách. Paper ước lượng:

```text
Urban: d̂ = 4.6 min/mile
Rural: d̂ = 3.8 min/mile
```

### 2. Hai đường ngưỡng trong Fig. 2

Với `q ≤ 2`, ngưỡng parking time là:

```text
p = l̂(2ŵ - d̂)
```

Nếu:

```text
p ≤ l̂(2ŵ - d̂)
```

thì TSP đỗ ở từng khách vẫn là nghiệm tối ưu cho CDPP-grid.

Nếu:

```text
p > l̂(2ŵ - d̂)
```

thì TSP đỗ ở từng khách không còn tối ưu.

Với `q = 3`, ngưỡng parking time là:

```text
p = l̂((4/3)ŵ - d̂)
```

Nếu:

```text
p ≤ l̂((4/3)ŵ - d̂)
```

thì TSP đỗ ở từng khách vẫn tối ưu.

Nếu:

```text
p > l̂((4/3)ŵ - d̂)
```

thì CDPP bắt đầu có cấu trúc nghiệm khác TSP, thường là đỗ ít hơn và đi bộ nhiều hơn.

### 3. Ý nghĩa các vùng trong Fig. 2

**Vùng dưới đường `q = 3`**  
Parking time còn nhỏ. Việc đỗ ở từng khách hàng chưa gây thiệt hại đủ lớn. TSP vẫn có thể tối ưu.

**Vùng giữa đường `q = 3` và đường `q ≤ 2`**  
Parking đã đủ lớn để ảnh hưởng khi người giao có sức chứa `q = 3`, nhưng chưa đủ lớn để làm thay đổi nghiệm trong trường hợp `q ≤ 2`.

**Vùng trên đường `q ≤ 2`**  
Parking time lớn. Đỗ ở từng khách không còn tối ưu cho cả hai trường hợp. CDPP nên chọn ít điểm đỗ hơn, gom khách thành các walking loop, và giảm số lần đỗ.

### 4. Kết luận từ Fig. 2

Trong môi trường đô thị, khách hàng gần nhau nên chỉ cần parking time nhỏ cũng đủ làm thay đổi nghiệm tối ưu. Với `q = 3`, paper chỉ ra rằng nếu:

```text
p > 1.6 phút
```

thì TSP đỗ ở từng khách không còn tối ưu.

Trong môi trường nông thôn, khách hàng xa nhau hơn. Việc đi bộ gom khách kém hiệu quả, nên cần parking time lớn hơn mới làm CDPP khác TSP. Paper cho thấy trong vùng rural, nếu:

```text
p < 6 phút
```

thì TSP vẫn xấp xỉ hoặc giữ vai trò rất tốt.

Nói ngắn gọn: **Fig. 2 giải thích bằng phân tích lý thuyết rằng parking càng đắt và khách càng gần nhau thì càng cần CDPP thay cho TSP.**

---

## Fig. 3: Phần trăm giảm completion time khi dùng CDPP

Fig. 3 là kết quả thực nghiệm trong base case, dùng để chứng minh rằng CDPP tốt hơn các benchmark.

Base case gồm:

```text
n = 50 khách hàng
q = 3 gói
f = 2.1 phút/gói
```

Parking time theo từng vùng:

```text
Cook County:       p = 9 phút
Adams County:      p = 5 phút
Cumberland County: p = 1 phút
```

### 1. Completion time là gì?

Completion time là tổng thời gian hoàn thành tour giao hàng:

```text
Completion time = Driving time + Parking time + Walking time + Loading time
```

Trong CDPP, objective trực tiếp tối thiểu hóa completion time.

### 2. Công thức phần trăm giảm trong Fig. 3

Mỗi cột trong Fig. 3 biểu diễn mức giảm completion time của CDPP so với một benchmark:

```text
Percent reduction = ((T_benchmark - T_CDPP) / T_benchmark) × 100%
```

Trong đó:

- `T_CDPP`: completion time của CDPP.
- `T_benchmark`: completion time của benchmark được so sánh.

Nếu giá trị là `53%`, nghĩa là dùng CDPP giúp giảm 53% thời gian hoàn thành so với benchmark đó.

### 3. Các benchmark trong Fig. 3

**Relaxed M-S với `α = 0.5`**  
Benchmark dựa trên mô hình Martinez-Sykora, sử dụng weighted sum giữa driving time và walking time. Với `α = 0.5`, driving và walking được cân bằng tương đối.

**Relaxed M-S với `α = 0.6`**  
Tăng trọng số cho driving time so với `α = 0.5`.

**Relaxed M-S với `α = 0.8`**  
Trọng số driving cao hơn nữa. Benchmark này vẫn không đưa parking time trực tiếp vào objective, nên có thể tạo nghiệm không tối ưu khi xét completion time thực tế.

Objective của Relaxed M-S có dạng:

```text
α × Driving time + (1 - α) × Walking time
```

Sau đó, completion time thực tế được tính lại bằng cách cộng thêm loading time và parking time.

**Modified TSP**  
Benchmark gần với thực hành công nghiệp. Nó lấy thứ tự phục vụ từ TSP, sau đó tối ưu việc đỗ xe và đi bộ theo thứ tự đã cố định. Vì thứ tự khách hàng bị cố định bởi TSP, Modified TSP kém linh hoạt hơn CDPP.

### 4. Ý nghĩa từng nhóm cột theo county

#### Cook County

Cook County đại diện cho môi trường đô thị: mật độ khách cao, khách gần nhau, parking time lớn.

Kết quả paper:

```text
CDPP giảm 53% so với Relaxed M-S α = 0.5
CDPP giảm 53% so với Relaxed M-S α = 0.6
CDPP giảm 48% so với Relaxed M-S α = 0.8
CDPP giảm 11% so với Modified TSP
```

Ý nghĩa: trong đô thị, parking time cao làm các mô hình không xét parking bị thiệt hại nặng. CDPP thắng rõ rệt vì nó chủ động giảm số lần đỗ, chấp nhận đi bộ nhiều hơn để tránh mất thời gian tìm chỗ đỗ.

#### Adams County

Adams County đại diện cho môi trường suburban: mật độ khách trung bình, parking time trung bình.

Kết quả paper:

```text
CDPP giảm 29% so với Relaxed M-S α = 0.5
CDPP giảm 28% so với Relaxed M-S α = 0.6
CDPP giảm 20% so với Relaxed M-S α = 0.8
CDPP giảm 6% so với Modified TSP
```

Ý nghĩa: parking vẫn quan trọng, nhưng lợi ích thấp hơn Cook County vì khách hàng xa nhau hơn. Khi khách xa hơn, việc đi bộ gom nhiều khách từ một điểm đỗ không còn hiệu quả bằng đô thị.

#### Cumberland County

Cumberland County đại diện cho môi trường nông thôn: khách xa nhau, parking time thấp.

Kết quả paper:

```text
CDPP giảm 3% so với Relaxed M-S α = 0.5
CDPP giảm 3% so với Relaxed M-S α = 0.6
CDPP giảm 6% so với Relaxed M-S α = 0.8
CDPP giảm 1% so với Modified TSP
```

Ý nghĩa: CDPP chỉ cải thiện rất ít. Trong rural, khách xa nhau nên đi bộ gom khách không hiệu quả. Parking time lại thấp, nên đỗ ở nhiều khách không gây thiệt hại lớn. Vì vậy TSP hoặc Modified TSP gần như đủ tốt.

### 5. Kết luận từ Fig. 3

Fig. 3 chứng minh bằng thực nghiệm rằng:

1. CDPP luôn tốt hơn các benchmark trong base case.
2. Lợi ích của CDPP lớn nhất ở đô thị.
3. Lợi ích giảm dần khi chuyển từ urban sang suburban rồi rural.
4. Modified TSP là benchmark mạnh hơn Relaxed M-S, nhưng vẫn thua CDPP vì bị cố định thứ tự phục vụ.
5. Parking time phải được đưa trực tiếp vào objective, vì weighted sum giữa driving và walking không đủ để thay thế tác động của parking.

Nói ngắn gọn: **Fig. 3 là bằng chứng thực nghiệm cho kết luận chính của paper: parking matters, đặc biệt trong last-mile delivery ở đô thị.**

---

## Liên hệ giữa Fig. 2 và Fig. 3

Fig. 2 là phân tích lý thuyết trên lưới khách hàng. Nó cho thấy khi parking time vượt một ngưỡng, TSP đỗ ở từng khách không còn tối ưu.

Fig. 3 là kiểm chứng thực nghiệm trên dữ liệu thực tế của Illinois. Nó cho thấy đúng xu hướng mà Fig. 2 dự đoán:

- Cook County: khách gần, parking time cao → CDPP thắng mạnh.
- Adams County: mức trung gian → CDPP thắng vừa phải.
- Cumberland County: khách xa, parking time thấp → CDPP chỉ thắng rất ít.

Do đó, hai hình bổ trợ cho nhau:

```text
Fig. 2: giải thích vì sao parking matters về mặt lý thuyết.
Fig. 3: chứng minh parking matters bằng thực nghiệm.
```
