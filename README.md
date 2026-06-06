# tps2toj

將TPS格式轉換成TOJ格式

## 使用方法(windows)

### 小提醒

**請不要在 windows 中的 wsl 執行 tps2toj，因為某些路徑問題，很常發生問題**

### 執行命令

在本專案下執行 `cmd` 或者是 `powershell`

輸入 `python tps2toj.py {題目所在資料夾} {輸出所在資料夾} [-k(可選)] [-d(可選)]`

舉例來說:

執行 `python tps2toj.py "./pA" "./output/pA"`

會在專案資料夾中自動創建 `/output/pA_{日期+時間}.tar.xz` 檔案

### 可選參數

1. `[-k(可選)]` 會將過程產生的資料夾(tar.xz 解壓縮的資料夾)保留
2. `[-d(可選)]` 會輸出 debug 的訊息

<!-- ## 使用方法(linux)

應該跟 windows 差不多，本人沒用過(待補) -->
