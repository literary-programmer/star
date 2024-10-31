# This code was almost entirely generated by chatGPT with minor modifications to make it work the way we need.

import json
import base64
import asyncio
import os
import sys
import websockets
import pyttsx3
from configobj import ConfigObj

# Load configuration
config = ConfigObj("pyttsx.ini")
websocket_url = config.get("url", "ws://localhost:7774")

# Initialize text-to-speech engine
engine = pyttsx3.init()
voices = [(voice.name.replace("_", " ").replace("-", " ").replace("(", " ").replace(")", " ").replace("   ", " ").replace("  ", " "), voice.id) for voice in engine.getProperty("voices")]

# Define function to save synthesized speech to a wave file
def synthesize_to_wave(event):
	for v in voices:
		if v[0] != event["voice"]: continue
		voice_name = v[1]
		break
	engine.setProperty("voice", voice_name)
	old_rate = engine.getProperty("rate")
	old_pitch = engine.getProperty("pitch")
	if "rate" in event: engine.setProperty("rate", float(event["rate"]))
	if "pitch" in event: engine.setProperty("pitch", float(event["pitch"]))
	engine.save_to_file(event["text"], "tmp.wav")
	try: engine.runAndWait()
	except Exception as e:
		print(e)
		pass
	if "rate" in event: engine.setProperty("rate", old_rate)
	if "pitch" in event: engine.setProperty("pitch", old_pitch)
	if sys.platform == "darwin":
		# frustratingly pyttsx3 on MacOS produces aif files right now.
		os.rename("tmp.wav", "tmp.aiff")
		os.system("ffmpeg -y -i tmp.aiff tmp.wav 2>/dev/null")
		os.remove("tmp.aiff")
	# Read the wave file and encode it to base64
	wave_data = None
	with open("tmp.wav", "rb") as wave_file:
		wave_data = base64.b64encode(wave_file.read()).decode("utf-8")
	os.remove("tmp.wav")
	return wave_data

# WebSocket handling
async def send_voices(websocket):
	data = {
		"provider": 1,
		"voices": [v[0] for v in voices]
	}
	await websocket.send(json.dumps(data))

async def handle_websocket():
	async with websockets.connect(websocket_url) as websocket:
		await send_voices(websocket)
		while True:
			message = await websocket.recv()
			try:
				event = json.loads(message)
				if "voice" in event and "text" in event:
					encoded_wave = synthesize_to_wave(event)
					response = {
						"speech": event["id"],
						"data": encoded_wave
					}
					await websocket.send(json.dumps(response))
			except json.JSONDecodeError:
				print("Received an invalid JSON message:", message)

# Main entry point
if __name__ == "__main__":
	asyncio.run(handle_websocket())
