# 1 # ใช้ base image ที่มี Python (แนะนำให้ใช้เวอร์ชัน slim เพื่อลดขนาด image)
FROM python:3.9-slim-buster

# 3 # ตั้ง working directory ใน container
WORKDIR /app

# 6 # คัดลอก requirements.txt ไปยัง /app และติดตั้ง dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 9 # คัดลอก code ทั้งหมดของ Flask app ไปยัง /app
COPY . /app/

# 13 # ตั้งค่า environment variables (ถ้าจำเป็น)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# 17 # Expose port ที่ Flask app จะรัน (default คือ 5000, แต่ code ใช้ 5001)
EXPOSE 5001

# 20 # Command ที่จะรันเมื่อ container เริ่มทำงาน
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]