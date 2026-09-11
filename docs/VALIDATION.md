# Manual distribution validation

Validated with Blender 5.2.1 LTS on Windows.

- Copied the add-on and its assets into an isolated temporary `addons` directory.
- Enabled it through Blender's `addon_utils` Preferences backend in an empty factory scene, then opened the starter. Disabled it successfully after verification.
- Confirmed the font and MakeHuman source resolve from the installed add-on directory, without the repository in the import path.
- Re-ran the 49 existing editor checks: reference locks, geometry, elevation conventions, styles, item isolation, picking, visibility, save/reopen, and 2000 × 2000 RGBA PNG export all passed.
- Confirmed the starter contains no automatically executed text modules.
- Confirmed no `.cmd` launcher or auto-registration/bootstrap script remains in the public distribution.
- The starter `.blend` is byte-for-byte unchanged from the initial public release (SHA-256 `2c8ac305ad7bb4a4b7ba75fc95355a3b4e2270a960d5ba52116398237a18d914`).

The registration compatibility change defers font access until text creation because Preferences restricts scene data during registration. Reference locks already exist in the saved starter and remain applied by the scene builder. No geometry formulas, parameter defaults, or teaching rules were changed.

This was an isolated automated backend check; interactive Preferences installation on macOS and Linux has not been verified. Test harnesses that explicitly load/register the add-on are kept outside the public distribution.
