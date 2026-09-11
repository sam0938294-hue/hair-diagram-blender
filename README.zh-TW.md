# Hair Diagram：Blender 美髮教育工具

供美髮教育、技術圖解與教材製作使用的專業 Blender 工具。可編輯頭皮分線、提拉髮片、輔助線、點位及角度圖，並輸出多視角教材圖片。

[English README](README.md) · [英文使用指南](docs/USER_GUIDE.md)

## 環境需求

自行安裝 Blender。本版以 Blender 5.2.1 LTS 驗證，外掛最低版本設定為 5.2。使用者應具備 Blender 外掛安裝、3D 視窗操作和檔案管理能力。不需要另裝 Python，也不需要第三方 Python 套件。

## 手動安裝與開啟

1. 下載並解壓縮儲存庫，或使用 Git clone。
2. 自行安裝並啟動 Blender。
3. 將儲存庫內 `blender/addon/hair_diagram` 整個資料夾壓縮成 ZIP。ZIP 內第一層應為 `hair_diagram`，其中包含 `__init__.py`、其他程式及 `assets`。在 Blender「編輯 → 偏好設定 → 附加元件」右上選單選擇「從磁碟安裝（Install from Disk）」，手動選取此 ZIP。不要直接安裝整個儲存庫的下載 ZIP。
4. 在偏好設定找到 Hair Diagram，手動勾選啟用；若未啟用自動儲存偏好設定，請自行儲存。
5. 透過 Blender「檔案 → 開啟」，手動開啟儲存庫內 `blender/scenes/editor_head.blend`。
6. 在 3D 視窗按 N 展開側欄，自行找到 Hair Diagram 分頁。

也可手動把完整 `hair_diagram` 資料夾複製至 Blender 使用者 scripts 的 `addons` 目錄，重新啟動 Blender，再完成啟用及開檔步驟。請保留外掛內的 `assets`。

公開版不提供自動安裝、啟動或載入外掛的腳本。保留 Blender 正常的外掛啟用／停用介面，供使用者在偏好設定中自行操作。

## 使用與範圍

新增圖形後，修改所選項目的參數並按「套用到這一項」。用「另存新檔」保存可編輯版本，或輸出透明 PNG。實際控制項和角度定義見英文指南。

頭部模型、參數、幾何及教學邏輯維持原樣。本工具呈現幾何示意，未模擬自然垂落或自動預測完整髮型。教材練習橋接功能仍保留；公開包原本未包含其課程目錄與書頁，需另行提供對應教材。

## 來源與使用範圍

頭部源自 MakeHuman CC0 基礎網格，由本專案加工頭頸並加入教學控制。中文字型為 Noto Sans CJK TC，依 SIL Open Font License 1.1 分享。素材及完整授權位於 `blender/addon/hair_diagram/assets/vendor/`。

提供大家下載、在 Blender 編輯頭圖及輸出自己的教材圖片。本次發布未另行授予重新包裝、轉售或再授權本工具的許可；其他用途請聯絡維護者。第三方素材依原授權使用。
