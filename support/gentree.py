# Đóng vai trò là "tác giả" của paper trong file parking_matter.txt, hãy đưa ra 1 file notebook thực hiện "đầu đủ" và "chi tiết" quá trình để có phần kết quả trong mục "thực nghiệm của bài báo.
from pathlib import Path

# Thư mục cần quét
root_dir = Path(__file__).parents[2]   # đổi thành thư mục của bạn

# File đầu ra
output_file = Path("tree.txt")

with output_file.open("w", encoding="utf-8") as f:
    for file_path in root_dir.rglob("*"):
        if file_path.is_file():
            f.write(str(file_path.resolve()) + "\n")

print(f"Đã xuất danh sách file vào: {output_file.resolve()}")