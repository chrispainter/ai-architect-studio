# App Design Guidelines (Apple Human Interface & Material Design Inspired)

**Primary Directive for all Product Designs:**
Simplicity is paramount. The user interface should feel invisible.

## 1. Aesthetic Integrity
*   **Color Palette:** Use a stark, monochromatic base (white, off-white, dark gray, black) to allow high-quality property photography to serve as the application's primary color. Use exactly one vibrant accent color (e.g., Electric Blue or Coral) strictly for primary call-to-action (CTA) buttons. Do not use generic colors.
*   **Typography:** Utilize a clean, geometric sans-serif font (like Inter, SF Pro, or Roboto). Maintain large, readable body text (minimum 16px) and high-contrast headlines.

## 2. Conversational Interfaces (The Core Flow)
*   **No Clutter:** The chat interface must not look like a traditional search engine. Remove all traditional dropdown menus, sliders, and checkboxes from the primary view.
*   **Natural Language Entry:** The primary interaction model is a single, prominent text input field mimicking a message app, encouraging natural language (e.g., "Find me a home with...").
*   **Progressive Disclosure:** Only reveal complex data (like school ratings, tax history) when the user specifically asks for it or taps a "Deep Dive" button. Do not overwhelm the initial property card.

## 3. Visual Matching System
*   **Image Centric:** When a user uploads an inspiration photo, the response must prioritize large, edge-to-edge image grids of matching properties. Text should be minimized to essential data (Price, Bed/Bath, Match %).

## 4. Mobile-First Responsiveness
*   **Touch Targets:** All interactive elements must be a minimum of 44x44pt to accommodate touch on iOS and Android.
*   **Bottom Navigation:** On mobile, essential navigation and the conversational input bar must be anchored to the bottom of the screen to ensure one-handed usability.
