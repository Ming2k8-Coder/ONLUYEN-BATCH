import json

def convert_assignment_json_to_dict(json_data_string: str) -> dict:
    """
    Chuyển đổi chuỗi JSON của bài tập thành một dictionary theo cấu trúc yêu cầu.

    Cấu trúc đầu ra yêu cầu:
    {
        'assignId': ...,
        'assignmentContentType': ...,
        'name': ...,
        'data': [
            {
                'stepIndex': ...,             # <-- Đã thêm trường này
                'content-dataStandard': ...,
                'numberquestion': ...,
                'content': [
                    # Nội dung của các tùy chọn được chọn dựa trên 3 điều kiện:
                    # 1. Nếu chỉ có MỘT tùy chọn có "isAnswer": true -> Chọn nội dung tùy chọn đó.
                    # 2. Nếu có 0, 2, hoặc nhiều hơn 2 "isAnswer": true, VÀ "rightAnswer": true -> Chọn nội dung các tùy chọn có "userSelected": true.
                    # 3. Các trường hợp còn lại -> Nội dung rỗng ([]).
                ]
            },
            ...
        ]
    }
    """
    try:
        # Tải dữ liệu từ chuỗi JSON
        data_json = json.loads(json_data_string)
        detail = data_json.get('data', {}).get('dataDetail', {})

        # Khởi tạo danh sách chứa dữ liệu câu hỏi đã xử lý
        processed_questions = []

        # Lặp qua từng mục trong danh sách 'data' của 'dataDetail'
        # Sử dụng enumerate để lấy chỉ mục (index) và tính toán stepIndex
        for index, item in enumerate(detail.get('data', [])):
            q = item.get('dataStandard', {})

            # Lấy các giá trị cơ bản của câu hỏi
            question_content = q.get('content', '')
            question_number = q.get('numberQuestion', None)
            is_question_right = q.get('rightAnswer', False)
            options = q.get('options', [])

            # --- TÍNH TOÁN CÁC ĐÁP ÁN ĐÚNG ---
            # Tìm danh sách các tùy chọn có isAnswer = true
            correct_options = [opt for opt in options if opt.get('isAnswer', False)]
            num_correct_options = len(correct_options)

            # Tập hợp (set) để lưu trữ nội dung tùy chọn đã lọc
            filtered_contents = set()

            # --- ÁP DỤNG LOGIC LỌC MỚI ---

            # 1. Điều kiện 1: Nếu chỉ có một đáp án đúng (isAnswer = true)
            if num_correct_options == 1:
                # Lấy nội dung của đáp án đúng duy nhất đó
                content = correct_options[0].get('content')
                if content is not None:
                    filtered_contents.add(content)
            
            # 2. Điều kiện 2: Nếu Condition 1 KHÔNG thỏa mãn (0, 2, hoặc >2 đáp án đúng)
            # VÀ câu hỏi được trả lời đúng tổng thể
            elif is_question_right:
                # Lấy nội dung của TẤT CẢ các tùy chọn mà người dùng đã chọn
                for option in options:
                    if option.get('userSelected', False):
                        content = option.get('content')
                        if content is not None:
                            filtered_contents.add(content)
            
            # 3. Điều kiện 3: Các trường hợp còn lại, filtered_contents sẽ là tập rỗng (đã được khởi tạo)

            # Tính toán Step Index (Bắt đầu từ 1)
            step_index = index + 1

            # Tạo dictionary cho câu hỏi đã xử lý, bao gồm stepIndex mới
            processed_question = {
                'stepIndex': step_index, # <-- Đã thêm stepIndex
                'content-dataStandard': question_content,
                'numberquestion': question_number,
                'content': list(filtered_contents) # Chuyển set về list để hoàn thành cấu trúc
            }
            processed_questions.append(processed_question)

        # Xây dựng dictionary đầu ra cuối cùng
        output_dict = {
            'assignId': detail.get('id', ''),
            'assignmentContentType': detail.get('assignmentContentType', None),
            'name': detail.get('name', ''),
            'data': processed_questions
        }

        return output_dict

    except json.JSONDecodeError as e:
        print(f"Lỗi giải mã JSON: {e}")
        return {}
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")
        return {}


if __name__ == "__main__":
    # --- Dữ liệu đầu vào (Đã được chỉnh sửa để kiểm tra 3 logic) ---
    json_input = """
    {
        "success": true,
        "data": {
            "dataDetail": {
                "id": "69181dc79611cb0b6f95c433",
                "name": "Di truyền liên kết giới tính, liên kết gene và hoán vị gene",
                "assignmentType": 0,
                "assignmentContentType": 0,
                "data": [
                    {
                        "dataStandard": {
                            "content": "Câu 1: Kiểm tra ĐK 1 (Chỉ 1 isAnswer=true)",
                            "options": [
                                {"content": "<p>A: Đáp án đúng duy nhất (isAnswer=true)</p>", "isAnswer": true, "userSelected": false},
                                {"content": "<p>B: Tùy chọn khác</p>", "isAnswer": false, "userSelected": true}
                            ],
                            "rightAnswer": true,
                            "numberQuestion": 13052966
                        }
                    },
                    {
                        "dataStandard": {
                            "content": "Câu 2: Kiểm tra ĐK 2 (2 isAnswer=true, rightAnswer=true)",
                            "options": [
                                {"content": "<p>A: Tùy chọn được chọn (userSelected=true)</p>", "isAnswer": false, "userSelected": true},
                                {"content": "<p>B: Đáp án đúng #1 (isAnswer=true)</p>", "isAnswer": true, "userSelected": true},
                                {"content": "<p>C: Đáp án đúng #2 (isAnswer=true)</p>", "isAnswer": true, "userSelected": false}
                            ],
                            "rightAnswer": true,
                            "numberQuestion": 13052967
                        }
                    },
                    {
                        "dataStandard": {
                            "content": "Câu 3: Kiểm tra ĐK 3 (Không có isAnswer, rightAnswer=false)",
                            "options": [
                                {"content": "<p>A: Tùy chọn được chọn (userSelected=true)</p>", "isAnswer": false, "userSelected": true},
                                {"content": "<p>B: Tùy chọn không được chọn</p>", "isAnswer": false, "userSelected": false}
                            ],
                            "rightAnswer": false,
                            "numberQuestion": 13052968
                        }
                    }
                ]
            }
        },
        "totalRecords": 0, "elapsed": 0.02, "timeServer": 1763293092, "timeResp": "16/11/2025 18:38", "message": "Thành công", "status": 1
    }
    """
    # with open("Nguyễn Việt Anh-6912d78b1b317995c13313d1.json","r",encoding = 'utf8') as f:
    #     json_input=f.read()
    # Thực thi hàm và in kết quả
    result_dict = convert_assignment_json_to_dict(json_input)

    print("--- Dictionary Kết Quả ---")
    print(json.dumps(result_dict, indent=4, ensure_ascii=False))

    print("\n--- Giải Thích Lọc Nội Dung Theo Điều Kiện Mới ---")
    if result_dict and result_dict.get('data'):
        # Kiểm tra Câu 1: Chỉ lấy đáp án có isAnswer=true
        q1 = result_dict['data'][0]
        print(f"1. Câu hỏi '{q1['content-dataStandard'][:20]}...':")
        print(f"   -> stepIndex: {q1.get('stepIndex')}, Kết quả: {q1['content']}. (Chỉ lấy A, bỏ qua B vì ĐK 1 thỏa mãn)")

        # Kiểm tra Câu 2: Lấy tất cả đáp án userSelected=true
        q2 = result_dict['data'][1]
        print(f"2. Câu hỏi '{q2['content-dataStandard'][:20]}...':")
        print(f"   -> stepIndex: {q2.get('stepIndex')}, Kết quả: {q2['content']}. (Lấy A và B vì ĐK 1 không thỏa (2 đáp án đúng) và ĐK 2 thỏa (rightAnswer=true))")

        # Kiểm tra Câu 3: Lấy None (List rỗng)
        q3 = result_dict['data'][2]
        print(f"3. Câu hỏi '{q3['content-dataStandard'][:20]}...':")
        print(f"   -> stepIndex: {q3.get('stepIndex')}, Kết quả: {q3['content']}. (List rỗng vì ĐK 1 không thỏa (0 đáp án đúng) và ĐK 2 không thỏa (rightAnswer=false))")