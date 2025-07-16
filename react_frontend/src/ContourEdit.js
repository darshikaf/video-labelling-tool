import React, { useState, useRef } from "react";

function distance(p1, p2) {
  return Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);
}

export default function ContourEditor() {
  const [newContour, setNewContour] = useState([]);
  const [contours, setContours] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [draggingIndex, setDraggingIndex] = useState({ contourIdx: null, pointIdx: null });
  const svgRef = useRef(null);

  const getMousePosition = (e) => {
    const svg = svgRef.current;
    const rect = svg.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };

  const handleMouseDown = (e) => {
    if (draggingIndex.pointIdx !== null) return;

    const pos = getMousePosition(e);

    if (newContour.length >= 3 && distance(pos, newContour[0]) < 10) {
      // Close contour
      setContours([...contours, newContour]);
      setNewContour([]);
    } else {
      setIsDrawing(true);
      setNewContour([...newContour, pos]);
    }
  };

  const handleMouseMove = (e) => {
    if (draggingIndex.pointIdx !== null) {
      const { contourIdx, pointIdx } = draggingIndex;
      const newContours = [...contours];
      newContours[contourIdx][pointIdx] = getMousePosition(e);
      setContours(newContours);
    }
  };

  const handleMouseUp = () => {
    setIsDrawing(false);
    setDraggingIndex({ contourIdx: null, pointIdx: null });
  };

  const handlePointMouseDown = (contourIdx, pointIdx, e) => {
    e.stopPropagation();
    setDraggingIndex({ contourIdx, pointIdx });
  };

  const handleUndo = () => {
    if (newContour.length > 0) {
      // Undo last drawn point
      setNewContour(newContour.slice(0, -1));
    } else if (contours.length > 0) {
      // Undo last finalized contour
      setContours(contours.slice(0, -1));
    }
  };

  return (
    <div>
      <button onClick={handleUndo} style={{ marginBottom: "10px" }}>
        Undo
      </button>
      <svg
        ref={svgRef}
        width="100%"
        height="500"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{ border: "1px solid black", background: "#f8f8f8" }}
      >
        {/* Finalized contours */}
        {contours.map((contour, ci) => (
          <g key={ci}>
            <polygon
              points={contour.map((p) => `${p.x},${p.y}`).join(" ")}
              fill="rgba(0,0,255,0.2)"
              stroke="blue"
              strokeWidth="2"
            />
            {contour.map((p, pi) => (
              <circle
                key={pi}
                cx={p.x}
                cy={p.y}
                r="5"
                fill="red"
                onMouseDown={(e) => handlePointMouseDown(ci, pi, e)}
                style={{ cursor: "pointer" }}
              />
            ))}
          </g>
        ))}

        {/* In-progress contour */}
        {newContour.length > 1 && (
          <polyline
            points={newContour.map((p) => `${p.x},${p.y}`).join(" ")}
            fill="none"
            stroke="green"
            strokeWidth="2"
          />
        )}
        {newContour.map((p, idx) => (
          <circle key={idx} cx={p.x} cy={p.y} r="4" fill="green" />
        ))}
      </svg>
    </div>
  );
}
