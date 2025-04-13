# AutoDraw

AutoDraw is a Python application that automatically draws images in target applications like MS Paint or Gartic Phone. It processes images in various styles and draws them using mouse automation.

## Features

- **Multiple Image Sources**: Load images from local files or URLs
- **Multiple Drawing Styles**:
  - Pixel-by-pixel replication
  - Edge/outline tracing
  - Vector-style sketch
- **Target Applications**:
  - Windows Paint (mspaint.exe)
  - Gartic Phone (web app)
  - Any other application (custom window title)
- **Color Palette Management**:
  - Default palettes for common applications
  - Custom palette support (JSON/CSV)
- **Adjustable Parameters**:
  - Resolution (scaling)
  - Drawing speed
  - Drawing style
- **User Interface**:
  - Graphical UI with Tkinter
  - Command-line interface
- **Safety Features**:
  - Press ESC at any time to immediately stop drawing
  - Automatic fail-safe when mouse moves to screen corner

## Installation

### Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - pillow
  - opencv-python
  - pyautogui
  - numpy
  - requests
  - keyboard

### Install Dependencies

```bash
pip install pillow opencv-python pyautogui numpy requests keyboard
```

### Download the Application

Download the code files from this repository:
- `auto_draw.py` - Main application
- `sample_palette.json` - Example color palette in JSON format
- `sample_palette.csv` - Example color palette in CSV format

## Usage

### Graphical Interface

Run the application with the GUI:

```bash
python auto_draw.py
```

1. Click "Local File" to select an image file or "URL" to enter an image URL
2. Choose a target application (MS Paint, Gartic Phone, or custom)
3. Select drawing style (Pixel, Outline, or Vector)
4. Adjust resolution (0.5x, 1x, 2x, 4x)
5. Set drawing speed using the slider
6. Choose a color palette (Default or Custom)
7. Click "Draw!" to start the drawing process
8. Press ESC at any time to immediately stop the drawing process

### Command Line

Run the application from the command line:

```bash
python auto_draw.py [IMAGE_PATH_OR_URL] [OPTIONS]
```

Options:
- `--target`, `-t`: Target application (mspaint, gartic, custom) (default: mspaint)
- `--style`, `-s`: Drawing style (pixel, outline, vector) (default: pixel)
- `--resolution`, `-r`: Output resolution multiplier (default: 1.0)
- `--speed`, `-p`: Drawing speed in seconds (default: 0.001)
- `--palette`, `-l`: Path to palette file (JSON or CSV)
- `--nogui`: Run in command-line mode

Examples:

```bash
# Draw an image in MS Paint with default settings
python auto_draw.py image.jpg

# Draw an image from URL in Gartic Phone with outline style
python auto_draw.py https://example.com/image.jpg --target gartic --style outline

# Draw an image with custom palette and 2x resolution
python auto_draw.py image.png --palette custom_palette.json --resolution 2.0 --nogui
```

## Color Palettes

### Default Palettes

The application includes default color palettes for:
- MS Paint (20 colors)
- Gartic Phone (20 colors)
- Generic fallback (9 colors)

### Custom Palettes

You can create your own palette files in JSON or CSV format:

#### JSON Format:
```json
[
    [0, 0, 0],        
    [255, 255, 255],  
    [255, 0, 0],
    ...
]
```

#### CSV Format:
```
0,0,0
255,255,255
255,0,0
...
```

## Tips and Notes

1. **Window Capture**: Make sure the target application window is visible and active before drawing. The application will try to find and activate it automatically.

2. **MS Paint**: For best results in MS Paint:
   - Open MS Paint before starting the drawing
   - Set the canvas size large enough for your image
   - Select the Pencil tool

3. **Gartic Phone**: For Gartic Phone:
   - Join a drawing round before starting
   - Make sure you're in drawing mode

4. **Drawing Speed**: Adjust the drawing speed based on your system's performance:
   - Faster speeds may not work well on slower systems
   - Slower speeds produce more accurate drawings but take longer

5. **Safety Features**:
   - Press ESC at any time to immediately stop the drawing process
   - Moving the mouse to a corner of the screen will also trigger PyAutoGUI's fail-safe and stop the process
   - Use these safety features if you need to regain control of your mouse

6. **Cross-Platform Considerations**:
   - This application is primarily designed for Windows
   - Some features may not work correctly on other platforms
   - Window activation is platform-specific

## Troubleshooting

### Common Issues:

1. **Window Not Found**: If the application can't find the target window:
   - Make sure the application is open and visible
   - Try using a custom window title that matches part of the window title

2. **Drawing Issues**:
   - Make sure drawing tools are selected in the target application
   - Adjust the drawing speed (slower for more accuracy)
   - Try a lower resolution for faster drawing

3. **Image Loading Failures**:
   - Check that the image file exists and is a supported format
   - For URLs, verify the URL is correct and accessible

4. **Stopping the Drawing**:
   - Press ESC to stop drawing immediately
   - Move mouse to any corner of the screen to trigger PyAutoGUI's fail-safe

## License

MIT License 