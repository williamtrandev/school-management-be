# Hệ thống Quản lý Thi đua Học đường

Hệ thống RESTful API đơn giản cho quản lý thi đua học đường với JWT authentication, được tổ chức theo cấu trúc applications với function-based views.

## 🏗️ Cấu trúc Project

```
school-management-backend/
├── applications/                 # Các ứng dụng chức năng
│   ├── user_management/         # App Quản lý người dùng
│   │   ├── models.py           # User model
│   │   ├── serializers.py      # Request/Response serializers
│   │   ├── views.py            # Function-based views
│   │   ├── urls.py             # URL patterns
│   │   └── apps.py
│   ├── event/                  # App Sự kiện thi đua
│   │   ├── models.py           # Event, EventType models
│   │   ├── serializers.py      # Request/Response serializers
│   │   ├── views.py            # Function-based views
│   │   ├── urls.py             # URL patterns
│   │   └── apps.py
│   ├── grade/                  # App Khối lớp
│   ├── classroom/              # App Lớp học (tránh keyword class)
│   ├── student/                # App Học sinh
│   ├── teacher/                # App Giáo viên
│   ├── week_summary/           # App Tổng hợp tuần
│   ├── notification/           # App Thông báo
│   ├── point_rule/             # App Quy tắc điểm
│   ├── permissions.py          # Custom permissions
│   └── urls.py                 # Main URL routing
├── school_management/           # Django project settings
├── requirements.txt            # Dependencies
├── manage.py                   # Django management
├── install_dependencies.py     # Script cài đặt dependencies
├── database_setup.py           # Script setup MySQL
├── migrate_all.py              # Script migration tất cả apps
├── env_template.txt            # Template cho environment variables
└── README.md                   # Documentation
```

## 🚀 Tính năng chính

- **Authentication**: Đăng nhập, đăng ký, đổi mật khẩu với JWT
- **Quản lý người dùng**: Admin, Giáo viên, Học sinh
- **Quản lý lớp học**: Khối, lớp, GVCN
- **Ghi nhận sự kiện thi đua**: Tiết học, chuyên cần, nề nếp, vệ sinh
- **Dashboard**: Thống kê và báo cáo

## 🛠️ Công nghệ sử dụng

- **Backend**: Django 5.2 + Django REST Framework
- **Database**: MySQL 8.0+
- **Authentication**: JWT (JSON Web Tokens)
- **Architecture**: Applications-based structure với function-based views

## 📋 Cài đặt

### 1. Cài đặt MySQL Server

#### macOS
```bash
# Cài đặt MySQL
brew install mysql

# Khởi động MySQL service
brew services start mysql

# Thiết lập password cho root user
mysql_secure_installation
```

#### Ubuntu/Debian
```bash
# Cài đặt MySQL
sudo apt-get update
sudo apt-get install mysql-server

# Khởi động MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Thiết lập bảo mật
sudo mysql_secure_installation
```

#### Windows
- Tải MySQL từ: https://dev.mysql.com/downloads/mysql/
- Cài đặt và thiết lập password cho root user

### 2. Cài đặt Python Dependencies

#### Cách 1: Sử dụng script tự động
```bash
# Chạy script cài đặt dependencies
python3 install_dependencies.py
```

#### Cách 2: Cài đặt thủ công
```bash
# Tạo virtual environment (khuyến nghị)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

#### Troubleshooting MySQL Dependencies

**macOS:**
```bash
# Cài đặt MySQL connector
brew install mysql-connector-c

# Sau đó cài đặt Python dependencies
pip install -r requirements.txt
```

**Ubuntu/Debian:**
```bash
# Cài đặt system dependencies
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential

# Sau đó cài đặt Python dependencies
pip install -r requirements.txt
```

**Windows:**
- Tải MySQL client từ: https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient
- Cài đặt file .whl tương ứng với Python version

### 3. Setup Environment Variables

```bash
# Tạo file .env từ template
cp env_template.txt .env

# Chỉnh sửa file .env với thông tin database thực tế
nano .env
```

**Nội dung file .env:**
```bash
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=school_management
DB_USER=root
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=3306

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=1
JWT_REFRESH_TOKEN_LIFETIME=7

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 4. Setup Database

```bash
# Chạy script setup database
python3 database_setup.py

# Hoặc tạo database thủ công
mysql -u root -p
CREATE DATABASE school_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 5. Migration Database
```bash
# Cách 1: Migration tất cả apps cùng lúc
python3 migrate_all.py

# Cách 2: Migration từng app
python3 manage.py makemigrations user_management event grade classroom student teacher week_summary notification point_rule
python3 manage.py migrate
```

### 6. Tạo superuser
```bash
python3 manage.py createsuperuser
```

### 7. Chạy server
```bash
python3 manage.py runserver
```

## 🔐 Authentication

### Đăng nhập
```http
POST /api/auth/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

### Response
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": "uuid",
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "first_name": "Admin",
        "last_name": "User"
    }
}
```

### Sử dụng token
```http
GET /api/auth/users
Authorization: Bearer <access_token>
```

## 📚 API Endpoints

### User Management App (`/api/auth/`)
- `POST /api/auth/auth/login` - Đăng nhập
- `POST /api/auth/auth/register` - Đăng ký
- `POST /api/auth/auth/refresh` - Refresh token
- `POST /api/auth/auth/logout` - Đăng xuất
- `POST /api/auth/auth/change_password` - Đổi mật khẩu
- `GET /api/auth/users` - Danh sách users (Admin only)
- `GET /api/auth/users/profile` - Profile hiện tại
- `PUT /api/auth/users/update_profile` - Cập nhật profile

### Event App (`/api/`)
- `GET /api/events` - Danh sách sự kiện
- `POST /api/events/create` - Tạo sự kiện mới (Admin/Teacher)
- `GET /api/events/{id}` - Chi tiết sự kiện
- `PUT /api/events/{id}/update` - Cập nhật sự kiện
- `DELETE /api/events/{id}/delete` - Xóa sự kiện
- `POST /api/events/bulk_create` - Tạo nhiều sự kiện
- `GET /api/event-types` - Danh sách loại sự kiện
- `POST /api/event-types/create` - Tạo loại sự kiện mới
- `GET /api/event-types/{id}` - Chi tiết loại sự kiện
- `PUT /api/event-types/{id}/update` - Cập nhật loại sự kiện
- `DELETE /api/event-types/{id}/delete` - Xóa loại sự kiện

## 🔍 Query Parameters

### Filtering
```http
GET /api/events?classroom_id=uuid&event_type_id=uuid&date=2024-01-15
GET /api/auth/users?role=teacher
```

### Pagination
```http
GET /api/events?page=1&page_size=10
```

## 👥 Roles và Permissions

### Admin
- Quản lý toàn bộ hệ thống
- CRUD tất cả entities

### Teacher
- Tạo/sửa sự kiện thi đua
- Xem thông tin lớp mình phụ trách

### Student
- Xem thông tin lớp mình
- Chỉ đọc (read-only)

## 📊 Ví dụ sử dụng

### 1. Tạo sự kiện thi đua
```http
POST /api/events/create
Authorization: Bearer <token>
Content-Type: application/json

{
    "event_type": "uuid",
    "classroom": "uuid",
    "student": "uuid",
    "date": "2024-01-15",
    "period": 3,
    "points": 5,
    "description": "Học tập tốt"
}
```

### 2. Tạo nhiều sự kiện cùng lúc
```http
POST /api/events/bulk_create
Authorization: Bearer <token>
Content-Type: application/json

{
    "events": [
        {
            "event_type": "uuid",
            "classroom": "uuid",
            "date": "2024-01-15",
            "points": 5,
            "description": "Sự kiện 1"
        },
        {
            "event_type": "uuid",
            "classroom": "uuid",
            "date": "2024-01-15",
            "points": -2,
            "description": "Sự kiện 2"
        }
    ]
}
```

## 🎯 Đặc điểm

- **Applications-based**: Mỗi chức năng được tổ chức thành app riêng
- **Function-based Views**: Sử dụng function thay vì ViewSet
- **Custom URLs**: URL patterns được định nghĩa thủ công
- **MySQL Database**: Database mạnh mẽ và ổn định
- **Environment Variables**: Bảo mật thông tin nhạy cảm
- **Clean Structure**: Cấu trúc rõ ràng, dễ hiểu
- **RESTful**: Tuân thủ REST API conventions
- **JWT**: Authentication an toàn
- **Permissions**: Role-based access control

## 🚀 Deployment

### Production Settings
1. Cập nhật `DEBUG = False` trong file `.env`
2. Cấu hình MySQL production với connection pooling
3. Cấu hình CORS cho domain thực tế
4. Sử dụng environment variables cho tất cả thông tin nhạy cảm
5. Setup SSL/TLS cho MySQL connection

### Environment Variables cho Production
```bash
# Database
DB_NAME=school_management
DB_USER=django_user
DB_PASSWORD=your_secure_password
DB_HOST=your_mysql_host
DB_PORT=3306

# Django
SECRET_KEY=your_production_secret_key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# JWT
JWT_ACCESS_TOKEN_LIFETIME=1
JWT_REFRESH_TOKEN_LIFETIME=7

# CORS
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## 📝 Development

### Thêm App mới
1. Tạo cấu trúc thư mục trong `applications/`
2. Tạo models.py, serializers.py, views.py, urls.py, apps.py
3. Thêm vào `INSTALLED_APPS` trong settings.py
4. Thêm vào `applications/urls.py`

### Migration tất cả apps
```bash
# Sử dụng script tự động
python3 migrate_all.py

# Hoặc migration thủ công
python3 manage.py makemigrations user_management event grade classroom student teacher week_summary notification point_rule
python3 manage.py migrate
```

### Testing
```bash
python3 manage.py test
```

## 🔧 Troubleshooting

### MySQL Connection Issues
1. Kiểm tra MySQL service đang chạy
2. Kiểm tra thông tin trong file `.env`
3. Kiểm tra database đã được tạo
4. Kiểm tra user permissions

### Dependencies Issues
1. Chạy `python3 install_dependencies.py` để kiểm tra
2. Cài đặt system dependencies cho MySQL
3. Sử dụng virtual environment
4. Kiểm tra Python version compatibility

### Environment Variables Issues
1. Đảm bảo file `.env` tồn tại và có đúng format
2. Kiểm tra tên biến trong file `.env` khớp với settings.py
3. Restart Django server sau khi thay đổi `.env`

### Migration Issues
1. Xóa tất cả migration files cũ
2. Chạy `python3 manage.py makemigrations` lại
3. Kiểm tra database connection

## 🔒 Security Best Practices

### Development
- Sử dụng file `.env` để lưu trữ thông tin nhạy cảm
- Không commit file `.env` vào git
- Sử dụng strong passwords cho database
- Sử dụng virtual environment

### Production
- Sử dụng environment variables của server
- Cấu hình firewall cho MySQL
- Sử dụng SSL/TLS cho database connection
- Regular backup database
- Monitor database performance

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

MIT License 