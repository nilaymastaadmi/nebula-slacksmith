| path group | capture clock | period ns | slack ns | required period ns | F_max MHz |
|---|---|---|---|---|---|
| clk_a | clk_a | 30.000 | -36.723 | **66.723** | **14.99** |
| clk_b | clk_b | 26.500 | -43.438 | **69.938** | **14.30** |
| clk_e | clk_e | 26.500 | -47.683 | **74.183** | **13.48** |
| clk_a | clk_a | 30.000 | +17.593 | **12.407** | **80.60** |
| clk_b | clk_b | 79.500 | +12.367 | **67.133** | **14.90** |
| clk_e | clk_e | 26.500 | +19.529 | **6.971** | **143.45** |

before  k = max(required/period) = **2.799**, binding on clk_e -> design runs at **0.357x** the SDC target frequency
after   k = max(required/period) = **0.844**, binding on clk_b -> design runs at **1.184x** the SDC target frequency

**Improvement factor: 2.799 / 0.844 = 3.32x achievable frequency.**

The binding domain may MOVE between the two halves, in which case per-group before-and-after F_max is not like-for-like and only the scaling factor is.
