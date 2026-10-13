# Empirical results — institutional/whale positioning vs BTC price

Panel: 3345 days (2017-08-17 → 2026-10-13); ETF era 1007 days (2024-01-11 → 2026-10-13)

==============================================================================
A. US SPOT ETF NET FLOWS -> BTC RETURNS  (Farside daily, US$m)
==============================================================================

A1. OLS: forward BTC return (bp) on ETF flow (US$m), Newey-West t-stats
      signal      return    n  bp_per_100m     t     p    r2  ci_lo  ci_hi
    etf_flow ret_prev_d1 1007       32.460 9.729 0.000 0.141  0.259  0.390
    etf_flow      ret_d1 1006        3.407 1.275 0.202 0.002 -0.018  0.086
    etf_flow      ret_d2 1005        3.411 0.747 0.455 0.001 -0.055  0.124
    etf_flow      ret_d3 1004        2.926 0.568 0.570 0.000 -0.072  0.130
 etf_flow_5d ret_prev_d1 1007        3.582 3.954 0.000 0.017  0.018  0.054
 etf_flow_5d      ret_d1 1006        0.482 0.606 0.545 0.000 -0.011  0.020
 etf_flow_5d      ret_d2 1005        0.679 0.449 0.654 0.000 -0.023  0.036
 etf_flow_5d      ret_d3 1004        0.950 0.418 0.676 0.000 -0.035  0.054
etf_flow_10d ret_prev_d1 1007        1.463 2.522 0.012 0.008  0.003  0.026
etf_flow_10d      ret_d1 1006        0.184 0.331 0.740 0.000 -0.009  0.013
etf_flow_10d      ret_d2 1005        0.331 0.310 0.757 0.000 -0.018  0.024
etf_flow_10d      ret_d3 1004        0.699 0.443 0.658 0.001 -0.024  0.038

A2. Contemporaneous vs predictive correlation (reverse-causality check)
     signal      return    n  pearson  spearman
   etf_flow ret_prev_d1 1007   0.3753    0.3380
   etf_flow      ret_d1 1006   0.0394    0.0416
   etf_flow      ret_d2 1005   0.0287    0.0325
etf_flow_5d ret_prev_d1 1007   0.1313    0.1305
etf_flow_5d      ret_d1 1006   0.0177    0.0225
etf_flow_5d      ret_d2 1005   0.0181    0.0258

A3. Next-day return by ETF-flow bucket (US$m; ties at zero make quantiles unusable)
              bucket   n  mean_bp  median_bp  std_bp  hit%  mean_d3%  mean_d7%
strong outflow <-250  92    -9.59     -28.53  314.43 43.48     -0.00      0.46
   outflow -250..-50 156   -20.68     -13.05  234.30 47.44      0.18      0.33
        flat -50..50 411    23.54      17.23  243.65 54.99      0.29      0.62
      inflow 50..250 170     2.45      -6.49  237.12 46.47      0.26      0.46
  strong inflow >250 177    16.68       4.72  226.74 51.98      0.48      1.32

A4. Extreme flow days (top/bottom decile) -> forward returns
group   n  mean_etf_flow  mean_ret_d1  hit%_ret_d1  mean_ret_d2  hit%_ret_d2  mean_ret_d3  hit%_ret_d3  mean_ret_d7  hit%_ret_d7  t_H-L_ret_d1  p_H-L_ret_d1  t_H-L_ret_d2  p_H-L_ret_d2  t_H-L_ret_d3  p_H-L_ret_d3  t_H-L_ret_d7  p_H-L_ret_d7
 HIGH 101      659.15545      0.00099     50.49505      0.00143     53.46535     -0.00037     50.49505      0.00495     53.46535       0.62871       0.53027       0.71453       0.47574       0.14777       0.88267       0.18287       0.85509
  LOW 101     -416.07426     -0.00152     42.57426     -0.00253     47.52475     -0.00136     52.47525      0.00314     54.54545           NaN           NaN           NaN           NaN           NaN           NaN           NaN           NaN

==============================================================================
B. CME COT — LEVERAGED FUNDS (HEDGE FUNDS) NET POSITION -> BTC
==============================================================================

B1. OLS: BTC forward return (bp) on COT position per 1000 contracts (NW t)
    signal  return    n  coef_bp_per_1000       t      p     r2
    lf_net  ret_d7 3102            0.0432  0.7509 0.4527 0.0010
    lf_net ret_d14 3095            0.0833  0.7532 0.4513 0.0016
lf_net_chg  ret_d7 3095            0.1093  0.3597 0.7191 0.0001
    am_net  ret_d7 3102           -0.0721 -0.9872 0.3235 0.0018

B2. Next 1/2/4-week returns when leveraged funds are in top/bottom net-position decile
group   n  mean_lf_net  mean_ret_d7  hit%_ret_d7  mean_ret_d14  hit%_ret_d14  mean_ret_d28  hit%_ret_d28  t_H-L_ret_d7  p_H-L_ret_d7  t_H-L_ret_d14  p_H-L_ret_d14  t_H-L_ret_d28  p_H-L_ret_d28
 HIGH 315     -5.72381     -0.00245     52.38095      -0.00745      46.98413      -0.01499      44.44444      -0.86322       0.38838       -1.43189         0.1527       -2.99099         0.0029
  LOW 315 -19088.64444      0.00313     49.20635       0.00497      47.61905       0.02455      51.42857           NaN           NaN            NaN            NaN            NaN            NaN

B3. Weekly change in leveraged-fund net position (top/bottom decile) -> next-week return
group   n  mean_lf_net_chg  mean_ret_d7  hit%_ret_d7  mean_ret_d14  hit%_ret_d14  t_H-L_ret_d7  p_H-L_ret_d7  t_H-L_ret_d14  p_H-L_ret_d14
 HIGH 313       1514.06709      0.01986     60.38339       0.02464      65.79805         0.206       0.83685       -0.44901        0.65359
  LOW 317      -1383.76341      0.01858     52.05047       0.02872      53.31230           NaN           NaN            NaN            NaN

==============================================================================
C. AGGRESSIVE TAKER BUY SHARE (Binance perp, daily) -> BTC RETURNS
==============================================================================

C1. OLS: return (bp) on taker-buy-share (level), NW t-stats
  signal      return    n  bp_per_+1pp_share     t     p    r2
taker_pp ret_prev_d1 3344             30.904 3.302 0.001 0.085
taker_pp      ret_d1 3344              2.503 1.120 0.263 0.001
taker_pp      ret_d2 3343              5.945 1.405 0.160 0.002

C2. Next-day return by taker-buy-share quintile
 q  count  mean  median    std  hit%  %taker_buy_share
 0    669  3.92    2.74 362.72 50.82              0.45
 1    669 25.41   21.92 341.07 55.01              0.48
 2    668 10.78   -1.19 312.78 49.70              0.50
 3    669 16.74    1.61 366.71 50.52              0.51
 4    669 18.45   -2.15 360.90 49.78              0.54

C3. Extreme taker days (deciles)
group   n  mean_taker_buy_share  mean_ret_d1  hit%_ret_d1  mean_ret_d2  hit%_ret_d2  mean_ret_d3  hit%_ret_d3  t_H-L_ret_d1  p_H-L_ret_d1  t_H-L_ret_d2  p_H-L_ret_d2  t_H-L_ret_d3  p_H-L_ret_d3
 HIGH 335               0.55096      0.00427     50.59880      0.00721     54.49102      0.00888     51.65165       1.86522       0.06259       2.27948       0.02296       2.55652       0.01079
  LOW 335               0.43901     -0.00145     49.55224     -0.00227     48.35821     -0.00440     49.85075           NaN           NaN           NaN           NaN           NaN           NaN

==============================================================================
D. FUNDING-RATE Z-SCORE (crowded positioning) -> BTC RETURNS
==============================================================================

D1. OLS: return (bp) on funding z-score
   signal  return    n  bp_per_1z     t     p  r2
funding_z  ret_d1 2531      3.812 0.640 0.522 0.0
funding_z  ret_d7 2525      1.779 0.056 0.955 0.0
funding_z ret_d14 2518      4.909 0.106 0.915 0.0

D2. Extreme funding weeks (z >= 2 vs z <= -2) -> forward returns
               regime    n  mean_d1%  hit_d1%  mean_d7%  hit_d7%  mean_d14%
  z>=2 (crowded long)   99     0.384   48.485     1.148   53.535      0.508
z<=-2 (crowded short)   30    -0.159   46.667     3.155   66.667      3.078
     -1<z<1 (neutral) 2092     0.101   50.382     0.754   52.008      1.876

==============================================================================
E. DAILY-BIAS CONFLUENCE (ETF 5d flow x taker-buy share) -> next-day BTC
==============================================================================
etf5d taker   n  mean_d1%  median_d1%  hit_d1%  mean_d3%  hit_d3%
  POS   POS 312     0.191      -0.069   49.038     0.455   50.000
  POS   NEG 290     0.119       0.082   53.103     0.427   55.172
  NEG   POS 191     0.174       0.069   52.880     0.464   56.545
  NEG   NEG 213    -0.179      -0.065   48.357    -0.356   52.113

Baseline (all ETF-era days): n=1006, mean_d1=0.089%, hit_d1=50.8%

==============================================================================
F. HOURLY SESSION STUDY — WHERE DOES BTC ACTUALLY MOVE? (2024-01 -> )
==============================================================================

F1. By session (hours = count of hourly candles; share of total |move|):
                  session  hours  mean_ret_bp  mean_abs_bp  mean_taker  up_share  share_of_total_abs_move%
         1 ASIA 00-07 UTC   7119       0.2021      29.0071      0.4849   49.9649                   25.9528
           2 EU 07-13 UTC   6102       0.8008      27.2932      0.4892   51.0980                   20.9338
       3 PRE-US 13-14 UTC   1017      -2.2289      43.1345      0.4923   47.0010                    5.5140
4 US CASH / ETF 14-21 UTC   7113       0.2358      40.3290      0.4913   50.9771                   36.0572
     5 US AFTER 21-24 UTC   3048       1.3549      30.1266      0.4878   50.7218                   11.5421

F2. Hourly |return| by UTC hour (top 8 most volatile hours):
      mean_abs_bp  taker     n
hour                          
14         53.922  0.494  1017
15         49.053  0.494  1016
13         43.135  0.492  1017
17         39.282  0.494  1016
16         37.393  0.491  1016
18         35.441  0.491  1016
1          35.187  0.490  1017
19         34.583  0.487  1016

==============================================================================
G. DATED CASE STUDIES (event -> what BTC did next)
==============================================================================
      date                                                                               event  close_at  ret_d1%  ret_d3%  ret_d7%  ret_d14%
2025-04-08   US tariff-tantrum bottom; whales 10k+ had been buying since ~$75k (Glassnode ATS)  76322.42     8.25     9.30     9.59     22.43
2025-11-07 Whale ATS flip: 10k+ cohort back to accumulation after 3 months selling (Glassnode) 103339.08    -0.99     2.59    -8.46    -17.62
2025-11-27                    Glassnode: whales ATS 0.8 strong accumulation, BTC reclaims $90k  91333.95    -0.49    -1.07     0.81      1.29
2026-01-30               Mega-whales sole accumulators at ~$78k while retail sells (Glassnode)  84260.49    -6.55    -6.55   -16.24    -18.28
2026-08-10         CME leveraged funds flip net long for first time in years (CryptoQuant/COT)  63970.01    -0.58    -0.75     0.88     23.48
2026-04-22                       All ETF rolling flow periods turn positive; IBIT +$246.9m day  78178.23     0.10    -0.71    -3.07      4.18
2026-10-07                   ETF outflow $484.9m (largest recent) -> BTC selloff next sessions  83321.81    -1.88    -0.40      NaN       NaN

==============================================================================
H. ROBUSTNESS & SIGNIFICANCE CHECKS
==============================================================================

H1. ETF outflow asymmetry: pooled outflow days (< -50m) vs all other days
                 n  mean_d1_bp  hit_d1%  mean_d3%  mean_d7%  t_out_vs_rest_d1  p_out_vs_rest_d1
outflow<-50  248.0    -16.5671  45.9677    0.1141    0.3793           -1.7781            0.0762
other        758.0     17.2045  52.3747    0.3295    0.7487           -1.7781            0.0762
   binomial p(hit<50% | outflow) = 0.2276 (one-sided: worse than coin-flip)

H2. Regime split of the ETF->next-day relation (bull vs bear sub-samples)
          period   n  same_day_corr  next_day_bp_per_100m  next_day_hit%  mean_next_d1%  outflow_days
2024-01..2024-12 356          0.330                 0.364         52.809          0.238            65
2025-01..2025-12 365          0.297                 1.168         50.137          0.007            95
    2026-01..now 285          0.577                 9.993         49.123          0.007            88

H3. Extreme taker-share day (top decile) x ETF-5d-flow sign -> forward returns
              taker     etf  n  mean_d1%  hit_d1%  mean_d3%  hit_d3%
   taker TOP decile etf5d>0 60     0.306   46.667     0.193   41.667
   taker TOP decile etf5d<0 41     0.004   43.902    -0.232   43.902
taker BOTTOM decile etf5d>0 61     0.058   52.459    -0.033   50.820
taker BOTTOM decile etf5d<0 40    -0.359   47.500    -1.123   47.500

H4. Is the E confluence (ETF5d<0 & taker<0.5) significantly worse than the rest?
               group   n  mean_d1%  hit_d1%  mean_d3%  rest_mean_d1%    t_d1   p_d1    t_d3   p_d3
etf5d<0 & taker<=0.5 274   -0.1227  48.1752   -0.0996         0.1679 -1.5119 0.1313 -1.6982 0.0901

H5. Lead-lag cross-correlation: ETF flow vs BTC return at +/- 3 days
 lag_days(flow relative to return)  corr_with_ret_prev_d1  corr_with_ret_d1
                                -3                 0.0973            0.1417
                                -2                 0.1418            0.3324
                                -1                 0.3322            0.3768
                                 0                 0.3753            0.0394
                                 1                 0.0394           -0.0025
                                 2                -0.0025           -0.0079
                                 3                -0.0079            0.0094

H6. Live 30-day positioning snapshot (Binance public /futures/data — free, rolling 30d)
                                            count          mean           min           max
takerlongshortRatio_buySellRatio             30.0  9.838000e-01  8.710000e-01  1.121300e+00
takerlongshortRatio_buyVol                   30.0  6.843279e+04  1.820008e+04  1.523336e+05
takerlongshortRatio_sellVol                  30.0  6.973417e+04  1.781243e+04  1.383720e+05
openInterestHist_sumOpenInterest             30.0  9.901711e+04  9.237848e+04  1.091892e+05
openInterestHist_sumOpenInterestValue        30.0  8.173334e+09  7.599452e+09  9.454075e+09
globalLongShortAccountRatio_longAccount      30.0  5.565000e-01  4.716000e-01  6.515000e-01
globalLongShortAccountRatio_shortAccount     30.0  4.435000e-01  3.485000e-01  5.284000e-01
globalLongShortAccountRatio_longShortRatio   30.0  1.284700e+00  8.925000e-01  1.869400e+00
topLongShortPositionRatio_longAccount        30.0  6.568000e-01  6.065000e-01  7.058000e-01
topLongShortPositionRatio_shortAccount       30.0  3.432000e-01  2.942000e-01  3.935000e-01
topLongShortPositionRatio_longShortRatio     30.0  1.933500e+00  1.541500e+00  2.399500e+00
