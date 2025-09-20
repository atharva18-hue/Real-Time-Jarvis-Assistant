# Jarvis Pro — Desktop (Runnable)

This package is prepared to run locally on your machine.

## Quick start (Windows)
1. Extract the ZIP.
2. Double-click `run.bat` and follow prompts. If UAC or antivirus blocks, allow it.
3. If run.bat fails installing PyAudio, try:
   - Install pipwin: `pip install pipwin`
   - `pipwin install pyaudio`
   - Then run `run.bat` again.

## Quick start (macOS / Linux)
1. Extract the ZIP.
2. Open terminal in the folder, run:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
3. If microphone access is blocked, enable it in System Preferences / Settings.

## Files
- `main.py` — entrypoint GUI app (PyQt5)
- `requirements.txt` — pip packages
- `run.bat` / `run.sh` — helper scripts to install deps and run
- `config.json` — (optional) add your OpenWeatherMap API key: {"openweathermap_api_key": "YOUR_KEY"}
- `README.md` — this file

## Notes
- Speech recognition (Google) requires internet.
- pyttsx3 runs offline.
- If you face issues installing PyAudio on Windows, use pipwin or download a wheel matching your Python version.
