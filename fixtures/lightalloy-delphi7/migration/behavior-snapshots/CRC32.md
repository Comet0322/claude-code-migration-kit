# Behavior snapshot — CRC32 (TCRC32)

來源：Python 內建 `zlib.crc32`，作為跟來源語言無關的外部權威標準值——不是
實測 Delphi/Free Pascal 輸出（這台機器沒有可用的來源語言執行環境，見
`migration/ground-truth-strategy.md`）。

## 為什麼可以用 zlib.crc32 當權威

`legacy/CRC32.pas` 的 `CRCHash` 查表常數、`Reset`（`Sum:=$FFFFFFFF`）、
`Result`（`Sum xor $FFFFFFFF`）三者合起來就是標準 CRC-32 / IEEE 802.3
（反射多項式 `0xEDB88320`、初始值全 1、輸出前全 1 XOR）——跟 zlib、PNG、
Ethernet FCS、PKZIP 用的是同一個演算法，非本專案自訂的變體。`CRCHash[1] =
$77073096` 這個值就是這個標準多項式查表法的公開已知第二項，可以逐值核對。

驗證方式：

```
$ python3 -c "import zlib; print(hex(zlib.crc32(b'123456789') & 0xFFFFFFFF))"
0xcbf43926
```

`0xCBF43926` 是 CRC-32/ISO-HDLC 演算法對 ASCII `"123456789"` 公開已知的
check value（各種 CRC 演算法目錄，例如 reveng catalogue，都收錄這個值），
`zlib.crc32` 的輸出跟這個公開 check value 一致，確認 `zlib.crc32` 就是跟
`TCRC32` 同一個演算法的獨立實作，可以放心拿來當這個 unit 的行為快照來
源。

## 案例（全部由 `zlib.crc32(data) & 0xFFFFFFFF` 算出）

| # | 輸入（bytes） | 長度 | 預期 `result()`（32-bit unsigned, hex） |
|---|---|---|---|
| 1 | `b""`（空輸入） | 0 | `0x00000000` |
| 2 | `b"123456789"`（CRC 演算法目錄公開 check value） | 9 | `0xCBF43926` |
| 3 | `b"\x00"` | 1 | `0xD202EF8D` |
| 4 | `b"\xff"` | 1 | `0xFF000000` |
| 5 | `bytes(range(256))`（0x00~0xFF 每個值各一次，依序） | 256 | `0x29058C73` |
| 6 | `b"Light Alloy"` | 11 | `0x20B206E5` |
| 7 | `b"abcdefghijklmnopqrstuvwxyz"` | 26 | `0x4C2750BD` |
| 8 | `b"The quick brown fox jumps over the lazy dog"` | 43 | `0x414FA339` |

## 案例 9：`update()` 分段呼叫要跟一次性呼叫結果相同（累加語意）

`UpdateWithBuffer` 沒有在呼叫之間重置 `Sum`，代表可以多次呼叫來累加同一條
資料流的 CRC，等價於 `zlib.crc32(b, zlib.crc32(a)) == zlib.crc32(a + b)`
（zlib 的遞增 CRC 語意跟 `TCRC32` 內部用複數形式保存 running state 的設計
一致，只是外部呈現方式不同）：

```
a = b"Light "
b = b"Alloy"
zlib.crc32(a + b) & 0xFFFFFFFF        == 0x20B206E5
zlib.crc32(b, zlib.crc32(a)) & 0xFFFFFFFF == 0x20B206E5   # 相等
```

也就是說：對一個 `TCRC32`/`CRC32` 實例先 `update(a)` 再 `update(b)`，其
`result()` 必須等於對整個 `a+b` 一次 `update` 的 `result()`——這是驗證
「累加狀態沒有在呼叫之間被錯誤重置」的關鍵案例（案例 6 `b"Light Alloy"`
的值 `0x20B206E5` 剛好可以拿來對照）。

## 案例 10：`UpdateWithStream` 語意等價於把整個 stream 內容餵給 `update()`

`UpdateWithStream` 會先 `Seek(0, soFromBeginning)` 再從頭讀到底（分塊讀
取，不影響最終結果），等於是「讀出 stream 從頭到尾的全部內容，呼叫
`update(整個內容)`」。用 `io.BytesIO(b"Light Alloy")` 當 stream 餵進
`update_stream()`，預期 `result()` 跟案例 6 的 `0x20B206E5` 相同。

## 案例 11：`Reset()` 之後的狀態要能重新從頭累加

呼叫 `update()` 後再呼叫 `reset()`，接著對一組新資料呼叫 `update()`，其
`result()` 必須只反映 `reset()` 之後餵進去的資料，不能殘留 `reset()` 之
前的狀態——例如：先 `update(b"garbage")`，`reset()`，再
`update(b"123456789")`，預期 `result()` 為案例 2 的 `0xCBF43926`，不是別
的值。

## 未涵蓋

- Delphi `DWORD`/`Int64` 在極端邊界（例如剛好 4GB 以上的 stream）下的行
  為：這個 fixture 範圍內不需要驗證這麼大的輸入，`UpdateWithStream` 的分
  塊讀取邏輯本身就是為了處理任意大小輸入設計的，不影響 CRC 數學結果，未
  提供對應案例。
