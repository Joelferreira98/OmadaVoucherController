#!/usr/bin/env python3
"""
Script to generate PWA icons from SVG
"""

import os
from PIL import Image, ImageDraw, ImageFont
import io

def create_voucher_icon(size, filename):
    """Create a voucher-themed icon"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background circle
    margin = size // 8
    draw.ellipse([margin, margin, size-margin, size-margin], 
                fill=(0, 123, 255, 255))  # Bootstrap primary blue
    
    # Inner circle (lighter)
    inner_margin = margin + size // 16
    draw.ellipse([inner_margin, inner_margin, size-inner_margin, size-inner_margin], 
                fill=(255, 255, 255, 255))
    
    # Voucher/ticket shape
    ticket_margin = size // 4
    ticket_width = size - 2 * ticket_margin
    ticket_height = ticket_width // 2
    ticket_y = (size - ticket_height) // 2
    
    # Ticket background
    draw.rectangle([ticket_margin, ticket_y, ticket_margin + ticket_width, ticket_y + ticket_height],
                  fill=(0, 123, 255, 255))
    
    # Ticket perforations (small circles on edges)
    perforation_size = size // 32
    for i in range(3):
        y_pos = ticket_y + (i + 1) * ticket_height // 4
        # Left perforations
        draw.ellipse([ticket_margin - perforation_size//2, y_pos - perforation_size//2,
                     ticket_margin + perforation_size//2, y_pos + perforation_size//2],
                    fill=(255, 255, 255, 255))
        # Right perforations
        draw.ellipse([ticket_margin + ticket_width - perforation_size//2, y_pos - perforation_size//2,
                     ticket_margin + ticket_width + perforation_size//2, y_pos + perforation_size//2],
                    fill=(255, 255, 255, 255))
    
    # Save the image
    img.save(filename, 'PNG')
    print(f"Generated {filename} ({size}x{size})")

def create_simple_icons():
    """Create simple icon variants for shortcuts"""
    sizes_and_names = [
        (96, 'shortcut-dashboard.png'),
        (96, 'shortcut-vouchers.png'),
        (96, 'shortcut-reports.png'),
        (72, 'badge-72x72.png'),
        (32, 'checkmark.png'),
        (32, 'xmark.png')
    ]
    
    for size, name in sizes_and_names:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if 'dashboard' in name:
            # Dashboard icon - grid
            margin = size // 4
            grid_size = (size - 2 * margin) // 3
            for i in range(2):
                for j in range(2):
                    x = margin + i * (grid_size + size // 12)
                    y = margin + j * (grid_size + size // 12)
                    draw.rectangle([x, y, x + grid_size, y + grid_size],
                                 fill=(0, 123, 255, 255))
        
        elif 'vouchers' in name:
            # Voucher icon - ticket
            margin = size // 4
            draw.rectangle([margin, size//3, size-margin, 2*size//3],
                         fill=(40, 167, 69, 255))  # Success green
        
        elif 'reports' in name:
            # Reports icon - chart bars
            margin = size // 4
            bar_width = (size - 2 * margin) // 4
            heights = [0.4, 0.7, 0.5, 0.9]
            for i, height in enumerate(heights):
                x = margin + i * bar_width
                bar_height = int((size - 2 * margin) * height)
                y = size - margin - bar_height
                draw.rectangle([x, y, x + bar_width - 2, size - margin],
                             fill=(255, 193, 7, 255))  # Warning yellow
        
        elif 'badge' in name:
            # Badge - simple circle
            margin = size // 8
            draw.ellipse([margin, margin, size-margin, size-margin],
                        fill=(220, 53, 69, 255))  # Danger red
        
        elif 'checkmark' in name:
            # Checkmark
            margin = size // 4
            # Simple checkmark path
            points = [
                (margin, size//2),
                (size//2 - margin//2, size - margin),
                (size - margin, margin)
            ]
            draw.line(points, fill=(40, 167, 69, 255), width=size//8)
        
        elif 'xmark' in name:
            # X mark
            margin = size // 4
            width = size // 8
            # Draw X
            draw.line([margin, margin, size-margin, size-margin], 
                     fill=(220, 53, 69, 255), width=width)
            draw.line([size-margin, margin, margin, size-margin], 
                     fill=(220, 53, 69, 255), width=width)
        
        img.save(f'/home/runner/workspace/static/icons/{name}', 'PNG')
        print(f"Generated {name} ({size}x{size})")

def main():
    # Create main app icons
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    for size in sizes:
        filename = f'/home/runner/workspace/static/icons/icon-{size}x{size}.png'
        create_voucher_icon(size, filename)
    
    # Create shortcut and utility icons
    create_simple_icons()
    
    print("\nAll PWA icons generated successfully!")
    print("Icons created in /home/runner/workspace/static/icons/")

if __name__ == '__main__':
    main()