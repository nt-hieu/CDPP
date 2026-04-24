# 1.Phương pháp tối ưu chính: Two-echelon heuristic
MIP cho CDPP (exact optimization)

- Bài toán: CDPP – Capacitated Delivery Problem with Parking
- Mục tiêu: giải gần tối ưu thay cho MIP do giải giải được ~ 50 khách hàng với chi phí tính toán rất cao.
- Cách giải: Chi bài toán thành 2 tầng
    - PA-R: Parking Assignment & Routing
        - Mục đích: 
            - chọn điểm đỗ
            - gán khách vào điểm đỗ
            - tìm route giữa các điểm đỗ
        - Cách giải: 
            - Min (parking time + walking assignment)
            - Sử dụng TSP trên các điểm đỗ
    - SSA: Service Set Assignment
        - Mục đích: chia khách đã gán cho từng điểm đỗ thành các service set để tối ưu phần đi bộ.
        - Cách giải: 
            - Min (walking assignment)
# 2. Mục tiêu của paper
- Đưa parking time vào objective function của MIP
- Cho phép 1 điểm đỗ phục vụ nhiều nhóm khách hàng
- Tối ưu đồng thời 3 quyết định: 
    - chọn điểm đỗ
    - đỗ bao nhiêu lần
    - đi bộ trong bao lâu

# 3. So sánh với các phương pháp cũ

| Phương pháp      | Điểm yếu                           |
| ---------------- | ---------------------------------- |
| TSP              | đỗ ở mọi khách → quá nhiều parking |
| M-S (literature) | không có parking time              |
| Modified TSP     | fix thứ tự → không tối ưu toàn cục |

- M-S (Martinez-Sykora et al. 2020) - một mô hình 2 lớp (two-echolon routing) cho last-mile delivery có kết hợp driving + walking. Trong mô hình gốc của họ:
    - Khách hàng được chia thành các cluster (services sets)
    - Mỗi cluster bắt buộc phải có một parking location riêng
    - Giá trị tính toán = sum (driving + walking), không có parking time
    - với set up 1 cluster - 1 service -> đánh giá trên benchmark bị yếu

- Relaxed M-S:
    - Cho phép nhiều services sets dùng chung 1 parking spot
    - Không bắt buộc "1 cluster <-> 1 parking"
    - Từ đó sinh ra khác biệt chính:
        - tối ưu sum (/alpha * driving + (1-/alpha)*walking)
        - đỗ rồi muốn đi bộ bao nhiêu vòng cũng được

- CDPP = Relaxed M-S + chi phí parking vào objective
    - Do đó để đo ảnh hưởng ta chỉ cần dùng Relaxed M-S để so sánh với TSP như fig3.

