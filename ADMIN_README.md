# QR Menu Admin Panel

This is an advanced CRUD admin panel for the QR Menu system built with Flask.

## Features

### Authentication
- Simple login system (admin/admin123)
- Session-based authentication
- Protected admin routes

### Categories Management
- **Create**: Add new menu categories
- **Read**: View all categories in a clean list
- **Update**: Edit category names
- **Delete**: Remove categories (with validation to prevent deleting categories with menu items)

### Menu Items Management
- **Create**: Add new menu items with:
  - Name, price, portion size
  - Category assignment
  - Image upload support
- **Read**: View all menu items with category information and images
- **Update**: Edit all menu item details including image replacement
- **Delete**: Remove menu items

### User Interface
- Modern, responsive design using Tailwind CSS
- Russian language interface
- Intuitive navigation with breadcrumbs
- Flash messages for user feedback
- Image preview and upload functionality

## File Structure

```
api/
├── admin.py          # Admin routes and CRUD operations
└── menu.py           # Public menu API

templates/
├── admin/
│   ├── login.html           # Login page
│   ├── dashboard.html       # Admin dashboard
│   ├── categories.html      # Categories list
│   ├── add_category.html    # Add category form
│   ├── edit_category.html   # Edit category form
│   ├── menu.html            # Menu items list
│   ├── add_menu_item.html   # Add menu item form
│   └── edit_menu_item.html  # Edit menu item form
└── index.html        # Public menu page

static/
└── resource/
    └── img/          # Uploaded menu item images
```

## Database Schema

The admin panel works with two main tables:

### categories
- `id` (INT, PRIMARY KEY, AUTO_INCREMENT)
- `name` (VARCHAR(100))

### menu
- `id` (INT, PRIMARY KEY, AUTO_INCREMENT)
- `name` (VARCHAR(200))
- `price` (INT)
- `amount` (VARCHAR(50)) - portion size
- `image` (VARCHAR(255)) - image path
- `category_id` (INT) - foreign key to categories

## Usage

1. **Access Admin Panel**: Navigate to `/admin/login`
2. **Login**: Use credentials `admin` / `admin123`
3. **Dashboard**: Overview of available management options
4. **Categories**: Manage menu categories
5. **Menu**: Manage individual menu items

## Security Notes

- This uses a simple authentication system for demonstration
- In production, implement proper password hashing and user management
- Consider using Flask-Login or similar for session management
- Add CSRF protection for forms
- Validate file uploads more thoroughly

## API Endpoints

### Authentication
- `GET /admin/login` - Login page
- `POST /admin/login` - Process login
- `GET /admin/logout` - Logout

### Dashboard
- `GET /admin/` - Admin dashboard

### Categories
- `GET /admin/categories` - List categories
- `GET /admin/categories/add` - Add category form
- `POST /admin/categories/add` - Create category
- `GET /admin/categories/edit/<id>` - Edit category form
- `POST /admin/categories/edit/<id>` - Update category
- `POST /admin/categories/delete/<id>` - Delete category

### Menu Items
- `GET /admin/menu` - List menu items
- `GET /admin/menu/add` - Add menu item form
- `POST /admin/menu/add` - Create menu item
- `GET /admin/menu/edit/<id>` - Edit menu item form
- `POST /admin/menu/edit/<id>` - Update menu item
- `POST /admin/menu/delete/<id>` - Delete menu item

## Image Upload

- Images are stored in `static/resource/img/`
- Supported formats: PNG, JPG, JPEG, GIF
- Images are served at `/static/resource/img/filename`
- File names are secured using Werkzeug's `secure_filename`

## Development

To run the application:

```bash
pip install -r requirements.txt
python app.py
```

Access the admin panel at: `http://localhost:5000/admin/login`