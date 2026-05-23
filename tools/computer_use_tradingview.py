"""
Computer Use Tool for TradingView Strategy Creation
====================================================
Uses Claude's Computer Use API to control your desktop,
navigate TradingView, and create Pine Script strategies.

Requirements:
  pip install anthropic pyautogui Pillow

Usage:
  set ANTHROPIC_API_KEY=sk-ant-...
  python tools/computer_use_tradingview.py

The script will:
1. Take a screenshot of your desktop
2. Send it to Claude with computer use tools
3. Claude will navigate to TradingView, wait for you to log in,
   then create a strategy based on the 100 algorithms catalog
"""

import anthropic
import pyautogui
import base64
import io
import time
import sys
import os
import json
from PIL import ImageGrab

# ── Configuration ────────────────────────────────────────────────────────────

SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
MODEL = "claude-sonnet-4-20250514"  # vision-capable sonnet, faster + cheaper for computer use
BETA_FLAG = "computer-use-2025-11-24"
TOOL_VERSION = "computer_20251124"
MAX_ITERATIONS = 60  # max agentic loop steps
MAX_TOKENS = 4096

# Disable pyautogui failsafe (mouse to corner) for automation
pyautogui.FAILSAFE = True  # keep True so you can abort by moving mouse to corner
pyautogui.PAUSE = 0.3  # small delay between actions


# ── Screenshot ───────────────────────────────────────────────────────────────


def take_screenshot() -> str:
    """Capture screen, resize to fit Claude's expected resolution, return base64."""
    img = ImageGrab.grab()

    # Claude expects the display dimensions we declare — scale if needed
    # We'll declare actual screen size to Claude, but cap at 1920x1080 for token cost
    max_w, max_h = 1280, 800
    if img.width > max_w or img.height > max_h:
        ratio = min(max_w / img.width, max_h / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return (
        base64.standard_b64encode(buf.getvalue()).decode("utf-8"),
        img.width,
        img.height,
    )


# ── Execute Computer Actions ─────────────────────────────────────────────────


def execute_computer_action(action: str, params: dict, scale_x: float, scale_y: float):
    """Translate Claude's computer use actions into pyautogui calls."""
    print(f"  > Action: {action}", end="")

    if action == "screenshot":
        print(" (capturing screen)")
        return "screenshot_taken"

    elif action == "left_click":
        coord = params.get("coordinate", [0, 0])
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" at ({x}, {y})")
        modifier = params.get("text", "")
        if modifier:
            pyautogui.keyDown(modifier)
            pyautogui.click(x, y)
            pyautogui.keyUp(modifier)
        else:
            pyautogui.click(x, y)

    elif action == "right_click":
        coord = params.get("coordinate", [0, 0])
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" at ({x}, {y})")
        pyautogui.rightClick(x, y)

    elif action == "double_click":
        coord = params.get("coordinate", [0, 0])
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" at ({x}, {y})")
        pyautogui.doubleClick(x, y)

    elif action == "triple_click":
        coord = params.get("coordinate", [0, 0])
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" at ({x}, {y})")
        pyautogui.tripleClick(x, y)

    elif action == "middle_click":
        coord = params.get("coordinate", [0, 0])
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" at ({x}, {y})")
        pyautogui.middleClick(x, y)

    elif action == "mouse_move":
        coord = params.get("coordinate", [0, 0])
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" to ({x}, {y})")
        pyautogui.moveTo(x, y)

    elif action == "left_click_drag":
        start = params.get("start_coordinate", [0, 0])
        end = params.get("coordinate", [0, 0])
        sx, sy = int(start[0] * scale_x), int(start[1] * scale_y)
        ex, ey = int(end[0] * scale_x), int(end[1] * scale_y)
        print(f" from ({sx},{sy}) to ({ex},{ey})")
        pyautogui.moveTo(sx, sy)
        pyautogui.mouseDown()
        pyautogui.moveTo(ex, ey, duration=0.5)
        pyautogui.mouseUp()

    elif action == "type":
        text = params.get("text", "")
        print(f" '{text[:50]}{'...' if len(text) > 50 else ''}'")
        # Use pyperclip for reliability with special chars
        import pyperclip

        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)

    elif action == "key":
        key_combo = params.get("text", "")
        print(f" '{key_combo}'")
        # Convert Claude's key format to pyautogui
        keys = key_combo.replace("Return", "enter").replace("BackSpace", "backspace")
        if "+" in keys:
            parts = [k.strip().lower() for k in keys.split("+")]
            pyautogui.hotkey(*parts)
        else:
            pyautogui.press(keys.lower())

    elif action == "scroll":
        coord = params.get("coordinate", [0, 0])
        direction = params.get("scroll_direction", "down")
        amount = params.get("scroll_amount", 3)
        x, y = int(coord[0] * scale_x), int(coord[1] * scale_y)
        print(f" {direction} by {amount} at ({x},{y})")
        pyautogui.moveTo(x, y)
        scroll_val = amount if direction == "up" else -amount
        if direction in ("left", "right"):
            pyautogui.hscroll(amount if direction == "right" else -amount)
        else:
            pyautogui.scroll(scroll_val)

    elif action == "wait":
        duration = params.get("duration", 1)
        print(f" {duration}s")
        time.sleep(duration)

    elif action == "hold_key":
        key = params.get("text", "")
        duration = params.get("duration", 1)
        print(f" '{key}' for {duration}s")
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)

    else:
        print(f" (unknown action: {action})")

    time.sleep(0.3)  # brief pause after each action


# ── Agent Loop ───────────────────────────────────────────────────────────────


def run_computer_use_agent(task: str):
    """Main agentic loop: Claude sees screen -> requests actions -> we execute -> repeat."""

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTR")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY (or ANTR) environment variable first!")
        print("  Windows: set ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    print(f"Using API key: {api_key[:12]}...")

    client = anthropic.Anthropic(api_key=api_key)

    # Take initial screenshot to get dimensions
    screenshot_b64, img_w, img_h = take_screenshot()
    scale_x = SCREEN_WIDTH / img_w
    scale_y = SCREEN_HEIGHT / img_h

    print(f"Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT} -> Claude sees: {img_w}x{img_h}")
    print(f"Scale factors: x={scale_x:.2f}, y={scale_y:.2f}")
    print(f"Task: {task}\n")

    # System prompt for TradingView strategy creation
    system_prompt = """You are a desktop automation agent on Windows 11 helping create a TradingView Pine Script strategy.

CRITICAL RULES FOR WINDOWS NAVIGATION:
1. To open a browser: press Win+R, type "chrome https://www.tradingview.com/chart" and press Enter. Do NOT try to find icons in the taskbar.
2. To switch windows: use Alt+Tab, NOT clicking the taskbar.
3. After EVERY action, take a screenshot to verify the result.
4. When you need the user to do something (like log in), say "Please log in now" and WAIT.
5. Be patient with page loads -- use the wait action (2-3 seconds) after navigation.
6. If something doesn't work, try keyboard shortcuts first (Ctrl+A to select all, Ctrl+V to paste, etc).
7. Do NOT take unnecessary screenshots. Only screenshot after meaningful actions.
8. Keep text output SHORT to save tokens.

STRATEGY CREATION APPROACH:
- Open TradingView chart page directly
- Let user log in if needed
- Open Pine Script editor (click "Pine Editor" tab at bottom, or use keyboard)
- Create a NEW indicator/strategy
- Write the RSI-MACD-Volume Confluence strategy in Pine Script v6
- The strategy should include:
  * RSI with dynamic thresholds based on ATR
  * MACD histogram divergence detection
  * Volume confirmation (above 1.5x average)
  * Long/Short entry logic with stop loss (1.5x ATR) and take profit (2.5x ATR)
  * Default: BTCUSDT, 4H timeframe
  * Commission and slippage settings
"""

    tools = [
        {
            "type": TOOL_VERSION,
            "name": "computer",
            "display_width_px": img_w,
            "display_height_px": img_h,
        }
    ]

    # Build initial message with screenshot
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": task},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    },
                },
            ],
        }
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'=' * 60}")
        print(f"Step {iteration}/{MAX_ITERATIONS}")
        print(f"{'=' * 60}")

        # Retry with backoff for rate limits
        response = None
        for attempt in range(5):
            try:
                response = client.beta.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    tools=tools,
                    messages=messages,
                    betas=[BETA_FLAG],
                )
                break
            except anthropic.RateLimitError as e:
                wait_time = 30 * (attempt + 1)
                print(
                    f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/5)..."
                )
                time.sleep(wait_time)
            except anthropic.APIError as e:
                print(f"API Error: {e}")
                break
        if response is None:
            print("Failed after retries, stopping.")
            break

        # Process response
        response_content = response.content
        messages.append({"role": "assistant", "content": response_content})

        tool_results = []
        has_text = False

        for block in response_content:
            if block.type == "text":
                has_text = True
                print(f"\n💬 Claude says: {block.text}\n")

                # If Claude is asking user to do something, pause
                lower = block.text.lower()
                if any(
                    phrase in lower
                    for phrase in [
                        "please log in",
                        "log in",
                        "sign in",
                        "enter your",
                        "waiting for you",
                        "please click",
                        "your turn",
                    ]
                ):
                    input("\n⏸️  Press ENTER when you're done with your part...")
                    # Take fresh screenshot after user action
                    screenshot_b64, _, _ = take_screenshot()
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "I'm done. Here's the current screen:",
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": screenshot_b64,
                                    },
                                },
                            ],
                        }
                    )

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                action = tool_input.get("action", "")

                print(f"  🔧 Tool: {tool_name}")
                execute_computer_action(action, tool_input, scale_x, scale_y)

                # After every action, take a screenshot for the result
                time.sleep(0.5)  # let the screen settle
                screenshot_b64, _, _ = take_screenshot()

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_b64,
                                },
                            }
                        ],
                    }
                )

        # If no tools were called and there was text, we might be done
        if not tool_results:
            if response.stop_reason == "end_turn":
                print("\n✅ Claude finished the task!")
                break
            elif response.stop_reason == "pause_turn":
                # Re-send to continue
                continue
            else:
                print(f"\nStop reason: {response.stop_reason}")
                break

        # Feed tool results back
        messages.append({"role": "user", "content": tool_results})

    print("\n" + "=" * 60)
    print("Session complete!")
    print(f"Total steps: {iteration}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    task = """
Open a web browser and go to tradingview.com.
Let me log in first (tell me when you need me to log in and wait).

After I'm logged in:
1. Open the Pine Script Editor (click the "Pine Editor" tab at the bottom)
2. Create a NEW strategy script
3. Write a Pine Script v6 strategy called "RSI-MACD-Volume Confluence" with:
   - RSI(14) with dynamic overbought/oversold thresholds based on ATR
   - MACD(12,26,9) histogram divergence detection
   - Volume must be above 1.5x 20-period average for entry signals
   - LONG entry: RSI crosses above dynamic oversold + MACD histogram turns positive + volume confirms
   - SHORT entry: RSI crosses below dynamic overbought + MACD histogram turns negative + volume confirms
   - Stop loss: 1.5x ATR below/above entry
   - Take profit: 2.5x ATR from entry
   - Default: BTCUSDT, 4H timeframe
   - Include strategy settings for commission, slippage
4. Add the strategy to the chart
5. Take a final screenshot showing the results

IMPORTANT: After every action, take a screenshot to verify what happened.
If you need me to log in or do anything, tell me and WAIT.
"""
    run_computer_use_agent(task)
