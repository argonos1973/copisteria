"""
Generador de paleta de colores armónica basada en un color primario.
Utiliza teoría del color para generar colores complementarios y análogos.
"""
import colorsys
import re


def hex_to_rgb(hex_color):
    """Convierte color HEX a RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    """Convierte RGB a HEX."""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def adjust_lightness(rgb, factor):
    """Ajusta la luminosidad de un color RGB.
    factor > 1 = más claro
    factor < 1 = más oscuro
    """
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    l = max(0, min(1, l * factor))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r * 255, g * 255, b * 255)


def adjust_saturation(rgb, factor):
    """Ajusta la saturación de un color RGB.
    factor > 1 = más saturado
    factor < 1 = menos saturado
    """
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    s = max(0, min(1, s * factor))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r * 255, g * 255, b * 255)


def generate_complementary(rgb):
    """Genera color complementario (opuesto en el círculo cromático)."""
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    h = (h + 0.5) % 1.0  # 180 grados
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r * 255, g * 255, b * 255)


def generate_analogous(rgb, shift=30):
    """Genera color análogo (cercano en el círculo cromático).
    shift: grados de desplazamiento (30 = color análogo cercano)
    """
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    h = (h + shift/360.0) % 1.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r * 255, g * 255, b * 255)


def generate_palette(primary_color_hex):
    """
    Genera una paleta completa de colores basada en un color primario.
    
    Args:
        primary_color_hex: Color primario en formato HEX (#RRGGBB)
    
    Returns:
        dict: Diccionario con todos los colores generados
    """
    # Convertir primario a RGB
    primary_rgb = hex_to_rgb(primary_color_hex)
    
    # Color secundario: ligeramente más claro y con tono análogo
    secondary_rgb = generate_analogous(primary_rgb, shift=15)
    secondary_rgb = adjust_lightness(secondary_rgb, 1.15)
    
    # Color success: verde natural
    success_rgb = (39, 174, 96)  # #27ae60
    
    # Color warning: naranja/amarillo
    warning_rgb = (243, 156, 18)  # #f39c12
    
    # Color danger: rojo
    danger_rgb = (231, 76, 60)  # #e74c3c
    
    # Color info: azul, usar secundario o ajustado
    h, l, s = colorsys.rgb_to_hls(primary_rgb[0]/255.0, primary_rgb[1]/255.0, primary_rgb[2]/255.0)
    # Si el primario ya es azulado (h entre 0.5-0.7), usar el primario
    if 0.5 <= h <= 0.7:
        info_rgb = adjust_lightness(primary_rgb, 1.2)
    else:
        # Si no es azul, generar un azul
        info_rgb = (52, 152, 219)  # #3498db
    
    # Color botón: usar el primario ajustado
    button_rgb = adjust_lightness(primary_rgb, 1.05)
    button_rgb = adjust_saturation(button_rgb, 1.1)
    
    # Color botón hover: más oscuro que el botón
    button_hover_rgb = adjust_lightness(button_rgb, 0.85)
    
    # Color header background: usar el primario
    header_bg_rgb = primary_rgb
    
    # Color header text: blanco o negro según luminosidad del header
    h, l, s = colorsys.rgb_to_hls(header_bg_rgb[0]/255.0, header_bg_rgb[1]/255.0, header_bg_rgb[2]/255.0)
    header_text_rgb = (255, 255, 255) if l < 0.6 else (0, 0, 0)
    
    # Color grid header: mismo que primario o ligeramente diferente
    grid_header_rgb = primary_rgb
    
    # Color grid hover: versión muy clara del secundario con transparencia
    grid_hover_hex = rgb_to_hex(adjust_lightness(secondary_rgb, 1.6))
    # Convertir a rgba con opacidad
    grid_hover_rgba = f"rgba({int(adjust_lightness(secondary_rgb, 1.6)[0])}, {int(adjust_lightness(secondary_rgb, 1.6)[1])}, {int(adjust_lightness(secondary_rgb, 1.6)[2])}, 0.3)"
    
    # Color texto de botones: siempre blanco por defecto (los botones suelen ser oscuros)
    button_text_rgb = (255, 255, 255)
    
    # Color fondo de aplicación: blanco por defecto
    app_bg_rgb = (255, 255, 255)
    
    return {
        'color_primario': primary_color_hex,
        'color_secundario': rgb_to_hex(secondary_rgb),
        'color_success': rgb_to_hex(success_rgb),
        'color_warning': rgb_to_hex(warning_rgb),
        'color_danger': rgb_to_hex(danger_rgb),
        'color_info': rgb_to_hex(info_rgb),
        'color_button': rgb_to_hex(button_rgb),
        'color_button_hover': rgb_to_hex(button_hover_rgb),
        'color_button_text': rgb_to_hex(button_text_rgb),
        'color_app_bg': rgb_to_hex(app_bg_rgb),
        'color_header_bg': rgb_to_hex(header_bg_rgb),
        'color_header_text': rgb_to_hex(header_text_rgb),
        'color_grid_header': rgb_to_hex(grid_header_rgb),
        'color_grid_hover': grid_hover_rgba
    }


if __name__ == '__main__':
    # Ejemplos de uso
    print("Paleta para color negro #0d0d0d:")
    palette = generate_palette('#0d0d0d')
    for key, value in palette.items():
        print(f"{key}: {value}")
    
    print("\nPaleta para color verde #00f00c:")
    palette2 = generate_palette('#00f00c')
    for key, value in palette2.items():
        print(f"{key}: {value}")
    
    print("\nPaleta para color azul #3498db:")
    palette3 = generate_palette('#3498db')
    for key, value in palette3.items():
        print(f"{key}: {value}")
