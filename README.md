# Foundry VTT Wall Creator

A graphical Python application to **automatically detect walls from map images** using OpenCV, and export them directly into [Foundry VTT](https://foundryvtt.com/). No more tedious wall placement — streamline your map setup with a few clicks!

## 🧱 Features

- 🖼️ Load any map image through a simple GUI
- 🎯 Use OpenCV-based wall detection with adjustable sliders for precision
- 🛠️ Visual preview and real-time tweaking of wall detection
- 📤 Export walls to `walls.json` in Foundry-compatible format
- 🧙‍♂️ Send wall data directly to Foundry VTT via its API:
  - Just provide your **admin API token** and **scene name**
  - The app will automatically create all walls in Foundry!

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- A running instance of [Foundry VTT](https://foundryvtt.com/) with:
  - API access enabled (e.g., via [Foundry VTT API modules](https://foundryvtt.wiki/en/development/API))
  - A valid **admin API token**
  - The scene already created in Foundry

### Installation

1. Clone the repo:
    ```bash
    git clone https://github.com/yourusername/foundry-vtt-wall-creator.git
    cd foundry-vtt-wall-creator
    ```

2. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Launch the app:
    ```bash
    python app.py
    ```

## 🖥️ How to Use

1. **Load your map**:  
   Use the GUI to open a map image file (`.jpg`, `.png`, etc.).

2. **Adjust detection**:  
   Tune the wall detection sensitivity using sliders (powered by OpenCV edge detection).

3. **Preview & Edit (if needed)**:  
   Review the detected walls overlaid on the map.

4. **Export as JSON**:  
   Save a `walls.json` file for manual import into Foundry.

5. **OR Send directly to Foundry VTT**:
   - Input your **Foundry server URL**, **admin token**, and **target scene name**
   - Click *Upload*, and the app will send the wall data automatically via HTTP request

## 🧪 Example Output (`walls.json`)

```json
{
  "walls": [
    {
      "c": [x1, y1, x2, y2],
      "move": 1,
      "light": 1,
      "sight": 1,
      "sound": 0
    }
  ]
}
```
# 🔐 Security Note
When using the upload feature:

Your API token is only used locally within the app session

Make sure you do not commit tokens to version control!

# 📸 Screenshots
![image](https://github.com/user-attachments/assets/c89d00ca-bd3a-425f-9863-d9290dad1477)


# 🤝 Contributing
Feel free to open issues, suggest features, or create pull requests! All help is appreciated.

# 📄 License
MIT License © 2025 Your Name
