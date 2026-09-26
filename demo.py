"""
Interactive Demo & Inference Script for Hybrid Crowd Density Estimation.

This script runs the hybrid edge crowd-counting pipeline on any input image:
1. Dispatches image through MobileNetV2 router to determine crowd sparsity.
2. Routes to either LCDNet (sparse specialist) or MobileCount (dense specialist).
3. Produces person count, density map, and detailed routing analytics.
4. Generates a side-by-side visualization saved to disk.

Usage:
    # Run on a specific image
    python demo.py --image path/to/crowd.jpg

    # Run self-test verification
    python demo.py --test

    # Choose specific device or output path
    python demo.py --image path/to/crowd.jpg --device cpu --output demo_result.png
"""

import os
import sys
import argparse
import time
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
import matplotlib.pyplot as plt

# Ensure root is in path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from routing.router import create_router
from models.lcdnet import LCDNet
from models.mobilecount import MobileCount
from torchvision import transforms


def get_default_checkpoints():
    """Retrieve default paths for checkpoints."""
    ck_dir = os.path.join(ROOT_DIR, "checkpoints")
    router_path = os.path.join(ck_dir, "router", "router_best.pth")
    lcdnet_path = os.path.join(ck_dir, "best_model_nwpu_sparse.pth")
    if not os.path.exists(lcdnet_path):
        lcdnet_path = os.path.join(ck_dir, "best_model.pth")
    
    mc_distilled = os.path.join(ck_dir, "mobilecount_distilled.pth")
    mc_best = os.path.join(ck_dir, "mobilecount_best.pth")
    mc_path = mc_distilled if os.path.exists(mc_distilled) else mc_best

    return router_path, lcdnet_path, mc_path


def load_weights_safe(model, path, model_name, device):
    """Safely load model weights or fall back to initialized state with notice."""
    if os.path.exists(path):
        try:
            ckpt = torch.load(path, map_location=device)
            if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                model.load_state_dict(ckpt["model_state_dict"])
            elif isinstance(ckpt, dict) and "state_dict" in ckpt:
                model.load_state_dict(ckpt["state_dict"])
            else:
                model.load_state_dict(ckpt)
            print(f"  [OK] Loaded {model_name} from: {os.path.relpath(path, ROOT_DIR)}")
            return True
        except Exception as e:
            print(f"  [!] Failed loading checkpoint for {model_name}: {e}")
            return False
    else:
        print(f"  [i] Checkpoint not found for {model_name} ({os.path.relpath(path, ROOT_DIR)}).")
        print(f"      (Using initialized weights for pipeline demonstration. See README to download trained weights.)")
        return False


def create_synthetic_crowd_image(width=640, height=480, num_heads=45):
    """Generate a synthetic test image with simulated heads for verification."""
    np.random.seed(42)
    img_arr = np.full((height, width, 3), 40, dtype=np.uint8)
    
    # Add ambient background noise/texture
    noise = np.random.randint(-15, 15, (height, width, 3), dtype=np.int16)
    img_arr = np.clip(img_arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Place Gaussian dots as synthetic heads
    xs = np.random.randint(40, width - 40, size=num_heads)
    ys = np.random.randint(40, height - 40, size=num_heads)

    for x, y in zip(xs, ys):
        for dx in range(-6, 7):
            for dy in range(-6, 7):
                if 0 <= y + dy < height and 0 <= x + dx < width:
                    dist_sq = dx * dx + dy * dy
                    intensity = int(210 * np.exp(-dist_sq / 12.0))
                    for c in range(3):
                        cur_val = int(img_arr[y + dy, x + dx, c])
                        img_arr[y + dy, x + dx, c] = min(255, cur_val + intensity)

    return Image.fromarray(img_arr)


def run_demo(image_path=None, device_str=None, output_path="demo_result.png", threshold=0.85):
    """Execute end-to-end hybrid crowd counting demonstration."""
    # Determine device
    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("\n" + "=" * 65)
    print(" HybridEdge-Crowd: Real-Time Edge Crowd Counting Demo")
    print("=" * 65)
    print(f"Execution Device : {device}")

    # Load or generate image
    if image_path and os.path.exists(image_path):
        print(f"Input Image      : {image_path}")
        image = Image.open(image_path).convert("RGB")
    else:
        if image_path:
            print(f"[!] Warning: Image '{image_path}' not found.")
        print("--> Generating synthetic crowd test image (approx. 45 simulated heads)...")
        image = create_synthetic_crowd_image()

    orig_w, orig_h = image.size
    print(f"Image Resolution : {orig_w} x {orig_h}")

    # Build transformation pipelines
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
    router_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        normalize
    ])
    density_transform = transforms.Compose([
        transforms.Resize((384, 384)),
        transforms.ToTensor(),
        normalize
    ])

    # Instantiate models
    router_path, lcd_path, mc_path = get_default_checkpoints()

    print("\n[Stage 1/3] Initializing Neural Networks...")
    router = create_router(device=str(device), pretrained=False)
    lcdnet = LCDNet().to(device)
    mobilecount = MobileCount(pretrained=False).to(device)

    load_weights_safe(router, router_path, "Router (MobileNetV2)", device)
    load_weights_safe(lcdnet, lcd_path, "LCDNet (Sparse Specialist)", device)
    load_weights_safe(mobilecount, mc_path, "MobileCount (Dense Specialist)", device)

    router.eval()
    lcdnet.eval()
    mobilecount.eval()

    # Step 1: Router forward pass
    print("\n[Stage 2/3] Executing Dynamic Routing...")
    r_tensor = router_transform(image).unsqueeze(0).to(device)
    
    t0 = time.time()
    with torch.no_grad():
        router_logits = router(r_tensor)
        router_probs = F.softmax(router_logits, dim=1).cpu().numpy()[0]
    router_latency = (time.time() - t0) * 1000

    p_sparse = float(router_probs[0])
    p_dense = float(router_probs[1])

    # Decision rule: route to MobileCount if P(dense) >= threshold (p* = 0.85)
    if p_dense >= threshold:
        routed_model = "MobileCount (Dense Specialist)"
        active_model = mobilecount
        is_dense = True
    else:
        routed_model = "LCDNet (Sparse Specialist)"
        active_model = lcdnet
        is_dense = False

    print(f"  P(Sparse)       : {p_sparse:.4f} ({p_sparse*100:.1f}%)")
    print(f"  P(Dense)        : {p_dense:.4f} ({p_dense*100:.1f}%)")
    print(f"  Decision Bound  : p* = {threshold:.2f}")
    print(f"  Selected Route  : --> {routed_model}")
    print(f"  Router Latency  : {router_latency:.2f} ms")

    # Step 2: Density estimation forward pass
    print("\n[Stage 3/3] Density Estimation Inference...")
    d_tensor = density_transform(image).unsqueeze(0).to(device)

    t1 = time.time()
    with torch.no_grad():
        pred_density = active_model(d_tensor)
    density_latency = (time.time() - t1) * 1000
    total_latency = router_latency + density_latency

    density_map = pred_density.squeeze().cpu().numpy()
    pred_count = float(density_map.sum())

    print(f"  Density Latency : {density_latency:.2f} ms")
    print(f"  Total Latency   : {total_latency:.2f} ms (~{1000.0/max(total_latency, 1e-3):.1f} FPS)")
    print(f"\n" + "-" * 40)
    print(f"  >> PREDICTED CROWD COUNT: {pred_count:.1f} people")
    print("-" * 40)

    # Plot & save visual summary
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), facecolor="#f8f9fa")
    
    # Left: Original Image
    axes[0].imshow(image)
    axes[0].set_title(f"Input Image ({orig_w}x{orig_h})", fontsize=12, fontweight="bold", pad=8)
    axes[0].axis("off")

    # Right: Predicted Density Map
    im = axes[1].imshow(density_map, cmap="jet")
    title_text = (
        f"Predicted Density Map\n"
        f"Count: {pred_count:.1f} | Routed: {routed_model.split()[0]} (Conf: {max(p_sparse, p_dense)*100:.1f}%)\n"
        f"Latency: {total_latency:.1f} ms"
    )
    axes[1].set_title(title_text, fontsize=11, fontweight="bold", pad=8)
    axes[1].axis("off")
    fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04, label="Density Value")

    plt.tight_layout()
    plt.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close()

    print(f"\n[OK] Visual result saved to: {output_path}")
    print("=" * 65 + "\n")
    return {
        "count": pred_count,
        "model": routed_model,
        "p_sparse": p_sparse,
        "p_dense": p_dense,
        "latency_ms": total_latency,
        "output_path": output_path
    }


def main():
    parser = argparse.ArgumentParser(description="Hybrid Crowd Density Estimation Demo")
    parser.add_argument("--image", type=str, default=None, help="Path to input crowd image")
    parser.add_argument("--device", type=str, default=None, help="Device to run on (cuda or cpu)")
    parser.add_argument("--output", type=str, default="demo_result.png", help="Path to save output visualization")
    parser.add_argument("--threshold", type=float, default=0.85, help="Dense routing probability threshold p* (default: 0.85)")
    parser.add_argument("--test", action="store_true", help="Run self-test on a synthetic test image")
    args = parser.parse_args()

    run_demo(
        image_path=args.image,
        device_str=args.device,
        output_path=args.output,
        threshold=args.threshold
    )


if __name__ == "__main__":
    main()
