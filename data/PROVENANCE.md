# Provenance

Four public sources, each used under its own terms, and one simulator. Nothing here identifies a traveler: the on time files have no passenger, the registry is kept to the aircraft, and the check log stores airports, hours and buffers.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## The Bureau of Transportation Statistics: Reporting Carrier On-Time Performance

Public domain as a work of the U.S. government. Monthly files from `https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_<year>_<month>.zip`, downloaded one at a time with retries by `deploy/fetch-data.ps1` on a machine that could reach the host. 139 files of 139 expected from January 2015 to July 2026; missing months: none. The fetch on 2026-10-01 also asked for August 2026 and BTS had not published it yet, which is why the window stops at July 2026. 139 files matched the field layout their own readme describes. 74,201,388 rows in all. 950,473 rows (1.28%, from G4, WN, YX) reported the aircraft's registration without its leading N; the N is restored when the result is a valid registration, and the value as reported stays beside it as `tail_reported`.

| File | Rows | Bytes | SHA-256 (first 16) |
|---|---:|---:|---|
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_1.zip | 469,968 | 23,061,477 | 8868b27abf89df04 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_2.zip | 429,191 | 21,229,556 | 2a68ad83560b5ba5 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_3.zip | 504,312 | 24,808,787 | 7cd3568901d5eb57 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_4.zip | 485,151 | 23,625,575 | ed518452e9c630d5 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_5.zip | 496,993 | 24,332,076 | b0679c955296b26c |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_6.zip | 503,897 | 25,759,795 | 792c315d7737a118 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_7.zip | 520,718 | 26,205,185 | b675ccf0b763c6e1 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_8.zip | 510,536 | 25,727,968 | 75d5d8c9bf30b0dc |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_9.zip | 464,946 | 22,575,111 | a2f1d7c2203e7c94 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_10.zip | 486,165 | 23,879,320 | 4f689e7b9e6410bc |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_11.zip | 467,972 | 23,598,907 | a0be321e409219da |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2015_12.zip | 479,230 | 24,458,072 | 463af4e59bcdbc16 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_1.zip | 445,827 | 22,645,736 | b43b3fc96070a861 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_2.zip | 423,889 | 21,625,501 | 5d970bde6fd57530 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_3.zip | 479,122 | 24,478,430 | e1470fa6fd0ccea8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_4.zip | 461,630 | 23,347,686 | d8da8ca68cfa9073 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_5.zip | 479,358 | 23,828,963 | 410798763940aea2 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_6.zip | 487,637 | 24,791,926 | 1265d9c22b2c3e38 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_7.zip | 502,457 | 27,269,670 | 1c54e91116cd8809 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_8.zip | 498,347 | 26,997,150 | 3d50251088a6cd09 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_9.zip | 454,878 | 24,130,587 | bd8827b519c2f103 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_10.zip | 472,626 | 24,343,522 | b8e0b3e2c97a4b45 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_11.zip | 450,938 | 23,494,141 | 54fc94f0abcb2207 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2016_12.zip | 460,949 | 24,065,817 | 42bdb4ee36dbdc28 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_1.zip | 450,017 | 23,377,636 | b324cc73e75733c2 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_2.zip | 410,517 | 20,985,199 | be95630d0a5602d0 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_3.zip | 488,597 | 25,582,475 | 91abd03a7b162dc0 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_4.zip | 468,329 | 24,777,834 | 75380f433c63f592 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_5.zip | 486,483 | 25,724,973 | bdda27c302ef6965 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_6.zip | 494,266 | 26,590,778 | 1b3f1ed15862872e |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_7.zip | 509,070 | 26,793,154 | 1fcdffe88c8c8d1d |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_8.zip | 510,451 | 27,330,600 | f9bb54f2297e4038 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_9.zip | 458,727 | 23,799,967 | 68530e9355bf3fd4 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_10.zip | 479,797 | 25,213,844 | 1b59a7486e5fad44 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_11.zip | 454,162 | 23,400,520 | ca171bcb94f83536 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2017_12.zip | 464,205 | 24,829,541 | 9f84e7a002276646 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_1.zip | 570,138 | 29,202,589 | d9722f0134287273 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_2.zip | 520,769 | 26,783,225 | 8f7f283402b784f6 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_3.zip | 612,034 | 30,193,999 | 8f39974ed7886cb8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_4.zip | 596,078 | 30,781,043 | d35e81cfce45a634 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_5.zip | 616,573 | 31,736,637 | 2dc7e1aaf04e2dec |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_6.zip | 626,217 | 32,226,333 | 0e7a70532dac2088 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_7.zip | 645,317 | 32,887,569 | d3fcf16100dd59ed |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_8.zip | 637,103 | 33,006,511 | 6aae45cee01d6dda |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_9.zip | 585,765 | 29,882,599 | 32b9423c827b45ff |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_10.zip | 616,128 | 31,418,901 | fbe490583915f3fc |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_11.zip | 586,231 | 29,969,446 | 409d05a88e646c21 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2018_12.zip | 593,842 | 30,387,123 | c5269bc44df69060 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_1.zip | 583,985 | 29,527,308 | e0d43e9fca6a298a |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_2.zip | 533,175 | 27,392,090 | f875de8d70c18229 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_3.zip | 632,074 | 31,992,570 | cacf26234b805c20 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_4.zip | 612,023 | 31,115,601 | 6da5230e97bfa1ff |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_5.zip | 636,390 | 32,950,743 | 31ba30855fa8e163 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_6.zip | 636,691 | 33,597,362 | 22baf5bd22a7ecb9 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_7.zip | 659,029 | 34,226,844 | 60cc698891cc7a07 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_8.zip | 658,461 | 34,112,844 | bfe19fa8fd705998 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_9.zip | 605,979 | 30,508,709 | 7673b6d53aa11ea0 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_10.zip | 636,014 | 32,419,572 | 6da37bf93019ac33 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_11.zip | 602,453 | 31,005,144 | 6ec48d19a3d4813c |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2019_12.zip | 625,763 | 33,113,829 | e146e2068c060862 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_1.zip | 607,346 | 30,636,034 | 51a1c727d7103982 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_2.zip | 574,268 | 29,495,988 | 6596cd3c1ff9cb9c |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_3.zip | 648,229 | 30,370,031 | c3f6a248d2d16a80 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_4.zip | 313,382 | 12,878,743 | 5f8b91120234f429 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_5.zip | 180,617 | 8,640,843 | 7ea09b2420fcdc31 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_6.zip | 223,732 | 10,599,043 | 1ad82d56670b360d |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_7.zip | 352,888 | 16,735,556 | 3307d8a06f3f1061 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_8.zip | 376,715 | 18,096,690 | 3670b6c598f5af44 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_9.zip | 323,347 | 15,606,322 | e2f708c5acd4fcea |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_10.zip | 352,106 | 16,897,944 | 084f98e07f9cbe77 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_11.zip | 364,367 | 17,835,131 | f1c4ab06ffb77f39 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2020_12.zip | 371,357 | 18,544,493 | f83766cf64df6a7c |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_1.zip | 361,428 | 17,937,103 | 058bc6f1f017824e |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_2.zip | 332,468 | 16,566,293 | d3cd897cf27c0c08 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_3.zip | 444,476 | 22,052,696 | 9ca9cab885ac61e2 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_4.zip | 450,637 | 22,456,535 | 24801da98cf769b6 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_5.zip | 495,544 | 24,793,587 | f7c1bc0e3f8fca82 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_6.zip | 546,124 | 28,441,672 | 6fd695a0fb6fced4 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_7.zip | 583,258 | 30,524,039 | 756b7b741cfce3d7 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_8.zip | 579,179 | 30,286,200 | c46387fe04caed6a |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_9.zip | 538,051 | 27,453,392 | 6c883fa9768260f8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_10.zip | 564,788 | 29,062,376 | 0cf734917438db10 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_11.zip | 547,559 | 28,360,983 | 2a809f9c05610a5d |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2021_12.zip | 551,885 | 29,177,719 | 7d2a51f0b91ac0e6 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_1.zip | 537,902 | 27,656,931 | ca1ae860eaa54f1f |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_2.zip | 495,713 | 24,207,473 | e9124a0af49f69fd |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_3.zip | 564,853 | 27,939,418 | 90ed43e200ba70e1 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_4.zip | 556,502 | 27,701,512 | a6ebfb5e37929860 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_5.zip | 578,819 | 28,677,421 | cf67d5b1da3fbdce |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_6.zip | 577,283 | 28,846,680 | c92a18dc11037422 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_7.zip | 594,957 | 29,564,713 | edcdae5b306b609e |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_8.zip | 589,810 | 29,039,357 | e8903c63285608c3 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_9.zip | 557,494 | 27,239,747 | f158ff276b75d42e |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_10.zip | 572,287 | 27,884,935 | 4133e6e526a038ce |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_11.zip | 546,410 | 27,124,951 | 3a4343f5a2e59d00 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2022_12.zip | 557,095 | 27,855,593 | 93ef0f6ede001547 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_1.zip | 538,837 | 27,068,766 | 327924faa362d360 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_2.zip | 502,749 | 24,730,977 | bfa6eb7bebb53f10 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_3.zip | 580,322 | 28,954,576 | 1a61dce7c50e5c4f |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_4.zip | 561,441 | 27,994,592 | adf3ecf6e3763a55 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_5.zip | 579,958 | 28,333,534 | aec2e926b11e55f8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_6.zip | 577,262 | 29,075,972 | 67dc6b993ba2e7c2 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_7.zip | 601,866 | 30,208,166 | b1b73635dcb2add3 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_8.zip | 602,987 | 29,539,237 | d374aa3ec2b844d4 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_9.zip | 569,338 | 28,047,499 | 4e7bc3f76857accd |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_10.zip | 598,968 | 29,452,902 | a92cc51c6bb1e7fc |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_11.zip | 563,777 | 27,573,257 | 9ad54595568704a1 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_12.zip | 570,394 | 28,818,502 | c8391a3f06749b6e |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_1.zip | 547,271 | 27,573,265 | fe089b45523f9d4a |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_2.zip | 519,221 | 25,086,854 | 8463683d100504a9 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_3.zip | 591,767 | 29,313,663 | e2c5021406f480e8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_4.zip | 582,185 | 28,540,589 | d8b1e88626a7375d |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_5.zip | 609,743 | 31,139,902 | 03e4ae26c2d1247d |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_6.zip | 611,132 | 31,226,761 | 4f329439fd6892aa |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_7.zip | 634,613 | 34,427,174 | 4d992fee134137b3 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_8.zip | 619,025 | 30,854,511 | 58d651379af90cc4 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_9.zip | 582,622 | 28,433,978 | c0df7503b0050ca4 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_10.zip | 615,497 | 29,418,453 | a417136d6c166373 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_11.zip | 575,404 | 28,149,354 | 26b6e89e7c1f6616 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2024_12.zip | 590,581 | 30,150,370 | a324577aa76d1f0a |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip | 539,747 | 27,108,664 | 868387dcedaef1b8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_2.zip | 504,884 | 25,302,583 | 12dc8dbdb3c8b3c2 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_3.zip | 600,872 | 30,544,825 | 9c80fbc2112cdbf3 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_4.zip | 583,950 | 29,369,186 | f3718431e988e2af |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_5.zip | 605,648 | 30,830,593 | 17c3419d7169b313 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_6.zip | 611,575 | 31,131,411 | 087b75e4e059516c |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_7.zip | 631,428 | 32,208,704 | 74309a3a734d5104 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_8.zip | 602,378 | 30,864,245 | 405668b8a8072662 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_9.zip | 562,439 | 28,151,630 | adc722b1c1494445 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_10.zip | 605,844 | 30,723,803 | 05d14d3fd67fa3e0 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_11.zip | 570,550 | 28,847,755 | 6d5b68eea3ebb25f |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_12.zip | 582,304 | 30,337,431 | a2af96d186bc9997 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_1.zip | 544,003 | 27,312,195 | 9ff58f560519dbc8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_2.zip | 515,037 | 25,811,524 | a18b6de822a63bb8 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_3.zip | 612,102 | 31,150,791 | c0864d5dabd52251 |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_4.zip | 597,919 | 30,504,623 | 70e685ffa6042e6c |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_5.zip | 611,735 | 31,716,693 | 4e7b96999440afec |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_6.zip | 607,577 | 31,606,062 | acd9d03e223e079e |
| On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_7.zip | 631,970 | 33,075,361 | 61d657eb17f5b6f8 |

## The FAA releasable aircraft registry

Public domain as a work of the U.S. government. `ReleasableAircraft.zip` from `https://registry.faa.gov/database/ReleasableAircraft.zip`: MASTER, the aircraft registered today, and DEREG, the ones whose registration was cancelled, which is where the airliners retired since the window opened are. Only the aircraft columns are read; the registrant's name and street address never leave the zip, and the identifier scan fails on any of their column names in a committed table. 9,494 tail numbers in the flights; 79.9% matched a record valid for the dates they flew, covering 90.1% of flights.

## OurAirports

Public domain. `airports.csv` from `https://davidmegginson.github.io/ourairports-data/airports.csv`, for coordinates, names and time zones, committed as `data/airports.csv`: 397 airports in the flights, missing: none.

## Open-Meteo historical weather

Weather data by Open-Meteo.com, CC BY 4.0. Hourly temperature, precipitation, snowfall, wind speed and gusts, low cloud cover and the weather code (for fog, thunder and freezing precipitation) at the FAA's Core 30 airports (DECISIONS.md explains why not at every airport): 3,085,200 hourly rows from 2015-01-01 00:00 to 2026-09-24 23:00 UTC, pulled once with a disk cache and committed as `data/weather/hourly.parquet` with `data/weather/ATTRIBUTION.md`. The values are reanalysis at the airport's coordinates, not the airport's own observations.

## The simulator

`packages/sim` generates the synthetic network the estimators are proven on: 8 carriers, 40 airports and 258 routes over 365 days, seeded, with its truth tables in `data/sim`.
