# video-labelling-tool


## Instructions to Run the Video Segmentation Tool Frontend

This is a minimum viable product (MVP) implementation of the video segmentation tool using Streamlit and Python. Below are instructions to set up and run the frontend locally.

### Prerequisites

- Python 3.8 or newer
- pip package manager

### Setup Instructions

1. **Create a virtual environment** (recommended):
   ```bash
   conda create -n sam-vid python=3.10 -y
   
   conda activate sam-vid
   ```

2. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Streamlit application**:
   ```bash
   cd video-segmentation-tool
   streamlit run frontend/app.py
   ```

   The application should open in your default web browser at http://localhost:8501

### Using the MVP

1. **Upload a video** using the file uploader in the sidebar
2. **Navigate frames** using the frame slider
3. **Apply SAM** button to simulate segmentation (this is a placeholder that generates a simple mask)
4. **Select a class** from the dropdown to associate with segments
5. **Export annotations** button to simulate the export process

## Notes About This MVP

- This is a simplified version focused on the UI structure
- The SAM model functionality is simulated with placeholder methods
- In a real implementation, you would need to:
  - Install the Segment-Anything package from Meta
  - Download the SAM model weights
  - Implement proper interactive annotation callbacks
  - Add temporal tracking between frames
