# Tài liệu chuẩn bị demo: 3 prompt, 3 hành vi

Nguồn bằng chứng: `runs/v3_B_base_gemini_20260729T155303255458.json`.
Run v3 hợp lệ: 20/20 ca đạt, `provider_error_cases=0`.

## Mục tiêu demo

Cho thấy tác tử có thể chọn đúng công cụ, không đoán khi thiếu dữ liệu và phối hợp nhiều công cụ trong một yêu cầu. Không trình bày source code; chỉ nhập prompt, quan sát tool trace và giải thích hành vi.

## Kịch bản 1: Gọi công cụ chính

**Prompt nhập vào:** `Tin tức AI hôm nay có gì nổi bật?`

**Hành vi cần quan sát:** Tác tử nhận diện đây là yêu cầu tìm tin tức trên web trong ngày, sau đó gọi đúng một công cụ tìm kiếm web.

**Tool trace mong đợi:** `lookup(query=AI, topic=news, timeframe=day)`

**Bằng chứng trong run:** `R03_web_news_routing` - PASS, đúng cả công cụ lẫn tham số.

**Câu nói khi demo:** "Tác tử tách chủ đề AI khỏi thông tin thời gian. Vì vậy `query` chỉ là AI, còn hôm nay được chuyển thành `timeframe=day`."

## Kịch bản 2: Thiếu thông tin

**Prompt nhập vào:** `Tóm tắt bài viết này hộ mình`

**Hành vi cần quan sát:** Không tự chọn bài viết và không gọi `fetch` khi chưa có URL. Tác tử phải hỏi người dùng cung cấp đường dẫn.

**Tool trace mong đợi:** `clarify(question="Bạn vui lòng cung cấp đường dẫn (URL) của bài viết cần tóm tắt nhé!", response_type=text)`

**Bằng chứng trong run:** `R11_missing_url` - PASS, tác tử chuyển sang trạng thái chờ URL.

**Câu nói khi demo:** "Đây là ranh giới an toàn: thiếu dữ liệu bắt buộc thì tác tử hỏi lại, không đoán bừa."

## Kịch bản 3: Thử thách đa công cụ

**Prompt nhập vào:** `Tìm trên web tin AI hôm nay và tìm thêm tweet về AI.`

**Hành vi cần quan sát:** Tác tử tách yêu cầu thành hai nguồn dữ liệu: tin tức web và bài đăng Twitter/X; sau đó gọi hai công cụ trong cùng một lượt.

**Tool trace mong đợi:**

- `lookup(query=AI, topic=news, timeframe=day)`
- `social_search(query=AI, search_type=Latest)`

**Bằng chứng trong run:** `R13_parallel_web_and_tweets` - PASS, đúng cả hai lời gọi và tham số.

**Câu nói khi demo:** "Một prompt nhưng có hai ý khác nhau. Tác tử không bỏ sót ý nào: web news đi vào `lookup`, còn tweet đi vào `social_search`."

## Thứ tự thực hiện

Chạy lần lượt kịch bản 1, 2, 3. Sau mỗi prompt, chỉ vào tool trace và giải thích đúng một ý: chọn đúng tool, hỏi lại khi thiếu dữ liệu, hoặc phối hợp hai tool.
