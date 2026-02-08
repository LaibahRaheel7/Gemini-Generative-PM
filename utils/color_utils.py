"""
Color utilities for project and resource visualization.
Provides consistent color assignment and palette generation.
"""
from typing import Dict
import hashlib


# Predefined color palette with good contrast and accessibility
COLOR_PALETTE = [
    "#3498db",  # Blue
    "#2ecc71",  # Green
    "#e74c3c",  # Red
    "#f39c12",  # Orange
    "#9b59b6",  # Purple
    "#1abc9c",  # Turquoise
    "#e67e22",  # Carrot Orange
    "#34495e",  # Dark Blue-Gray
    "#16a085",  # Green Sea
    "#27ae60",  # Nephritis
    "#2980b9",  # Belize Hole
    "#8e44ad",  # Wisteria
    "#2c3e50",  # Midnight Blue
    "#f1c40f",  # Sunflower
    "#e74c3c",  # Alizarin
    "#95a5a6",  # Concrete
    "#d35400",  # Pumpkin
    "#c0392b",  # Pomegranate
    "#bdc3c7",  # Silver
    "#7f8c8d",  # Asbestos
]

# Cache for project ID to color mapping
_project_color_cache: Dict[str, str] = {}


def get_project_color(project_id: str) -> str:
    """
    Get a consistent color for a project ID.
    
    Uses a hash-based approach to ensure the same project always gets
    the same color, even across sessions.
    
    Args:
        project_id: Unique identifier for the project
        
    Returns:
        Hex color code (e.g., "#3498db")
    """
    if project_id in _project_color_cache:
        return _project_color_cache[project_id]
    
    # Use hash to deterministically assign color
    hash_value = int(hashlib.md5(project_id.encode()).hexdigest(), 16)
    color_index = hash_value % len(COLOR_PALETTE)
    color = COLOR_PALETTE[color_index]
    
    _project_color_cache[project_id] = color
    return color


def get_resource_color(resource_id: str) -> str:
    """
    Get a consistent color for a resource ID.
    
    Args:
        resource_id: Unique identifier for the resource
        
    Returns:
        Hex color code
    """
    # Use same logic as projects but offset by half the palette
    hash_value = int(hashlib.md5(resource_id.encode()).hexdigest(), 16)
    color_index = (hash_value + len(COLOR_PALETTE) // 2) % len(COLOR_PALETTE)
    return COLOR_PALETTE[color_index]


def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple.
    
    Args:
        hex_color: Hex color code (e.g., "#3498db")
        
    Returns:
        Tuple of (r, g, b) values (0-255)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB tuple to hex color.
    
    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)
        
    Returns:
        Hex color code (e.g., "#3498db")
    """
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """
    Lighten a color by a given factor.
    
    Args:
        hex_color: Hex color code
        factor: Lightening factor (0.0 to 1.0)
        
    Returns:
        Lightened hex color code
    """
    r, g, b = hex_to_rgb(hex_color)
    
    # Increase towards 255 (white)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    
    return rgb_to_hex(r, g, b)


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """
    Darken a color by a given factor.
    
    Args:
        hex_color: Hex color code
        factor: Darkening factor (0.0 to 1.0)
        
    Returns:
        Darkened hex color code
    """
    r, g, b = hex_to_rgb(hex_color)
    
    # Decrease towards 0 (black)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    
    return rgb_to_hex(r, g, b)


def get_contrast_text_color(hex_color: str) -> str:
    """
    Get appropriate text color (black or white) for a given background color.
    
    Uses relative luminance calculation to determine readability.
    
    Args:
        hex_color: Background color in hex
        
    Returns:
        "#000000" (black) or "#FFFFFF" (white)
    """
    r, g, b = hex_to_rgb(hex_color)
    
    # Calculate relative luminance
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    # Return black text for light backgrounds, white for dark backgrounds
    return "#000000" if luminance > 0.5 else "#FFFFFF"


def generate_project_palette(num_projects: int) -> list:
    """
    Generate a palette of distinct colors for multiple projects.
    
    Args:
        num_projects: Number of projects needing colors
        
    Returns:
        List of hex color codes
    """
    if num_projects <= len(COLOR_PALETTE):
        return COLOR_PALETTE[:num_projects]
    
    # If we need more colors than in palette, generate variations
    colors = COLOR_PALETTE.copy()
    
    while len(colors) < num_projects:
        # Add lightened versions of existing colors
        base_color = COLOR_PALETTE[len(colors) % len(COLOR_PALETTE)]
        lightened = lighten_color(base_color, 0.3)
        colors.append(lightened)
    
    return colors[:num_projects]


def clear_color_cache():
    """Clear the project color cache. Useful for testing."""
    global _project_color_cache
    _project_color_cache.clear()
