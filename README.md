# Hair Diagram for Blender

A professional Blender-based tool for hair education, technical diagram authoring, and teaching material production. Create and edit scalp sections, elevation panels, guide lines, landmarks, angle diagrams, and consistent multiview PNG illustrations.

[English user guide](docs/USER_GUIDE.md) · [中文說明](README.zh-TW.md)

## Requirements

- Install Blender manually. Verified with Blender 5.2.1 LTS; the add-on declares Blender 5.2 as its minimum version.
- Familiarity with Blender Preferences, add-on installation, the 3D Viewport, and saving `.blend` files.
- No separate Python installation or third-party Python packages are required. The add-on uses Blender's Python runtime.

## Manual installation

1. Download and extract this repository, or clone it.
2. Install and launch Blender yourself.
3. Manually prepare and install the add-on:
   - Locate `blender/addon/hair_diagram` in the extracted repository.
   - Compress the entire `hair_diagram` folder into a ZIP. Its top level must contain `hair_diagram/__init__.py`, the other Python modules, and `hair_diagram/assets/`. Do not select the repository download ZIP as the add-on package.
   - In Blender, open **Edit → Preferences → Add-ons**, open the menu at the top right, choose **Install from Disk**, and select your add-on ZIP.
4. In **Preferences → Add-ons**, find **Hair Diagram** and manually enable its checkbox. Save Preferences if automatic preference saving is disabled.
5. Use **File → Open** to open `blender/scenes/editor_head.blend` from your repository copy.
6. In the **3D Viewport**, open the sidebar with **N** and select **Hair Diagram**.

Alternatively, manually copy the complete `hair_diagram` folder into your Blender user scripts `addons` directory, restart Blender, and perform steps 4–6. Keep the included `assets` folder with the add-on.

There is no supplied installer, launcher, automatic add-on registration script, or scene startup script. Blender's normal `register()` / `unregister()` hooks remain so the user can enable and disable the add-on through Preferences.

## Authoring workflow

Select a viewing direction, add diagram elements on the scalp, edit the selected item's parameters, and apply the changes. Save an independent `.blend` using **File → Save As**, or export a transparent PNG from the Hair Diagram panel. See the [user guide](docs/USER_GUIDE.md) for controls and angle conventions.

The starter includes the head, hairline, locked construction lines, optional landmarks, materials, and cameras. Geometry represents technical diagrams; it does not simulate natural hair fall or predict a completed haircut. Landmarks are adjustable educational approximations.

The optional course/book bridge remains in the add-on. Its lesson catalog and book pages were not included in this public distribution; it requires those separate materials.

## Repository contents

- `blender/addon/hair_diagram/`: manually installable Blender add-on, including required source assets and font.
- `blender/scenes/editor_head.blend`: editable teaching starter.
- `docs/USER_GUIDE.md`: English operating reference.
- `exports/editor/`: interface reference image.

## Provenance and permitted use

The head was derived from the [MakeHuman base mesh](https://github.com/makehumancommunity/makehuman), cropped to the head and neck, reoriented, scaled, capped, and supplemented with eyes. The project adds teaching geometry and editing controls. MakeHuman assets retain CC0; their license files and source record are included under `blender/addon/hair_diagram/assets/vendor/`.

The included Noto Sans CJK TC font is distributed under SIL Open Font License 1.1. See `blender/addon/hair_diagram/assets/vendor/noto/LICENSE` and the [font project](https://github.com/notofonts/noto-cjk). The starter already contains a packed copy of the font.

Users may download the tool, edit head diagrams in Blender, and export their own teaching illustrations. This publication does not separately grant permission to repackage, resell, or sublicense the project tool; contact the maintainer for other uses. Third-party assets retain their respective licenses.
