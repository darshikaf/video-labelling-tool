import React, { useState, useEffect, useRef } from "react";
import "./PhotoPicker.css";

const MAX_FILE_SIZE_MB = 10;

const PhotoPicker = () => {
  const [imageURL, setImageURL] = useState(null);
  const [imageFile, setImageFile] = useState(null); // Store the file
  const [error, setError] = useState(null);
  const [clickCoords, setClickCoords] = useState(null);
  const [dotPosition, setDotPosition] = useState(null);
  const imageRef = useRef(null);
  const ws = useRef(null);

  const [maskURL, setMaskURL] = useState(null);

  // Open WebSocket connection
  useEffect(() => {
    ws.current = new WebSocket("ws://localhost:8080"); // Change to your server URL

    ws.current.onopen = () => {
      console.log("WebSocket connected");
      ws.current.onmessage = (event) => {
        console.log("Received message:", event.data);
        
      };
    };

    ws.current.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => {
      if (ws.current) ws.current.close();
      if (imageURL) URL.revokeObjectURL(imageURL);
    };
  }, []);

  const handleFileChange = (e) => {
    setError(null);
    setClickCoords(null);
    setDotPosition(null);

    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      return;
    }

    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_FILE_SIZE_MB) {
      setError(`Image size exceeds ${MAX_FILE_SIZE_MB}MB.`);
      return;
    }

    const objectURL = URL.createObjectURL(file);
    setImageURL((prevURL) => {
      if (prevURL) URL.revokeObjectURL(prevURL);
      return objectURL;
    });
    setImageFile(file);

    // Send image as base64 via WebSocket
    const reader = new FileReader();
    reader.onload = () => {
      if (ws.current && ws.current.readyState === 1) {
        ws.current.send(
          JSON.stringify({
            type: "image",
            data: reader.result, // base64 string
            name: file.name,
            mime: file.type,
          })
        );
      }
    };
    reader.readAsDataURL(file);
  };

  const handleImageClick = (e) => {
    if (!imageRef.current) return;

    const rect = imageRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Normalized
    const scaledX = (x / rect.width).toFixed(3);
    const scaledY = (y / rect.height).toFixed(3);

    setClickCoords({ x: +scaledX, y: +scaledY });
    setDotPosition({ x, y });

    // Send click coordinates via WebSocket
    if (ws.current && ws.current.readyState === 1) {
      ws.current.send(
        JSON.stringify({
          type: "click",
          coords: { x: +scaledX, y: +scaledY },
        })
      );
    }
  };

  return (
    <div className="photo-picker-container">
      <h2 className="photo-picker-title">Upload a Photo</h2>

      <input
        className="photo-picker-input"
        type="file"
        accept="image/*"
        onChange={handleFileChange}
      />

      {error && <p className="photo-picker-error">{error}</p>}

      {imageURL && (
        <div className="photo-wrapper">
          <img
            src={imageURL}
            alt="Uploaded preview"
            className="photo-picker-preview"
            onClick={handleImageClick}
            ref={imageRef}
          />
          {dotPosition && (
            <div
              className="green-dot"
              style={{
                left: `${dotPosition.x}px`,
                top: `${dotPosition.y}px`,
              }}
            />
          )}
        </div>
      )}

      {clickCoords && (
        <p>
          Clicked at: <strong>X: {clickCoords.x}, Y: {clickCoords.y}</strong> (normalized)
        </p>
      )}
    </div>
  );
};

export default PhotoPicker;