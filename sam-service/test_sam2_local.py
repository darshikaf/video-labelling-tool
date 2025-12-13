#!/usr/bin/env python3
"""
SAM 2 Local Test Script

This script tests the SAM 2 video predictor locally to verify:
1. Model loads correctly
2. Video can be initialized into a session
3. Object prompts generate initial masks
4. Mask propagation works across all frames
5. Masks are saved correctly

Usage:
    python test_sam2_local.py --video sample.mp4 --output ./masks/
    python test_sam2_local.py --video sample.mp4 --output ./masks/ --simulate  # Test without GPU
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.sam2_video_predictor import SAM2VideoPredictor  # noqa: E402


def save_mask(mask: np.ndarray, output_path: Path, frame_idx: int, object_id: int):
    """Save a mask as a PNG file"""
    # Convert binary mask to image (0 or 255)
    mask_image = Image.fromarray((mask * 255).astype(np.uint8), mode="L")

    filename = f"frame_{frame_idx:06d}_obj_{object_id}.png"
    mask_image.save(output_path / filename)
    return filename


def save_composite_mask(masks: dict, output_path: Path, frame_idx: int, colors: dict):
    """Save a colored composite mask with all objects"""
    if not masks:
        return None

    # Get dimensions from first mask
    first_mask = next(iter(masks.values()))
    h, w = first_mask.shape

    # Create RGB composite
    composite = np.zeros((h, w, 3), dtype=np.uint8)

    for obj_id, mask in masks.items():
        color = colors.get(obj_id, (255, 255, 255))
        # Apply color where mask is 1
        for c in range(3):
            composite[:, :, c] = np.where(mask > 0, color[c], composite[:, :, c])

    composite_image = Image.fromarray(composite, mode="RGB")
    filename = f"frame_{frame_idx:06d}_composite.png"
    composite_image.save(output_path / filename)
    return filename


async def run_test(
    video_path: str,
    output_dir: str,
    model_size: str = "base_plus",
    model_dir: str = "./models",
    simulate: bool = False,
    point_x: float = 320,
    point_y: float = 240,
):
    """Run SAM 2 test"""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SAM 2 Local Test")
    print("=" * 60)
    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")
    print(f"Model size: {model_size}")
    print(f"Simulate mode: {simulate}")
    print("=" * 60)

    # Initialize predictor
    print("\n[1/5] Initializing SAM 2 predictor...")
    start_time = time.time()

    predictor = SAM2VideoPredictor(
        model_size=model_size, model_dir=model_dir, device="cpu" if simulate else "auto"
    )

    if not simulate:
        try:
            await predictor.initialize()
            print(f"  ✓ Model loaded in {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"  ⚠ Model loading failed: {e}")
            print("  → Continuing in simulation mode")
            simulate = True
    else:
        print("  → Simulation mode (no model loaded)")

    # Create video session
    print("\n[2/5] Creating video session...")
    start_time = time.time()

    try:
        session = predictor.create_session(video_path)
        print(f"  ✓ Session created: {session.session_id}")
        print(
            f"  ✓ Video: {session.total_frames} frames, {session.frame_width}x{session.frame_height} @ {session.fps:.2f}fps"
        )
        print(f"  ✓ Loaded in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"  ✗ Failed to create session: {e}")
        return False

    # Add object with point prompt
    print("\n[3/5] Adding object with point prompt...")
    start_time = time.time()

    try:
        # Click on center of first frame (adjust these coordinates for your video)
        result = predictor.add_object(
            session_id=session.session_id,
            frame_idx=0,
            object_id=1,
            points=[(point_x, point_y)],
            labels=[1],  # Positive point
            name="TestObject",
            category="test",
        )
        print(f"  ✓ Object added: {result['name']} (ID: {result['object_id']})")
        print(f"  ✓ Initial mask generated on frame 0")
        print(f"  ✓ Color: RGB{result['color']}")

        # Save initial mask
        mask = result["mask"]
        filename = save_mask(mask, output_path, 0, 1)
        print(f"  ✓ Saved: {filename}")
        print(f"  ✓ Added in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"  ✗ Failed to add object: {e}")
        return False

    # Propagate masks
    print("\n[4/5] Propagating masks to all frames...")
    start_time = time.time()

    try:
        propagation_result = predictor.propagate_masks(session_id=session.session_id)

        num_frames = len(propagation_result["frames"])
        print(f"  ✓ Propagated to {num_frames} frames")
        print(f"  ✓ Propagation completed in {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"  ✗ Failed to propagate masks: {e}")
        return False

    # Save all masks
    print("\n[5/5] Saving masks...")
    start_time = time.time()

    # Get object colors
    colors = {}
    for obj_id, obj in session.objects.items():
        colors[obj_id] = obj.color

    saved_count = 0
    for frame_idx, frame_masks in propagation_result["frames"].items():
        # Save individual object masks
        for obj_id, mask in frame_masks.items():
            save_mask(mask, output_path, frame_idx, obj_id)
            saved_count += 1

        # Save composite (every 10th frame to save disk space)
        if frame_idx % 10 == 0:
            save_composite_mask(frame_masks, output_path, frame_idx, colors)

    print(f"  ✓ Saved {saved_count} mask files")
    print(f"  ✓ Saving completed in {time.time() - start_time:.2f}s")

    # Cleanup
    predictor.close_session(session.session_id)

    # Summary
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Session ID: {session.session_id}")
    print(f"Total frames: {session.total_frames}")
    print(f"Objects tracked: {len(session.objects)}")
    print(f"Output directory: {output_path.absolute()}")
    print("=" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test SAM 2 video segmentation locally"
    )
    parser.add_argument(
        "--video", type=str, required=True, help="Path to input video file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./masks/",
        help="Output directory for masks (default: ./masks/)",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        choices=["tiny", "small", "base_plus", "large"],
        default="base_plus",
        help="SAM 2 model size (default: base_plus)",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="./models",
        help="Directory containing model checkpoints (default: ./models)",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode (no actual model, for testing pipeline)",
    )
    parser.add_argument(
        "--point-x",
        type=float,
        default=320,
        help="X coordinate for initial point prompt (default: 320)",
    )
    parser.add_argument(
        "--point-y",
        type=float,
        default=240,
        help="Y coordinate for initial point prompt (default: 240)",
    )

    args = parser.parse_args()

    # Validate video path
    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}")
        sys.exit(1)

    # Run test
    success = asyncio.run(
        run_test(
            video_path=args.video,
            output_dir=args.output,
            model_size=args.model_size,
            model_dir=args.model_dir,
            simulate=args.simulate,
            point_x=args.point_x,
            point_y=args.point_y,
        )
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
