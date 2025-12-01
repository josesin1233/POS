import re
import os
from pathlib import Path

def remove_emojis(text):
    """
    Elimina todos los emojis del texto usando expresiones regulares.
    Cubre todos los rangos Unicode de emojis de manera precisa.
    """
    # Patrón más completo y preciso para emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticones
        "\U0001F300-\U0001F5FF"  # Símbolos y pictogramas
        "\U0001F680-\U0001F6FF"  # Transporte y símbolos de mapas
        "\U0001F700-\U0001F77F"  # Símbolos alquímicos
        "\U0001F780-\U0001F7FF"  # Símbolos geométricos extendidos
        "\U0001F800-\U0001F8FF"  # Flechas suplementarias-C
        "\U0001F900-\U0001F9FF"  # Símbolos y pictogramas suplementarios
        "\U0001FA00-\U0001FA6F"  # Chess symbols
        "\U0001FA70-\U0001FAFF"  # Símbolos y pictogramas extendidos-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Varios símbolos y pictogramas
        "\U0001F926-\U0001F937"  # Gestos y personas
        "\U0001F1E0-\U0001F1FF"  # Banderas regionales
        "\U00002600-\U000026FF"  # Símbolos varios
        "\U00002700-\U000027BF"  # Dingbats
        "\U0001F018-\U0001F270"  # Varios símbolos técnicos
        "\U0001F300-\U0001F5FF"  # Símbolos varios
        "\U0001F910-\U0001F96B"  # Caras emocionales
        "\U0001F980-\U0001F9E0"  # Animales y naturaleza
        "\u2600-\u26FF"          # Símbolos varios (formato corto)
        "\u2700-\u27BF"          # Dingbats (formato corto)
        "\uFE00-\uFE0F"          # Selectores de variación
        "\u200D"                 # Zero Width Joiner (usado en emojis compuestos)
        "\u20E3"                 # Combining Enclosing Keycap
        "\u3030"                 # Wavy dash
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)

def process_html_files(base_dir):
    """
    Procesa todos los archivos HTML en el directorio templates
    """
    templates_dir = Path(base_dir) / 'templates'

    if not templates_dir.exists():
        print(f"No se encontró el directorio: {templates_dir}")
        return

    html_files = list(templates_dir.rglob('*.html'))

    print(f"Encontrados {len(html_files)} archivos HTML")
    print("=" * 60)

    total_changes = 0

    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                original_content = f.read()

            cleaned_content = remove_emojis(original_content)

            if original_content != cleaned_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)

                emoji_count = len(original_content) - len(cleaned_content)
                print(f"[OK] {html_file.relative_to(base_dir)}")
                print(f"     Eliminados ~{emoji_count} caracteres (emojis)")
                total_changes += 1
            else:
                print(f"[-] {html_file.relative_to(base_dir)} (sin emojis)")

        except Exception as e:
            print(f"[ERROR] Error procesando {html_file}: {e}")

    print("=" * 60)
    print(f"\nResumen:")
    print(f"  Archivos procesados: {len(html_files)}")
    print(f"  Archivos modificados: {total_changes}")
    print(f"  Archivos sin cambios: {len(html_files) - total_changes}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    process_html_files(base_dir)
    print("\n¡Proceso completado!")
