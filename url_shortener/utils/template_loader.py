import os
from typing import Dict, Any

def load_template(template_name: str) -> str:
    """Завантажує HTML шаблон з файлу"""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(current_dir, "templates", "emails", template_name)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template {template_name} not found at {template_path}")
    except Exception as e:
        raise Exception(f"Error loading template {template_name}: {str(e)}")

def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """Завантажує шаблон та підставляє змінні"""
    template_content = load_template(template_name)
    
    # Простий механізм підстановки змінних {{variable}}
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        template_content = template_content.replace(placeholder, str(value))
    
    return template_content

def get_text_version(html_content: str) -> str:
    """Створює текстову версію з HTML (простий варіант)"""
    import re
    
    # Видаляємо HTML теги
    text = re.sub(r'<[^>]+>', '', html_content)
    
    # Замінюємо множинні пробіли та переноси рядків
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Очищуємо початок та кінець
    text = text.strip()
    
    return text 