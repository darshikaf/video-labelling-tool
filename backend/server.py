import asyncio
import websockets
import json
import base64
import cv2

from core.sam_model import SAMModel

async def handler(websocket):
    print("Client connected")
    sam_model = SAMModel()
    async for message in websocket:
        try:
            data = json.loads(message)
            if data.get("type") == "image":
                print(f"Received image: {data.get('name')} ({data.get('mime')})")
                # Save the image (optional)
                img_data = data["data"].split(",")[1]  # Remove data URL prefix
                with open("received_image.png", "wb") as f:
                    f.write(base64.b64decode(img_data))
                print("Image saved as received_image.png")
            elif data.get("type") == "click":
                frame_path = "received_image.png"  # Assuming the image is saved here
                # current_frame = frame_path
                image_frame = cv2.imread(str(frame_path))
                coords = data.get("coords")
                print(f"Received click at: X={coords['x']}, Y={coords['y']}")
                mask = sam_model.predict(
                            image_frame, 
                            prompt_type="point", 
                            points=[(coords['x'], coords['y'], True)]
                        )
                print(f'Mask is: {mask}')
                print(f"Mask shape: {mask.shape}")
                # Encode mask as PNG and then base64
                _, buffer = cv2.imencode('.png', mask)
                mask_base64 = base64.b64encode(buffer).decode('utf-8')
                await websocket.send(json.dumps({
                    "type": "mask",
                    "data": mask.tolist(),
                    "shape": mask.shape
                }))

            else:
                print("Unknown message type:", data)
        except Exception as e:
            print("Error handling message:", e)

async def main():
    async with websockets.serve(handler, "localhost", 8080):
        print("WebSocket server started on ws://localhost:8080")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())