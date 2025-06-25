
### 1. Створення віртуального оточення
```bash
python3 -m venv venv
```

### 2. Активація віртуального оточення
```bash
# Linux
source venv/bin/activate

### 3. Встановлення залежностей
```bash
pip install -r requirements.txt
```

### 4. Запуск сервера
```bash
cd url_shortener
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```